from playwright.sync_api import sync_playwright
from pathlib import Path

URL = "https://reserve.cottonclubjapan.co.jp/reserve/plan#5607"
STATE_FILE = Path("state.txt")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="load")

    current = page.content()

    previous = ""
    if STATE_FILE.exists():
        previous = STATE_FILE.read_text(encoding="utf-8")

    if previous == "":
        print("FIRST_RUN")
    elif previous != current:
        print("CHANGED")
    else:
        print("NO_CHANGE")

    STATE_FILE.write_text(current, encoding="utf-8")
    browser.close()
