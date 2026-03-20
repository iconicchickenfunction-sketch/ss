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
    page = browser.new_page(viewport={"width": 1400, "height": 1600})

    page.goto(ENTRY_URL)
    page.get_by_role("link", name="ご予約はこちら").first.click()
    page.wait_for_load_state("load")

    current_url = page.url
    text = page.locator("body").inner_text()

    if "セッション" in text or "エラー" in text:
        print("SESSION_ERROR")
        browser.close()
        sys.exit(0)

    # 見出し位置取得
    date_box = page.get_by_text("日時の選択").bounding_box()
    seat_box = page.get_by_text("座席エリアの選択").bounding_box()

    date_png = page.screenshot(clip={
        "x": date_box["x"], "y": date_box["y"],
        "width": 800, "height": 200
    })

    seat_png = page.screenshot(clip={
        "x": seat_box["x"], "y": seat_box["y"],
        "width": 800, "height": 400
    })

    date_hash = sha256_bytes(date_png)
    seat_hash = sha256_bytes(seat_png)

    current_state = f"{date_hash}\n{seat_hash}"

    previous = ""
    if STATE_FILE.exists():
        previous = STATE_FILE.read_text()

    if previous == "":
        status = "FIRST_RUN"
    elif previous != current_state:
        status = "CHANGED"
    else:
        status = "NO_CHANGE"

    print(status)

    if status == "CHANGED":
        notify(f"空席変化あり\n{current_url}")

    STATE_FILE.write_text(current_state)

    browser.close()
