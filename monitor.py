from playwright.sync_api import sync_playwright
from pathlib import Path
import os
import requests
import hashlib
import sys

ENTRY_URL = "https://www.cottonclubjapan.co.jp/jp/sp/artists/shoko-haida-260418/"
STATE_FILE = Path("state.txt")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def notify(msg: str):
    if WEBHOOK_URL:
        requests.post(WEBHOOK_URL, json={"content": msg}, timeout=15)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 2200}, device_scale_factor=1)

    page.goto(ENTRY_URL, wait_until="load")
    page.get_by_role("link", name="ご予約はこちら").first.click()
    page.wait_for_load_state("networkidle")

    current_url = page.url
    text = page.locator("body").inner_text()

    if "セッション" in text or "エラー" in text or "３０分以上経過" in text:
        print("SESSION_ERROR")
        browser.close()
        sys.exit(0)

    # 見出しの位置を取る
    date_heading = page.get_by_text("日時の選択", exact=True)
    seat_heading = page.get_by_text("座席エリアの選択", exact=True)
    plan_heading = page.get_by_text("プラン選択", exact=True)

    date_box = date_heading.bounding_box()
    seat_box = seat_heading.bounding_box()
    plan_box = plan_heading.bounding_box()

    if not date_box or not seat_box or not plan_box:
        print("SECTION_NOT_FOUND")
        browser.close()
        sys.exit(1)

    # 見出しより少し下から、次の見出しの直前まで切り取る
    date_clip = {
        "x": 250,
        "y": date_box["y"] + 40,
        "width": 820,
        "height": (seat_box["y"] - (date_box["y"] + 40)) - 20
    }

    seat_clip = {
        "x": 250,
        "y": seat_box["y"] + 40,
        "width": 820,
        "height": (plan_box["y"] - (seat_box["y"] + 40)) - 20
    }

    date_png = page.screenshot(clip=date_clip)
    seat_png = page.screenshot(clip=seat_clip)

    Path("debug_date.png").write_bytes(date_png)
    Path("debug_seat.png").write_bytes(seat_png)

    date_hash = sha256_bytes(date_png)
    seat_hash = sha256_bytes(seat_png)

    current_state = f"{date_hash}\n{seat_hash}"

    previous = ""
    if STATE_FILE.exists():
        previous = STATE_FILE.read_text(encoding="utf-8").strip()

    if previous == "":
        status = "FIRST_RUN"
    elif previous != current_state:
        status = "CHANGED"
    else:
        status = "NO_CHANGE"

    print("CURRENT_URL:", current_url)
    print("DATE_HASH:", date_hash)
    print("SEAT_HASH:", seat_hash)
    print(status)

    if status == "CHANGED":
        notify(f"空席画面に変化あり\n{current_url}")

    STATE_FILE.write_text(current_state, encoding="utf-8")
    browser.close()
