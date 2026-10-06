#!/usr/bin/env python3
"""Post one draft from your own X account. Refuses to run without --confirm."""

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.parse
from pathlib import Path

import requests

API = "https://api.x.com"


def load_env(path):
    if not path.exists():
        sys.exit(f"Missing {path}. Copy .env.example to .env and fill your user tokens.")
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def must(name):
    val = os.environ.get(name, "").strip()
    if not val:
        sys.exit(f"{name} is empty in .env")
    return val


def oauth_header(method, url, keys, extra=None):
    params = {
        "oauth_consumer_key": keys["key"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": keys["token"],
        "oauth_version": "1.0",
    }
    if extra:
        params.update(extra)
    items = [(urllib.parse.quote(k, safe=""), urllib.parse.quote(params[k], safe="")) for k in sorted(params)]
    base = "&".join(f"{k}={v}" for k, v in items)
    raw = "&".join([
        method.upper(),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(base, safe=""),
    ])
    signing = f"{urllib.parse.quote(keys['secret'], safe='')}&{urllib.parse.quote(keys['access_secret'], safe='')}"
    sig = base64.b64encode(hmac.new(signing.encode(), raw.encode(), hashlib.sha1).digest()).decode()
    params["oauth_signature"] = sig
    head = ", ".join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(params[k], safe="")}"'
        for k in sorted(params)
        if k.startswith("oauth_")
    )
    return {"Authorization": f"OAuth {head}"}


def upload_image(path, keys):
    url = f"{API}/2/media/upload"
    data = Path(path).read_bytes()
    if len(data) > 5_000_000:
        sys.exit(f"{path} is over 5 MB. X rejects the image at post time.")
    init = requests.post(
        f"{url}/initialize",
        headers={**oauth_header("POST", f"{url}/initialize", keys), "Content-Type": "application/json"},
        json={"media_type": "image/png" if path.lower().endswith(".png") else "image/jpeg", "media_category": "tweet_image", "total_bytes": len(data)},
        timeout=60,
    )
    if init.status_code >= 300:
        sys.exit(f"Media init failed {init.status_code}: {init.text[:400]}")
    media_id = init.json()["data"]["id"]
    append = requests.post(
        f"{url}/{media_id}/append",
        headers=oauth_header("POST", f"{url}/{media_id}/append", keys),
        files={"media": data},
        data={"segment_index": 0},
        timeout=120,
    )
    if append.status_code >= 300:
        sys.exit(f"Media append failed {append.status_code}: {append.text[:400]}")
    fin = requests.post(
        f"{url}/{media_id}/finalize",
        headers={**oauth_header("POST", f"{url}/{media_id}/finalize", keys), "Content-Type": "application/json"},
        timeout=60,
    )
    if fin.status_code >= 300:
        sys.exit(f"Media finalize failed {fin.status_code}: {fin.text[:400]}")
    return media_id


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--text", default="draft.txt")
    p.add_argument("--image", action="append", default=[])
    p.add_argument("--confirm", action="store_true", help="Required. Without this, nothing is sent.")
    args = p.parse_args()
    here = Path(__file__).resolve().parent
    load_env(here / ".env")
    keys = {
        "key": must("X_API_KEY"),
        "secret": must("X_API_SECRET"),
        "token": must("X_ACCESS_TOKEN"),
        "access_secret": must("X_ACCESS_SECRET"),
    }
    text = Path(args.text).read_text().strip()
    if len(text) > 25000:
        sys.exit("Text is over the long-post cap.")
    print(text)
    print("---")
    if not args.confirm:
        sys.exit("Dry run. Re-run with --confirm to post from your account.")
    media_ids = [upload_image(img, keys) for img in args.image[:4]]
    body = {"text": text}
    if media_ids:
        body["media"] = {"media_ids": media_ids}
    url = f"{API}/2/tweets"
    res = requests.post(
        url,
        headers={**oauth_header("POST", url, keys), "Content-Type": "application/json"},
        data=json.dumps(body),
        timeout=60,
    )
    print(res.status_code)
    print(res.text)
    if res.status_code >= 300:
        sys.exit(1)


if __name__ == "__main__":
    main()
