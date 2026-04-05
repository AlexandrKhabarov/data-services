#!/usr/bin/env python3
"""
Interactive script to authenticate a Telegram user account and register it
with the data-services pool via the admin API.

Usage (from the backend/ directory):
    python scripts/add_account.py [--api-url http://localhost:8000]

Requirements:
    - The backend service must be running and reachable at --api-url.
    - You need a Telegram API ID + hash from https://my.telegram.org.
    - Run this once per account; it handles interactive OTP / 2FA.
"""

import argparse
import asyncio

import httpx
from telethon import TelegramClient
from telethon.sessions import StringSession


async def _authenticate() -> tuple[str, int, str, str]:
    print("=== Telegram Account Setup ===\n")
    print("Get your API credentials at https://my.telegram.org/apps\n")
    api_id = int(input("API ID:   "))
    api_hash = input("API Hash: ").strip()
    phone = input("Phone (E.164, e.g. +12025551234): ").strip()

    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        await client.start(phone=lambda: phone)
        session_string = client.session.save()
        me = await client.get_me()

    print(f"\nAuthenticated as: {me.first_name} (@{me.username or 'no username'})")
    return phone, api_id, api_hash, session_string


async def _register(
    api_url: str,
    admin_key: str,
    phone: str,
    api_id: int,
    api_hash: str,
    session_string: str,
) -> None:
    async with httpx.AsyncClient(timeout=30.0) as http:
        response = await http.post(
            f"{api_url}/api/v1/accounts",
            json={
                "phone_number": phone,
                "api_id": api_id,
                "api_hash": api_hash,
                "session_string": session_string,
            },
            headers={"X-API-Key": admin_key},
        )
        response.raise_for_status()
        data = response.json()

    print("\nAccount registered successfully!")
    print(f"  ID:     {data['id']}")
    print(f"  Phone:  {data['phone_number']}")
    print(f"  Status: {data['status']}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Authenticate a Telegram account and add it to the pool."
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL of the backend service (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    phone, api_id, api_hash, session_string = await _authenticate()
    admin_key = input("\nAdmin API Key: ").strip()

    await _register(
        api_url=args.api_url,
        admin_key=admin_key,
        phone=phone,
        api_id=api_id,
        api_hash=api_hash,
        session_string=session_string,
    )


if __name__ == "__main__":
    asyncio.run(main())
