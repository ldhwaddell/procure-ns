from typing import Dict
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import json
import socket
import random
import os
import httpx
from fake_useragent import UserAgent

load_dotenv()


def resolve_proxy() -> str:
    return socket.gethostbyname("brd.superproxy.io")


def get_proxy_conf(proxy_ip: str) -> Dict[str, str]:
    username = os.getenv("PROXY_USER")
    password = os.getenv("PROXY_PASS")
    port = 33335
    session_id = str(random.random())

    return {
        "server": f"http://{proxy_ip}:{port}",
        "username": f"{username}-session-{session_id}",
        "password": password,
    }


def launch_browser_and_get_auth(proxy_conf: Dict[str, str]):
    TARGET_URL = "https://procurement-portal.novascotia.ca/tenders"
    WATCH_REQUEST = (
        "https://procurement-portal.novascotia.ca/procurementui/authenticate"
    )
    jwt_token = None
    ua = UserAgent(platforms="desktop").random

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.new_context(
            proxy=proxy_conf,
            user_agent=ua,
            viewport={"width": 1280, "height": 800},
        )
        context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        """)

        def on_response(response):
            nonlocal jwt_token
            if response.url == WATCH_REQUEST:
                body = response.text()
                data = json.loads(body)
                jwt_token = data.get("jwttoken")

        context.on("response", on_response)

        page = context.new_page()
        page.goto(TARGET_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        cookies = context.cookies()
        browser.close()

    if not jwt_token:
        raise Exception("No token received")

    return {
        "jwt": jwt_token,
        "cookies": cookies,
        "user_agent": ua,
    }


def send_authenticated_request(auth_data: Dict[str, str]):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {auth_data['jwt']}",
        "Content-Length": "0",
        "Connection": "keep-alive",
        "DNT": "1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Origin": "https://procurement-portal.novascotia.ca",
        "Referer": "https://procurement-portal.novascotia.ca/tenders",
        "User-Agent": auth_data["user_agent"],
    }
    url = "https://procurement-portal.novascotia.ca/procurementui/tenders?page=1&numberOfRecords=50000&sortType=POSTED_DATE_DESC&keyword="

    cookies = httpx.Cookies()
    for cookie in auth_data["cookies"]:
        cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])

    with httpx.Client(cookies=cookies, headers=headers, timeout=30) as client:
        response = client.post(url)
        response.raise_for_status()
        return response.json()


def save_tenders(data: Dict):
    with open("tenders.json", "w") as f:
        json.dump(data, f, indent=2)
    return "tenders.json"


def scrape_tenders_job():
    ip = resolve_proxy()
    proxy_conf = get_proxy_conf(ip)
    auth_data = launch_browser_and_get_auth(proxy_conf)
    data = send_authenticated_request(auth_data)
    save_tenders(data)


scrape_tenders_job()
