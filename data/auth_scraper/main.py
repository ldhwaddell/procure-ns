import os
import json
from dagster_pipes import open_dagster_pipes, emit


def main():
    conf = json.loads(os.environ["PROXY_CONF"])
    result = {"jwt": "token123", "proxy": conf}

    with open_dagster_pipes():
        emit("auth", result)


if __name__ == "__main__":
    main()
# import json
# import sys
# from playwright.sync_api import sync_playwright
# from fake_useragent import UserAgent
#
# TARGET_URL = "https://procurement-portal.novascotia.ca/tenders"
# WATCH_REQUEST = "https://procurement-portal.novascotia.ca/procurementui/authenticate"
#
#
# def launch_browser_and_get_auth(proxy_conf):
#     jwt_token = None
#     ua = UserAgent(platforms="desktop").random
#
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
#         context = browser.new_context(
#             # proxy={
#             #     "server": f"http://{proxy_conf['server']}",
#             #     "username": proxy_conf["username"],
#             #     "password": proxy_conf["password"],
#             # },
#             user_agent=ua,
#             viewport={"width": 1280, "height": 800},
#         )
#         context.add_init_script("""
#         Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
#         Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
#         Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
#         """)
#
#         def on_response(response):
#             nonlocal jwt_token
#             if response.url == WATCH_REQUEST:
#                 try:
#                     data = response.json()
#                 except Exception:
#                     data = json.loads(response.text())
#                 jwt_token = data.get("jwttoken")
#
#         context.on("response", on_response)
#
#         page = context.new_page()
#         page.goto(TARGET_URL, timeout=60000, wait_until="domcontentloaded")
#         page.wait_for_timeout(3000)
#         cookies = context.cookies()
#         browser.close()
#
#     if not jwt_token:
#         raise Exception("No token received")
#
#     return {
#         "jwt": jwt_token,
#         "cookies": cookies,
#         "user_agent": ua,
#     }
#
#
# if __name__ == "__main__":
#     proxy_conf = {
#         "server": "",
#         "username": "",
#         "password": "",
#     }
#
#     result = launch_browser_and_get_auth(proxy_conf)
#     json.dump(result, sys.stdout)
