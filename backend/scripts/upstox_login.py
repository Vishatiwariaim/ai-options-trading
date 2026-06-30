"""One-time-per-day Upstox login → saves an access token for real option-chain data.

Upstox tokens expire at 3:30 AM IST daily (no refresh token), so run this each
trading day before using the app.

Setup (once):
  1. Go to https://account.upstox.com/developer/apps and create an app.
  2. Set Redirect URI to exactly:  https://127.0.0.1
  3. Put your API key + secret in backend/.env:
        UPSTOX_API_KEY=your_api_key
        UPSTOX_API_SECRET=your_api_secret
        UPSTOX_REDIRECT_URI=https://127.0.0.1

Run:  python -m scripts.upstox_login
  - Opens the Upstox login URL. Log in and authorize.
  - Your browser lands on https://127.0.0.1/?code=XXXX (page may look broken — that's fine).
  - Copy the `code` value from the address bar and paste it here.
"""
from __future__ import annotations

import json
import sys
import webbrowser
from datetime import date
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import settings

TOKEN_FILE = Path(__file__).resolve().parents[1] / ".upstox_token.json"
AUTH_URL = "https://api.upstox.com/v2/login/authorization/dialog"
TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"


def main() -> int:
    key, secret, redirect = settings.upstox_api_key, settings.upstox_api_secret, settings.upstox_redirect_uri
    if not key or not secret:
        print("ERROR: UPSTOX_API_KEY / UPSTOX_API_SECRET missing in backend/.env")
        return 1

    login = f"{AUTH_URL}?response_type=code&client_id={key}&redirect_uri={quote(redirect, safe='')}"
    print("\n1) Opening Upstox login in your browser...")
    print("   If it doesn't open, paste this URL manually:\n")
    print("   " + login + "\n")
    try:
        webbrowser.open(login)
    except Exception:
        pass

    print("2) Log in & authorize. Browser will redirect to:")
    print(f"     {redirect}/?code=XXXXX   (page may show an error — ignore it)")
    code = input("\n3) Paste the `code` value here: ").strip()
    if not code:
        print("No code entered.")
        return 1

    resp = httpx.post(
        TOKEN_URL,
        headers={"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        data={
            "code": code, "client_id": key, "client_secret": secret,
            "redirect_uri": redirect, "grant_type": "authorization_code",
        },
        timeout=15.0,
    )
    if resp.status_code != 200:
        print(f"Token request failed [{resp.status_code}]: {resp.text[:300]}")
        return 1

    data = resp.json()
    token = data.get("access_token")
    if not token:
        print(f"No access_token in response: {data}")
        return 1

    TOKEN_FILE.write_text(json.dumps({"access_token": token, "saved": date.today().isoformat()}), encoding="utf-8")
    print(f"\n✅ Saved access token to {TOKEN_FILE.name} (valid until ~3:30 AM IST).")
    print("   Restart the backend — option chain ab REAL (Upstox) se aayega.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
