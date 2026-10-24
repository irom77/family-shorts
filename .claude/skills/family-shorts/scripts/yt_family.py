#!/usr/bin/env python3
"""Upload family-archive Shorts to YouTube (Data API v3, OAuth desktop flow).

Own token (~/.config/family-archive-youtube/token.json), separate from racegow-youtube,
so the FPV channel and the family channel can never be mixed up.

  yt_family.py auth  [--client client_secret.json | --from-token other_token.json]
  yt_family.py channel
  yt_family.py upload --manifest manifest.json --short short_01 --privacy private --expect-channel @irom77
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# youtube = manage own videos (needed to change privacy after upload)
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]
CONFIG = Path.home() / ".config" / "family-archive-youtube"
TOKEN = CONFIG / "token.json"
AUTH_PORT = 8780


def youtube():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    if not TOKEN.exists():
        sys.exit(f"no token at {TOKEN}: run `yt_family.py auth` first")
    c = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not c.valid and c.refresh_token:
        c.refresh(Request())
        TOKEN.write_text(c.to_json())
        TOKEN.chmod(0o600)
    return build("youtube", "v3", credentials=c)


def channels(yt):
    items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    return [{"id": i["id"], "title": i["snippet"]["title"], "handle": i["snippet"].get("customUrl", "")}
            for i in items]


def cmd_auth(a):
    from google_auth_oauthlib.flow import InstalledAppFlow
    if a.client:
        flow = InstalledAppFlow.from_client_secrets_file(a.client, SCOPES)
    else:
        # Reuse the OAuth desktop client stored inside another token file.
        t = json.loads(Path(a.from_token).read_text())
        cfg = {"installed": {"client_id": t["client_id"], "client_secret": t["client_secret"],
                             "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                             "token_uri": t.get("token_uri", "https://oauth2.googleapis.com/token"),
                             "redirect_uris": ["http://localhost"]}}
        flow = InstalledAppFlow.from_client_config(cfg, SCOPES)
    # No browser on WSL: print the consent URL and wait for the redirect on localhost.
    c = flow.run_local_server(port=AUTH_PORT, open_browser=False, prompt="consent",
                              authorization_prompt_message="Open this URL to sign in:\nAUTH_URL {url}",
                              success_message="Done. You can close this tab.")
    CONFIG.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(c.to_json())
    TOKEN.chmod(0o600)
    print("CHANNELS", json.dumps(channels(youtube()), indent=2), flush=True)


def cmd_channel(a):
    print(json.dumps(channels(youtube()), indent=2))


def cmd_upload(a):
    from googleapiclient.http import MediaFileUpload
    mpath = Path(a.manifest)
    man = json.loads(mpath.read_text())
    s = next((x for x in man["shorts"] if x["id"] == a.short), None)
    if not s:
        sys.exit(f"{a.short} not in {mpath}")
    file = Path(a.file) if a.file else mpath.parent / s["file"]
    if not file.exists():
        sys.exit(f"clip not found: {file}")
    if s.get("youtube") and not a.again:
        sys.exit(f"already uploaded as {s['youtube']['url']} (pass --again for a second copy)")

    yt = youtube()
    chans = channels(yt)
    want = a.expect_channel.lower().lstrip("@")
    if not any(want in (c["id"].lower(), c["title"].lower(), c["handle"].lower().lstrip("@")) for c in chans):
        sys.exit(f"token uploads to {chans}, not {a.expect_channel!r}: nothing uploaded")

    body = {"snippet": {"title": s["title"], "description": s["description"], "tags": s.get("tags", []),
                        "categoryId": s.get("categoryId", "22"), "defaultLanguage": "pl"},
            "status": {"privacyStatus": a.privacy, "selfDeclaredMadeForKids": False}}
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(file), chunksize=8 * 1024 * 1024, resumable=True))
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"uploaded {status.progress():.0%}", flush=True)
    url = f"https://youtube.com/shorts/{resp['id']}"
    print("VIDEO", resp["id"], url, resp["status"]["privacyStatus"])
    s["youtube"] = {"id": resp["id"], "url": url, "privacy": resp["status"]["privacyStatus"],
                    "channel": chans[0], "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    mpath.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n")


def cmd_privacy(a):
    mpath = Path(a.manifest)
    man = json.loads(mpath.read_text())
    s = next((x for x in man["shorts"] if x["id"] == a.short), None)
    if not s or not s.get("youtube"):
        sys.exit(f"{a.short} has no upload recorded in {mpath}")
    yt = youtube()
    chans = channels(yt)
    want = a.expect_channel.lower().lstrip("@")
    if not any(want in (c["id"].lower(), c["title"].lower(), c["handle"].lower().lstrip("@")) for c in chans):
        sys.exit(f"token is for {chans}, not {a.expect_channel!r}: nothing changed")
    vid = s["youtube"]["id"]
    st = yt.videos().list(part="status", id=vid).execute()["items"][0]["status"]
    st["privacyStatus"] = a.privacy
    st.pop("publishAt", None)
    yt.videos().update(part="status", body={"id": vid, "status": st}).execute()
    now = yt.videos().list(part="status", id=vid).execute()["items"][0]["status"]["privacyStatus"]
    print("VIDEO", vid, s["youtube"]["url"], now)
    s["youtube"]["privacy"] = now
    mpath.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("auth", help="one-time Google sign-in")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--client", help="OAuth desktop client file (client_secret_*.json)")
    g.add_argument("--from-token", help="reuse the OAuth client stored in another token.json")
    sub.add_parser("channel", help="show the channel the token uploads to")
    p = sub.add_parser("upload", help="upload one short listed in manifest.json")
    p.add_argument("--manifest", required=True)
    p.add_argument("--short", required=True, help="e.g. short_01")
    p.add_argument("--privacy", required=True, choices=["private", "unlisted", "public"])
    p.add_argument("--expect-channel", required=True, help="channel id, title or @handle")
    p.add_argument("--file", help="default: manifest folder / short's file")
    p.add_argument("--again", action="store_true")
    p = sub.add_parser("privacy", help="change the privacy of an uploaded short")
    p.add_argument("--manifest", required=True)
    p.add_argument("--short", required=True)
    p.add_argument("--privacy", required=True, choices=["private", "unlisted", "public"])
    p.add_argument("--expect-channel", required=True)
    a = ap.parse_args()
    {"auth": cmd_auth, "channel": cmd_channel, "upload": cmd_upload, "privacy": cmd_privacy}[a.cmd](a)


if __name__ == "__main__":
    main()
