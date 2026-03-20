from playwright.sync_api import sync_playwright
from pathlib import Path
import os
import requests

URL = "https://reserve.cottonclubjapan.co.jp/reserve/plan#5607"
STATE_FILE = Path("state.txt")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="load")

    current = page.content()

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

    if status == "CHANGED" and WEBHOOK_URL:
        message = {
            "content": f"ページに変化あり: {URL}"
        }
        requests.post(WEBHOOK_URL, json=message, timeout=15)

    STATE_FILE.write_text(current, encoding="utf-8")
    browser.close()
