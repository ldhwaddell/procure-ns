from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import json
import socket
import random
import os
import httpx
from fake_useragent import UserAgent

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
jwt_token = None

random_ua = UserAgent().chrome

username = os.getenv("PROXY_USER")
password = os.getenv("PROXY_PASS")
proxy_conf = get_proxy_url(username, password)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.new_context(
        proxy=proxy_conf,
        user_agent=random_ua,
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
        global jwt_token
        if response.url == WATCH_REQUEST:
            print("\n RESPONSE RECEIVED:")
            print(f"Status: {response.status}")
            print(f"URL: {response.url}")
            try:
                body = response.text()
                data = json.loads(body)
                jwt_token = data.get("jwttoken")
                print(f"Got JWT: {jwt_token}")

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


if not jwt_token:
    raise Exception("No token found")

# Format cookies
cookie_jar = httpx.Cookies()
for cookie in cookies:
    cookie_jar.set(cookie["name"], cookie["value"], domain=cookie["domain"])

# Build headers
headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Authorization": f"Bearer {jwt_token}",
    "Connection": "keep-alive",
    "Content-Length": "0",
    "DNT": "1",
    "Origin": "https://procurement-portal.novascotia.ca",
    "Referer": "https://procurement-portal.novascotia.ca/tenders",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": random_ua,
    "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

url = "https://procurement-portal.novascotia.ca/procurementui/tenders?page=1&numberOfRecords=50000&sortType=POSTED_DATE_DESC&keyword="

print("\nSending authorized POST request to tenders endpoint...\n")
with httpx.Client(cookies=cookie_jar, headers=headers, timeout=30) as client:
    response = client.post(url)
    print("Status code:", response.status_code)
    print("Response preview:\n", response.text[:500], "...\n")

    try:
        data = response.json()
        with open("tenders.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Response saved to tenders.json")
    except Exception as e:
        print("Failed to parse or save JSON:", e)
