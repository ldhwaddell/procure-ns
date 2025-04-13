from typing import Dict
import json
import httpx
from utils import resolve_proxy_ip, get_proxy_conf, launch_browser_and_get_auth


def send_authenticated_request(auth_data: Dict[str, str]):
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

    records = 50000
    url = f"https://procurement-portal.novascotia.ca/procurementui/tenders?page=1&numberOfRecords={records}&sortType=POSTED_DATE_DESC&keyword="
    body = {"filters": [{"key": "tenderStatus", "values": ["AWARDED"]}]}

    cookies = httpx.Cookies()
    for cookie in auth_data["cookies"]:
        cookies.set(cookie["name"], cookie["value"], domain=cookie["domain"])

    with httpx.Client(cookies=cookies, headers=headers, timeout=30) as client:
        response = client.post(url, json=body)
        response.raise_for_status()
        return response.json()


def save_tenders(data: Dict):
    with open("tenders.json", "w") as f:
        json.dump(data, f, indent=2)
    return "tenders.json"


def scrape_tenders_job():
    ip = resolve_proxy_ip()
    proxy_conf = get_proxy_conf(ip)
    auth_data = launch_browser_and_get_auth(proxy_conf)
    data = send_authenticated_request(auth_data)
    save_tenders(data)


scrape_tenders_job()
