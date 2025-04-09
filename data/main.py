from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import json
import socket
import random
import os

load_dotenv()


def resolve_super_proxy() -> str:
    return socket.gethostbyname("brd.superproxy.io")


def get_proxy_url(username: str, password: str, proxy_ip: str = None) -> dict:
    proxy_ip = proxy_ip or resolve_super_proxy()
    port = 33335
    session_id = str(random.random())
    return {
        "server": f"http://{proxy_ip}:{port}",
        "username": f"{username}-session-{session_id}",
        "password": password,
    }


TARGET_URL = "https://procurement-portal.novascotia.ca/tenders"
WATCH_REQUEST = "https://procurement-portal.novascotia.ca/procurementui/authenticate"

username = os.getenv("PROXY_USER")
password = os.getenv("PROXY_PASS")
proxy_conf = get_proxy_url(username, password)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.new_context(
        proxy=proxy_conf,
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.78 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        device_scale_factor=1,
        is_mobile=False,
        has_touch=False,
    )

    context.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    """)

    def handle_request(request):
        if request.url == WATCH_REQUEST and request.method == "POST":
            print("\n REQUEST MATCHED:")
            print(f"Method: {request.method}")
            print(f"URL: {request.url}")
            print(f"Headers: {request.headers}")
            print(f"Post data: {request.post_data}\n")

    def handle_response(response):
        if response.url == WATCH_REQUEST:
            print("\n RESPONSE RECEIVED:")
            print(f"Status: {response.status}")
            print(f"URL: {response.url}")
            try:
                print(f"Body: {response.text()[:300]}...\n")  # truncate for readability
            except Exception as e:
                print(f"Unable to read response body: {e}\n")

    context.on("request", handle_request)
    context.on("response", handle_response)

    page = context.new_page()
    page.goto(TARGET_URL, timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    cookies = context.cookies()
    print("\n🍪 ALL COOKIES:\n")
    print(json.dumps(cookies, indent=2))

    browser.close()
