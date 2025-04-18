from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright

ua = UserAgent(platforms="desktop").random

print(f"$$$$$$$$$$$$$$$$$$$$${ua}$$$$$$$$$$$$$$$$$$$$$$")
