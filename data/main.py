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

    public_ip = "178.156.171.122"
    proxy_port = 12345

    options = Options()
    user_agent = UserAgent(platforms=["desktop"]).random
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("window-size=1920,1080")
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument(f"--proxy-server={public_ip}:{proxy_port}")

    capabilities = options.to_capabilities()

    return webdriver.Remote(
        command_executor="http://localhost:4444/wd/hub",
        desired_capabilities=capabilities,
        seleniumwire_options={
            "auto_config": False,
            "addr": public_ip,
            "port": proxy_port,
        },
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
