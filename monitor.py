from playwright.sync_api import sync_playwright
from pathlib import Path
import os
import requests
import hashlib
import sys

ENTRY_URL = "https://www.cottonclubjapan.co.jp/jp/sp/artists/shoko-haida-260418/"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

STATE_DIR = Path("state")
STATE_DIR.mkdir(exist_ok=True)

DATE_HASH_FILE = STATE_DIR / "date_hash.txt"
SEAT_HASH_FILE = STATE_DIR / "seat_hash.txt"

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""

def write_text(path: Path, value: str):
    path.write_text(value, encoding="utf-8")

def notify(msg: str):
    if WEBHOOK_URL:
        requests.post(WEBHOOK_URL, json={"content": msg}, timeout=15)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 1600})

    # 1. 公演ページへ
    page.goto(ENTRY_URL, wait_until="load")

    # 2. ご予約はこちら を押す
    page.get_by_role("link", name="ご予約はこちら").first.click()
    page.wait_for_load_state("load")

    current_url = page.url
    text = page.locator("body").inner_text()

    print("CURRENT_URL:", current_url)

    # セッション切れやエラーは無視
    bad_words = ["セッション", "切断", "有効期限", "やり直し", "システムエラー", "３０分以上経過"]
    if "error/session" in current_url or any(word in text for word in bad_words):
        print("SESSION_ERROR")
        browser.close()
        sys.exit(0)

    # 見出し位置を取る
    date_heading = page.get_by_text("日時の選択", exact=True)
    seat_heading = page.get_by_text("座席エリアの選択", exact=True)

    date_box = date_heading.bounding_box()
    seat_box = seat_heading.bounding_box()

    if not date_box or not seat_box:
        print("SECTION_NOT_FOUND")
        browser.close()
        sys.exit(1)

    # 見出しの少し下から必要範囲をクリップ
    # ここは今のレイアウト前提。必要なら後で微調整する。
    date_clip = {
        "x": max(date_box["x"] - 10, 0),
        "y": max(date_box["y"] - 5, 0),
        "width": 760,
        "height": 180,
    }

    seat_clip = {
        "x": max(seat_box["x"] - 10, 0),
        "y": max(seat_box["y"] - 5, 0),
        "width": 760,
        "height": 380,
    }

    date_png = page.screenshot(clip=date_clip)
    seat_png = page.screenshot(clip=seat_clip)

    date_hash = sha256_bytes(date_png)
    seat_hash = sha256_bytes(seat_png)

    prev_date_hash = read_text(DATE_HASH_FILE)
    prev_seat_hash = read_text(SEAT_HASH_FILE)

    date_changed = (prev_date_hash != "" and prev_date_hash != date_hash)
    seat_changed = (prev_seat_hash != "" and prev_seat_hash != seat_hash)

    if prev_date_hash == "" or prev_seat_hash == "":
        status = "FIRST_RUN"
    elif date_changed or seat_changed:
        status = "CHANGED"
    else:
        status = "NO_CHANGE"

    print("DATE_HASH:", date_hash)
    print("SEAT_HASH:", seat_hash)
    print(status)

    if status == "CHANGED":
        changed_parts = []
        if date_changed:
            changed_parts.append("日時の選択")
        if seat_changed:
            changed_parts.append("座席エリアの選択")

        message = " / ".join(changed_parts) if changed_parts else "不明"
        notify(f"空席画面に変化あり: {message}\n{current_url}")

    write_text(DATE_HASH_FILE, date_hash)
    write_text(SEAT_HASH_FILE, seat_hash)

    browser.close()
