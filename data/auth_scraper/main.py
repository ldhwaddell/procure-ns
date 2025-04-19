import subprocess
import time
import socket
from playwright.sync_api import sync_playwright

CDP_HOST = "127.0.0.1"
CDP_PORT = 9222
CDP_URL = f"http://{CDP_HOST}:{CDP_PORT}"


def wait_for_cdp(port, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex((CDP_HOST, port)) == 0:
                return True
        time.sleep(0.2)
    raise RuntimeError("CDP port not available after waiting")


def main():
    # Start Chrome with CDP endpoint
    chrome = subprocess.Popen(
        [
            "google-chrome-stable",
            "--remote-debugging-port=9222",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--headless=new",
        ]
    )

    try:
        wait_for_cdp(CDP_PORT)

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(CDP_URL)
            page = browser.new_page()
            page.goto("https://example.com")
            print(page.title())
            browser.close()
    finally:
        chrome.terminate()
        chrome.wait()


main()
