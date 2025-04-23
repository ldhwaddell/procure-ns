import asyncio
import random
from typing import Awaitable, Callable, Dict, List, Optional, TypedDict
from urllib.parse import quote

import httpx
from dagster import get_dagster_logger


class ProxyConf(TypedDict):
    server: str
    username: str
    password: str


class AuthData(TypedDict):
    jwt: str
    cookies: List[Dict]
    user_agent: str


def table_exists(conn, table_name: str) -> bool:
    return (
        conn.execute(
            """
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE lower(table_name) = lower(?)
            """,
            [table_name],
        ).fetchone()[0]
        > 0
    )


def send_authenticated_request(auth_data: AuthData, records: int):
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

    url = f"https://procurement-portal.novascotia.ca/procurementui/tenders?page=1&numberOfRecords={records}&sortType=POSTED_DATE_DESC&keyword="
    body = {"filters": [{"key": "tenderStatus", "values": ["AWARDED"]}]}

    cookies = httpx.Cookies()
    for cookie in auth_data["cookies"]:
        cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])

    with httpx.Client(cookies=cookies, headers=headers, timeout=30) as client:
        response = client.post(url, json=body)
        response.raise_for_status()
        return response.json()


class ProxyRotator:
    def __init__(self, limit: int, get_config: Callable[[], ProxyConf]):
        self._limit = limit
        self._lock = asyncio.Lock()
        self._request_count = 0
        self._get_config = get_config
        self._proxy_conf = self._get_config()

    async def get_proxy(self) -> str:
        async with self._lock:
            self._request_count += 1
            if self._request_count >= self._limit:
                self._proxy_conf = self._get_config()
                self._request_count = 0
            return f"http://{self._proxy_conf['username']}:{self._proxy_conf['password']}@{self._proxy_conf['server']}"


class AuthRotator:
    def __init__(self, limit: int, get_auth: Callable[[], Awaitable[AuthData]]):
        self._limit = limit
        self._lock = asyncio.Lock()
        self._request_count = 0
        self._get_auth = get_auth
        self._auth: Optional[AuthData] = None
        self._init_lock = asyncio.Lock()

    async def get_auth(self) -> AuthData:
        async with self._lock:
            if self._auth is None:
                async with self._init_lock:
                    if self._auth is None:  # Double-checked locking
                        self._auth = await self._get_auth()
            elif self._request_count >= self._limit:
                self._auth = await self._get_auth()
                self._request_count = 0

            self._request_count += 1
            return self._auth


async def scrape_tender(
    tender_id: str,
    proxy_rotator: ProxyRotator,
    auth_rotator: AuthRotator,
    timeout: int,
    semaphore: asyncio.Semaphore,
):
    base_url = (
        "https://procurement-portal.novascotia.ca/procurementui/tenders?tenderId={}"
    )

    log = get_dagster_logger()
    id = quote(tender_id, safe="")
    url = base_url.format(id)
    async with semaphore:
        proxy_url = await proxy_rotator.get_proxy()
        auth = await auth_rotator.get_auth()

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {auth['jwt']}",
            "Connection": "keep-alive",
            "DNT": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Origin": "https://procurement-portal.novascotia.ca",
            "Referer": "https://procurement-portal.novascotia.ca/tenders",
            "User-Agent": auth["user_agent"],
            "Content-Type": "application/json",
        }

        cookies = httpx.Cookies()
        for cookie in auth["cookies"]:
            cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])

        async with httpx.AsyncClient(
            proxy=proxy_url, cookies=cookies, headers=headers, timeout=timeout
        ) as client:
            try:
                response = await client.post(url, json={})
                response.raise_for_status()

                log.info(f"Received code: {response.status_code} for url: {url}")

                data = response.json()
                tender_payloads = data.get("tenderDataList")

                await asyncio.sleep(random.uniform(0.5, 2))
                return tender_payloads

            except httpx.HTTPStatusError as e:
                log.error(
                    f"[HTTPStatusError] {e.response.status_code} {e.response.reason_phrase} for {url} — Response: {e.response.text}"
                )
                return None

            except httpx.RequestError as e:
                log.error(
                    f"[RequestError] Request failed due to network or connection issue: {e} for url: {url}"
                )
                return None

            except Exception as e:
                log.error(f"[UnhandledError] Unexpected error for url {url}: {e}")
                return None
