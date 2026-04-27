#!/usr/bin/env python3

import json
import requests

BASE_URL = "http://localhost:5000"


def call(method, path, **kwargs):
    response = requests.request(method, f"{BASE_URL}{path}", timeout=10, **kwargs)
    try:
        body = response.json()
    except Exception:
        body = response.text
    return response.status_code, body


def main():
    print("[1] Health")
    print(call("GET", "/health"))

    print("[2] Login")
    status, body = call(
        "POST",
        "/auth/login",
        json={"phone_number": "0901234567", "password": "Password1"},
    )
    print(status, json.dumps(body, indent=2))

    token = body.get("access_token") if isinstance(body, dict) else None

    print("[3] Me")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    print(call("GET", "/auth/me", headers=headers))

    print("[4] OIDC proxy smoke test")
    print(
        call(
            "POST",
            "/auth/oidc/token",
            json={
                "grant_type": "authorization_code",
                "client_id": "serviceapp.demo",
                "code": "invalid_code",
                "redirect_uri": "netflixclone://callback",
                "code_verifier": "verifier",
            },
        )
    )


if __name__ == "__main__":
    main()
