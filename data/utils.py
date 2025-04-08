import asyncio
import os
import random
import socket
import sys
import time
from typing import Optional

import aiohttp
from dotenv import load_dotenv
from fake_useragent import UserAgent
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from seleniumwire import webdriver


def rand(min: int = 1, max: int = 4):
    """Get a random interval in [min, max]"""
    return random.uniform(min, max)


def resolve_super_proxy() -> str:
    """Resolve and cache the proxy server IP to avoid repeated DNS lookups."""
    return socket.gethostbyname("brd.superproxy.io")


def get_proxy_url(username: str, password: str, proxy_ip: Optional[str] = None) -> str:
    """Generate a rotating proxy URL with a session ID."""
    proxy_ip = proxy_ip or resolve_super_proxy()
    port = 33335
    session_id = str(random.random())
    return f"{username}-session-{session_id}:{password}@{proxy_ip}:{port}"


def build_remote_web_driver(
    use_proxy: bool = False,
    headless: bool = True,
    session_requests_limit: int = 5,
    download_dir: Optional[str] = None,
) -> webdriver.Remote:
    """
    Builds and returns a Chrome WebDriver with specified options.

    :param use_proxy: Whether to use a proxy.
    :param headless: Whether to run Chrome in headless mode.
    :param session_requests_limit: Number of requests per proxy session.
    :param download_dir: Optional directory to save downloaded files.
    :return: A configured Chrome WebDriver.
    """

    load_dotenv()

    username = os.getenv("PROXY_USER")
    password = os.getenv("PROXY_PASS")

    proxy_ip = resolve_super_proxy() if use_proxy else None
    proxy_url = get_proxy_url(username, password, proxy_ip) if use_proxy else None

    options = Options()
    seleniumwire_options = {}
    user_agent = UserAgent(platforms=["desktop"]).random
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("window-size=1920,1080")

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

    if use_proxy:
        seleniumwire_options["proxy"] = {
            "https": f"https://{proxy_url}",
            "http": f"http://{proxy_url}",
        }
        options.add_argument("--ignore-certificate-errors-spki-list")
        options.add_argument("--ignore-ssl-errors")

    if download_dir:
        os.makedirs(download_dir, exist_ok=True)
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)

    return webdriver.Remote(
        command_executor="http://localhost:4444/wd/hub",
        options=options,
        seleniumwire_options=seleniumwire_options,
        desired_capabilities=DesiredCapabilities.CHROME,
    )


def build_web_driver(
    use_proxy: bool = False,
    headless: bool = True,
    session_requests_limit: int = 5,
    download_dir: Optional[str] = None,
) -> webdriver.Chrome:
    """
    Builds and returns a Chrome WebDriver with specified options.

    :param use_proxy: Whether to use a proxy.
    :param headless: Whether to run Chrome in headless mode.
    :param session_requests_limit: Number of requests per proxy session.
    :param download_dir: Optional directory to save downloaded files.
    :return: A configured Chrome WebDriver.
    """

    load_dotenv()

    username = os.getenv("PROXY_USER")
    password = os.getenv("PROXY_PASS")

    proxy_ip = resolve_super_proxy() if use_proxy else None
    proxy_url = get_proxy_url(username, password, proxy_ip) if use_proxy else None

    options = Options()
    seleniumwire_options = {}
    user_agent = UserAgent(platforms=["desktop"]).random
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("window-size=1920,1080")

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

    if use_proxy:
        seleniumwire_options["proxy"] = {
            "https": f"https://{proxy_url}",
            "http": f"http://{proxy_url}",
        }
        options.add_argument("--ignore-certificate-errors-spki-list")
        options.add_argument("--ignore-ssl-errors")

    if download_dir:
        os.makedirs(download_dir, exist_ok=True)
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)

    return webdriver.Chrome(options=options, seleniumwire_options=seleniumwire_options)


class SingleSessionRetriever:
    def __init__(self, username, password):
        self._username = username
        self._password = password

        self._proxy_url = f"http://{get_proxy_url(username, password)}"

    async def retrieve(self, url, timeout):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url, proxy=self._proxy_url, timeout=timeout
                ) as response:
                    response.raise_for_status()
                    data = await response.read()
                    headers = response.headers
                    return data, headers
            except Exception as e:
                print(f"Request failed: {e}, Type: {type(e).__name__}")
                sys.exit(f"ERROR WITH {url}")
                return None, None


class MultiSessionRetriever:
    def __init__(self, session_requests_limit, session_failures_limit):
        load_dotenv()
        self._username = os.getenv("PROXY_USER")
        self._password = os.getenv("PROXY_PASS")
        self.session_requests_limit = session_requests_limit
        self.session_failures_limit = session_failures_limit
        self._proxy_ip = resolve_super_proxy()
        self._sessions_stack = []
        self._requests = 0

    async def retrieve(self, cases, timeout, parallel_sessions_limit, callback):
        semaphore = asyncio.Semaphore(parallel_sessions_limit)
        tasks = [
            self._retrieve_single(case, timeout, semaphore, callback) for case in cases
        ]
        await asyncio.gather(*tasks)

    async def _retrieve_single(self, case, timeout, semaphore, callback):
        async with semaphore:
            if (
                not self._sessions_stack
                or self._requests >= self.session_requests_limit
            ):
                if self._sessions_stack:
                    self._requests = 0
                session_retriever = SingleSessionRetriever(
                    self._username, self._password
                )
                self._sessions_stack.append(session_retriever)
            else:
                session_retriever = self._sessions_stack[-1]
            self._requests += 1
            url = case.get("pdf_url")
            data, headers = await session_retriever.retrieve(url, timeout)
            if data is not None:
                await callback(case, data, headers)
                await asyncio.sleep(rand())
            else:
                print(f"[WARNING]: No data received for {case}")


if __name__ == "__main__":
    driver = build_web_driver(use_proxy=True, headless=False)
    driver.get("https://geo.brdtest.com/welcome.txt?product=dc&method=native")
    time.sleep(10)
    driver.quit()
