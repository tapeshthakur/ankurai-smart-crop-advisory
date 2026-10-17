const path = require("path");
const { test, expect } = require("@playwright/test");

const farmer = {
  id: 41,
  name: "Demo Farmer",
  email: "demo@example.test",
  role: "farmer",
};

const screenshotsDirectory = path.resolve(__dirname, "../../docs/screenshots");

async function mockDashboardApi(page) {
  await page.route("**/api/**", async (route) => {
    const { pathname } = new URL(route.request().url());
    if (pathname === "/api/auth/me") return route.fulfill({ json: { user: farmer } });
    if (pathname === "/api/predictions") return route.fulfill({ json: { predictions: [] } });
    if (pathname === "/api/market/overview") {
      return route.fulfill({ json: {
        crop: "wheat",
        season: "Rabi",
        mandi: {
          records: [
            { market: "Pune", district: "Pune", arrival_date: "2026-09-27", min_price: 2250, modal_price: 2480, max_price: 2610 },
            { market: "Nashik", district: "Nashik", arrival_date: "2026-09-26", min_price: 2320, modal_price: 2510, max_price: 2670 },
            { market: "Nagpur", district: "Nagpur", arrival_date: "2026-09-25", min_price: 2210, modal_price: 2430, max_price: 2580 },
          ],
          is_live: false,
          source: "Synthetic example data",
          fetched_at: "2026-09-28T09:00:00Z",
          errors: ["Synthetic documentation capture; no live market request was made."],
          summary: { latest_arrival_date: "2026-09-27" },
        },
        msp: { value: 2425, marketing_season: "RMS 2026-27", variants: [] },
        schemes: [],
        market_tip: "Compare local arrivals and quality requirements before choosing a sale date.",
        kvk: { name: "District Krishi Vigyan Kendra", contact: "Contact your local KVK" },
      } });
    }
    if (pathname === "/api/market/trends") return route.fulfill({ json: { records: [] } });
    return route.fulfill({ json: {} });
  });
}

test("refreshes the README desktop and mobile screenshots", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(screenshotsDirectory, "ankurai-homepage-desktop.png"), fullPage: true });

  await page.goto("/login");
  await page.screenshot({ path: path.join(screenshotsDirectory, "ankurai-sign-in-desktop.png"), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: path.join(screenshotsDirectory, "ankurai-sign-in-mobile.png") });

  await mockDashboardApi(page);
  await page.addInitScript((user) => {
    localStorage.setItem("smart_crop_token", "readme-demo-token");
    localStorage.setItem("smart_crop_user", JSON.stringify(user));
  }, farmer);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/dashboard");
  await expect(page.getByText(/welcome, demo farmer/i)).toBeVisible();
  await page.screenshot({ path: path.join(screenshotsDirectory, "ankurai-crop-advisory-desktop.png"), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.getByText("State", { exact: true }).last().scrollIntoViewIfNeeded();
  await page.evaluate(() => window.scrollBy(0, -80));
  await page.screenshot({ path: path.join(screenshotsDirectory, "ankurai-crop-advisory-mobile.png") });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("button", { name: /market.*schemes/i }).first().click();
  await expect(page.getByRole("heading", { name: /market and government support/i })).toBeVisible();
  await page.screenshot({ path: path.join(screenshotsDirectory, "ankurai-market-schemes-desktop-demo.png"), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("heading", { name: "Recent mandi records" }).scrollIntoViewIfNeeded();
  await page.evaluate(() => window.scrollBy(0, -120));
  await expect(page.getByRole("heading", { name: "Pune" })).toBeVisible();
  await page.screenshot({ path: path.join(screenshotsDirectory, "ankurai-market-prices-mobile-demo.png") });
});
