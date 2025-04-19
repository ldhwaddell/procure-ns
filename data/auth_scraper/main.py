from playwright.sync_api import sync_playwright


def run():
    with sync_playwright() as p:
        # Launch Chromium with CDP enabled
        browser = p.chromium.launch(
            headless=True, args=["--remote-debugging-port=9222"]
        )
        context = browser.new_context()
        page = context.new_page()

        # Log all network requests
        page.on("request", lambda request: print(f"➡️  {request.method} {request.url}"))
        page.on(
            "response", lambda response: print(f"⬅️  {response.status} {response.url}")
        )

        page.goto("https://example.com")
        page.wait_for_timeout(3000)  # Wait for a few seconds to capture all requests

        browser.close()


if __name__ == "__main__":
    run()
