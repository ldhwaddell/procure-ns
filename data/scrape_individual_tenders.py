import json
import httpx
import random
import asyncio
from utils import resolve_proxy_ip, get_proxy_conf, rand, launch_browser_and_get_auth


class SingleSessionRetriever:
    def __init__(self, proxy_ip: str):
        proxy_conf = get_proxy_conf(proxy_ip)
        self._proxy_url = f"http://{proxy_conf['username']}:{proxy_conf['password']}@{proxy_conf['server']}"

    async def retrieve(self, url: str, timeout: int, auth_data):
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
            "Content-Type": "application/json",
        }

        cookies = httpx.Cookies()
        for cookie in auth_data["cookies"]:
            cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])

        async with httpx.AsyncClient(
            proxy=self._proxy_url, cookies=cookies, headers=headers, timeout=timeout
        ) as client:
            try:
                response = await client.post(url, json={})
                response.raise_for_status()
                return await response.json()
            except httpx.HTTPStatusError as e:
                print(f"Request failed: {e}, Type: {type(e).__name__}")
                return None


class MultiSessionRetriever:
    def __init__(self, session_requests_limit, session_failures_limit, proxy_ip):
        self.session_requests_limit = session_requests_limit
        self.session_failures_limit = session_failures_limit
        self._requests = 0
        self._session_retriever = SingleSessionRetriever(proxy_ip)

    async def retrieve(
        self, tenders, timeout, parallel_sessions_limit, callback, auth_data
    ):
        semaphore = asyncio.Semaphore(parallel_sessions_limit)
        tasks = [
            self._handle_tender(tender, timeout, semaphore, callback, auth_data)
            for tender in tenders
        ]
        await asyncio.gather(*tasks)

    async def _handle_tender(self, tender, timeout, semaphore, callback, auth_data):
        base_url = (
            "https://procurement-portal.novascotia.ca/procurementui/tenders?tenderId={}"
        )
        async with semaphore:
            self._rotate_session_if_needed()

            id = tender.get("tenderId")
            url = base_url.format(id)
            # url = "https://geo.brdtest.com/mygeo.json"

            data = await self._session_retriever.retrieve(url, timeout, auth_data)
            if data:
                await callback(tender, data)
                await asyncio.sleep(rand())
            else:
                print(f"[WARNING]: No data received for {tender}")

    def _rotate_session_if_needed(self):
        self._requests += 1
        if self._requests >= self.session_requests_limit:
            self._proxy_ip = resolve_proxy_ip()
            self._session_retriever = SingleSessionRetriever(self._proxy_ip)
            self._requests = 0


async def callback(tender, data):
    print(f"[SUCCESS] Tender {tender['tenderId']} | Size: {len(data)} bytes")


def main():
    with open("./tenders.json", "r") as f:
        tenders = json.load(f)

    ip = resolve_proxy_ip()
    proxy_conf = get_proxy_conf(ip)
    auth_data = launch_browser_and_get_auth(proxy_conf)

    retriever = MultiSessionRetriever(
        session_requests_limit=10,
        session_failures_limit=2,
        proxy_ip=ip,
        auth_data=auth_data,
    )

    asyncio.run(
        retriever.retrieve(
            tenders=tenders["tenderDataList"][:5],
            timeout=10,
            parallel_sessions_limit=3,
            callback=callback,
        )
    )


if __name__ == "__main__":
    main()
