import time
import json

from fake_useragent import UserAgent


def build_remote_webdriver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    user_agent = UserAgent(platforms=["desktop"]).random
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("window-size=1920,1080")
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Remote(
        command_executor="http://localhost:4444/wd/hub",
        options=options,
    )

    ...


def build_remote_webdriver_selwire():
    from seleniumwire import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    user_agent = UserAgent(platforms=["desktop"]).random
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("window-size=1920,1080")
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    seleniumwire_options = {
        # Example: you can add a proxy or other intercept settings
        # 'proxy': {
        #     'http': 'http://user:pass@host:port',
        #     'https': 'https://user:pass@host:port',
        #     'no_proxy': 'localhost,127.0.0.1'
        # }
    }

    return webdriver.Remote(
        command_executor="http://localhost:4444/wd/hub",
        options=options,
        seleniumwire_options=seleniumwire_options,
    )


def build_remote_webdriver_selwire_proxy(): ...


def main():
    # url = "https://procurement-portal.novascotia.ca/tenders"
    url = "https://www.whatismyip.com/"
    driver = build_remote_webdriver_selwire()

    try:
        driver.get(url)

        print(driver.title)

        print(driver.page_source)

        # print("Waiting for 10")
        # driver.implicitly_wait(10)
        # for request in driver.requests:
        #     if request.response and "authenticate" in request.url:
        #         try:
        #             body = request.response.body.decode("utf-8")
        #             data = json.loads(body)
        #             token = data.get("jwttoken")
        #             if token:
        #                 print("Extracted Bearer Token:\n", token)
        #                 break
        #         except Exception as e:
        #             print("Failed to parse response:", e)
        # print("Waiting for 10 again")
        # time.sleep(10)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
