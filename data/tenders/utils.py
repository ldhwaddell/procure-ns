import docker
from docker.models.containers import Container
from playwright.sync_api import sync_playwright
from fake_useragent import UserAgent
from typing import Dict, List, TypedDict
import json
import time
import httpx

from urllib.parse import urlparse, urlunparse


class ProxyConf(TypedDict):
    server: str
    username: str
    password: str


class AuthData(TypedDict):
    jwt: str
    cookies: List[Dict]
    user_agent: str


def get_ws_url():
    r = httpx.get(
        "http://chrome-headless-temp:9222/json/version", headers={"Host": "localhost"}
    )
    r.raise_for_status()
    u = urlparse(r.json()["webSocketDebuggerUrl"])
    return urlunparse(u._replace(netloc=f"chrome-headless-temp:{u.port or 9222}"))


def spawn_headless_chrome_container(timeout: int = 120, interval: int = 3) -> Container:
    """
    Spawns a headless Chrome container and waits until it is ready.

    It checks for both the container status and the availability of the remote debugging
    port (9222) on docker network.
    """
    client = docker.from_env()
    container_name = "chrome-headless-temp"

    try:
        existing = client.containers.get(container_name)
        existing.remove(force=True)
    except docker.errors.NotFound:
        pass

    container = client.containers.run(
        "zenika/alpine-chrome:with-puppeteer",
        name=container_name,
        command=(
            "chromium-browser "
            "--no-sandbox "
            "--headless "
            "--disable-gpu "
            "--remote-debugging-address=0.0.0.0 "
            "--remote-debugging-port=9222"
        ),
        shm_size="2gb",
        detach=True,
        network="dagster_network",
    )

    elapsed_time = 0
    while elapsed_time < timeout:
        try:
            resp = httpx.get(
                "http://chrome-headless-temp:9222/json/version",
                timeout=1.0,
                headers={"Host": "localhost"},
            )
            print(resp.json())
            if resp.status_code == 200 and "webSocketDebuggerUrl" in resp.json():
                return container
        except Exception:
            pass

        time.sleep(interval)
        elapsed_time += interval

    container.stop()
    container.remove()
    raise TimeoutError("Headless Chrome did not become ready before timeout.")


def launch_browser_and_get_auth(proxy_conf: ProxyConf) -> AuthData:
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

    chrome_container = spawn_headless_chrome_container()

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(get_ws_url())
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
    finally:
        chrome_container.stop()
        chrome_container.remove()


def send_authenticated_request(auth_data: AuthData):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {auth_data['jwt']}",
        "Connection": "keep-alive",
        "DNT": "1",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Origin": "https://procurement-portal.novascotia.ca",
        "Referer": "https://procurement-portal.novascotia.ca/tenders",
        "User-Agent": auth_data["user_agent"],
    }

    records = 20
    url = f"https://procurement-portal.novascotia.ca/procurementui/tenders?page=1&numberOfRecords={records}&sortType=POSTED_DATE_DESC&keyword="
    body = {"filters": [{"key": "tenderStatus", "values": ["AWARDED"]}]}

    cookies = httpx.Cookies()
    for cookie in auth_data["cookies"]:
        cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])

    with httpx.Client(cookies=cookies, headers=headers, timeout=30) as client:
        response = client.post(url, json=body)
        response.raise_for_status()
        return response.json()
