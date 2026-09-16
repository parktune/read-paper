#!/usr/bin/env python3
"""Attach an image to a Confluence page and print the <figure> snippet for the HTML+ body.

  python3 scripts/confluence_upload.py <page-id> <image.png> [--width 760]

The Atlassian MCP server has no attachment tool, so this uses the REST API with an API token
(https://id.atlassian.com/manage-profile/security/api-tokens). Credentials, in order:
  --site/--email/--token flags
  environment: ATL_SITE (https://<you>.atlassian.net), ATL_EMAIL, ATL_TOKEN
  read-paper config: publish.confluence.{site,email,token}
Output JSON: file_id, width, height, snippet. Feed {"<path>": snippet} to md2confluence.py --figures.
"""
import argparse
import base64
import json
import os
import struct
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path


def png_size(path: Path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", head[16:24])
        return w, h
    return None, None


def config_value(key: str):
    try:
        cfg = json.loads(subprocess.run([sys.executable, str(Path(__file__).parent / "config.py"), "show"],
                                        capture_output=True, text=True, check=True).stdout)
        return cfg.get("publish", {}).get("confluence", {}).get(key)
    except Exception:
        return None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("page_id"); p.add_argument("image"); p.add_argument("--width", type=int, default=760)
    p.add_argument("--site"); p.add_argument("--email"); p.add_argument("--token")
    a = p.parse_args()
    site = a.site or os.environ.get("ATL_SITE") or config_value("site")
    email = a.email or os.environ.get("ATL_EMAIL") or config_value("email")
    token = a.token or os.environ.get("ATL_TOKEN") or config_value("token")
    if not (site and email and token):
        sys.exit("error: need site, email and API token (flags, ATL_* env vars, or config publish.confluence.*)")
    site = site.rstrip("/")
    img = Path(a.image)
    data = img.read_bytes()
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{img.name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{site}/wiki/rest/api/content/{a.page_id}/child/attachment", data=body, method="POST",
        headers={"Authorization": "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode(),
                 "X-Atlassian-Token": "nocheck", "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.loads(r.read().decode())
    att = res["results"][0]
    file_id = att["extensions"]["fileId"]
    w, h = png_size(img)
    snippet = (f'<figure data-type="media-single" data-layout="center" data-width="{a.width}" data-width-type="pixel">'
               f'<div data-type="media" data-media-type="file" data-id="{file_id}" data-collection="contentId-{a.page_id}"'
               + (f' data-width="{w}" data-height="{h}"' if w else "") + f">{img.name}</div></figure>")
    print(json.dumps({"file_id": file_id, "width": w, "height": h, "attachment_id": att["id"], "snippet": snippet}))


if __name__ == "__main__":
    main()
