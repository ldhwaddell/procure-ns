import httpx
import random
import asyncio
from utils import resolve_proxy_ip, get_proxy_conf


class SingleSessionRetriever:
    def __init__(self, proxy_ip: str):
        proxy_conf = get_proxy_conf(proxy_ip)
        self._proxy_url = f"http://{proxy_conf['username']}:{proxy_conf['password']}@{proxy_conf['server']}"

    async def retrieve(self, url: str, timeout: int):
        async with httpx.AsyncClient(proxy=self._proxy_url, timeout=timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.content
                headers = response.headers
                return data, headers

            except Exception as e:
                print(f"Request failed: {e}, Type: {type(e).__name__}")
                return None, None


class MultiSessionRetriever:
    def __init__(self, session_requests_limit, session_failures_limit):
        self.session_requests_limit = session_requests_limit
        self.session_failures_limit = session_failures_limit
        self._requests = 0
        self._proxy_ip = resolve_proxy_ip()
        self._session_retriever = SingleSessionRetriever(self._proxy_ip)

    async def retrieve(self, tenders, timeout, parallel_sessions_limit, callback):
        semaphore = asyncio.Semaphore(parallel_sessions_limit)
        tasks = [
            self._handle_tender(tender, timeout, semaphore, callback)
            for tender in tenders
        ]
        await asyncio.gather(*tasks)

    async def _handle_tender(self, tender, timeout, semaphore, callback):
        base_url = (
            "https://procurement-portal.novascotia.ca/procurementui/tenders?tenderId={}"
        )
        async with semaphore:
            self._rotate_session_if_needed()

            id = tender.get("tenderId")
            # url = base_url.format(id)
            url = "https://geo.brdtest.com/mygeo.json"

            data, headers = await self._session_retriever.retrieve(url, timeout)
            if data:
                await callback(tender, data, headers)
                await asyncio.sleep(rand())
            else:
                print(f"[WARNING]: No data received for {tender}")

    def _rotate_session_if_needed(self):
        self._requests += 1
        if self._requests >= self.session_requests_limit:
            self._proxy_ip = resolve_proxy_ip()
            self._session_retriever = SingleSessionRetriever(self._proxy_ip)
            self._requests = 0


def main():
    async def callback(tender, data, headers):
        print(f"[SUCCESS] Tender {tender['tenderId']} | Size: {len(data)} bytes")

    # Fake tender list
    tenders = [{"tenderId": f"TID-{random.randint(1000, 9999)}"} for _ in range(10)]

    retriever = MultiSessionRetriever(
        session_requests_limit=10,
        session_failures_limit=2,
    )

    asyncio.run(
        retriever.retrieve(
            tenders=tenders,
            timeout=10,
            parallel_sessions_limit=3,
            callback=callback,
        )
    )


if __name__ == "__main__":
    main()
