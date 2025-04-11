import os
import random
import socket
from dotenv import load_dotenv
from typing import Dict
import json
from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright


def rand(min: int = 1, max: int = 4):
    """Get a random interval in [min, max]"""
    return random.uniform(min, max)


def resolve_proxy_ip() -> str:
    return socket.gethostbyname("brd.superproxy.io")


def get_proxy_conf(proxy_ip: str) -> Dict[str, str]:
    load_dotenv()
    username = os.getenv("PROXY_USER")
    password = os.getenv("PROXY_PASS")
    port = 33335
    session_id = str(random.random())

    return {
        "server": f"{proxy_ip}:{port}",
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
    proxy_conf = {
        "server": f"http://{proxy_conf['server']}",
        "username": proxy_conf["username"],
        "password": proxy_conf["password"],
    }

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
