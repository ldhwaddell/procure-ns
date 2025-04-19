import { chromium } from "playwright-chromium";
import http from "http";

const getWsUrl = async () => {
  return new Promise((resolve, reject) => {
    http
      .get("http://localhost:9222/json/version", (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          const json = JSON.parse(data);
          resolve(json.webSocketDebuggerUrl);
        });
      })
      .on("error", reject);
  });
};

const run = async () => {
  const wsUrl = await getWsUrl();
  const browser = await chromium.connectOverCDP(wsUrl);

  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto("https://example.com", { waitUntil: "domcontentloaded" });
  const title = await page.title();

  console.log(`✅ Connected and loaded page with title: "${title}"`);

  await browser.close();
};

run();
