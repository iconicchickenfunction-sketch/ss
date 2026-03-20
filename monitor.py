from playwright.sync_api import sync_playwright
from pathlib import Path
import os
import requests
import sys

ENTRY_URL = "https://www.cottonclubjapan.co.jp/jp/sp/artists/shoko-haida-260418/"
STATE_FILE = Path("state.txt")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def notify(msg: str):
    if WEBHOOK_URL:
        requests.post(WEBHOOK_URL, json={"content": msg}, timeout=15)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    # 1) 公演ページを開く
    page.goto(ENTRY_URL, wait_until="load")

    # 2) 「ご予約はこちら」を押す
    page.get_by_role("link", name="ご予約はこちら").first.click()

    # 3) 遷移完了を待つ
    page.wait_for_load_state("load")

    current_url = page.url
    text = page.locator("body").inner_text()
    current = page.content()

    print("CURRENT_URL:", current_url)
    print(text[:500])

    # 4) セッション切れ/エラーページは比較対象にしない
    bad_words = [
        "セッション",
        "切断",
        "有効期限",
        "やり直し",
        "システムエラー",
        "３０分以上経過",
    ]

    if "error/session" in current_url or any(word in text for word in bad_words):
        print("SESSION_ERROR")
        browser.close()
        sys.exit(0)

    # 5) 前回と比較
    previous = ""
    if STATE_FILE.exists():
        previous = STATE_FILE.read_text(encoding="utf-8")

    if previous == "":
        status = "FIRST_RUN"
    elif previous != current:
        status = "CHANGED"
    else:
        status = "NO_CHANGE"

    print(status)

    # 6) 変化があればDiscord通知
    if status == "CHANGED":
        notify(f"空席ページに変化あり: {current_url}")

    # 7) 今回の状態を保存
    STATE_FILE.write_text(current, encoding="utf-8")
    browser.close()
