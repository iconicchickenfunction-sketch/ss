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
    page = browser.new_page(viewport={"width": 1400, "height": 1800}, device_scale_factor=1)

    page.goto(ENTRY_URL, wait_until="load")
    page.get_by_role("link", name="ご予約はこちら").first.click()
    page.wait_for_load_state("networkidle")

    current_url = page.url
    text = page.locator("body").inner_text()

    if "セッション" in text or "エラー" in text or "３０分以上経過" in text:
        print("SESSION_ERROR")
        browser.close()
        sys.exit(0)

    # ページを少し下へ
    page.evaluate("window.scrollTo(0, 500)")
    page.wait_for_timeout(1000)

    # 固定座標で小さく切り取る
    # 1st/2nd のボタン付近
    date_png = page.screenshot(clip={
        "x": 290,
        "y": 590,
        "width": 760,
        "height": 120
    })

    # 席種ボタン群だけ
    seat_png = page.screenshot(clip={
        "x": 285,
        "y": 845,
        "width": 380,
        "height": 250
    })

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
