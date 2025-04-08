import time
import json

from utils import build_remote_web_driver


def main():
    url = "https://procurement-portal.novascotia.ca/tenders"
    driver = build_remote_web_driver(use_proxy=True, headless=False)

    try:
        driver.get(url)

        print("Waiting for 10")
        driver.implicitly_wait(10)
        for request in driver.requests:
            if request.response and "authenticate" in request.url:
                try:
                    body = request.response.body.decode("utf-8")
                    data = json.loads(body)
                    token = data.get("jwttoken")
                    if token:
                        print("Extracted Bearer Token:\n", token)
                        break
                except Exception as e:
                    print("Failed to parse response:", e)
        print("Waiting for 10 again")
        time.sleep(10)
    finally:
        driver.quit()

    return []


if __name__ == "__main__":
    main()
