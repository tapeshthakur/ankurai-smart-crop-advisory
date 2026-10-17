const { test, expect } = require("@playwright/test");

const farmer = {
  id: 41,
  name: "Test Farmer",
  email: "farmer@example.test",
  role: "farmer",
};

async function mockApi(page) {
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === "/api/auth/login" && request.method() === "POST") {
      return route.fulfill({
        json: { access_token: "e2e-token", user: farmer },
      });
    }
    if (path === "/api/auth/signup" && request.method() === "POST") {
      return route.fulfill({
        status: 201,
        json: { message: "User registered successfully.", user: farmer },
      });
    }
    if (path === "/api/auth/me") {
      return route.fulfill({ json: { user: farmer } });
    }
    if (path === "/api/predictions") {
      return route.fulfill({ json: { predictions: [] } });
    }
    if (path === "/api/market/overview") {
      return route.fulfill({ json: {
        mandi: {
          records: [{ market: "Pune", district: "Pune", arrival_date: "2026-09-27", min_price: 2300, modal_price: 2500, max_price: 2750 }],
          is_live: true,
          source: "AGMARKNET",
          fetched_at: "2026-09-28T09:00:00Z",
          summary: {},
        },
        msp: { value: 2200, marketing_season: "2026-27" },
        schemes: [],
      } });
    }
    if (path === "/api/market/trends") {
      return route.fulfill({ json: { records: [] } });
    }
    return route.fulfill({ json: {} });
  });
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("farmer can create an account and reach sign-in", async ({ page }) => {
  let signupPayload;
  await page.route("**/api/auth/signup", async (route) => {
    signupPayload = route.request().postDataJSON();
    await route.fulfill({
      status: 201,
      json: { message: "User registered successfully.", user: farmer },
    });
  });

  await page.goto("/signup");
  await page.getByLabel("Name", { exact: true }).fill("Test Farmer");
  await page.getByLabel("Email", { exact: true }).fill(farmer.email);
  await page.getByLabel("Password", { exact: true }).fill("fieldtest123");
  await page.getByRole("button", { name: /create account|sign up|register/i }).click();

  await expect(page.getByText(/account created|registered successfully|success/i).first()).toBeVisible();
  expect(signupPayload).toMatchObject({ name: farmer.name, email: farmer.email, role: "farmer" });
  await expect(page).toHaveURL(/\/login$/, { timeout: 5000 });
});

test("farmer can sign in and access the protected dashboard", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(farmer.email);
  await page.getByLabel("Password", { exact: true }).fill("fieldtest123");
  await page.getByRole("button", { name: /sign in|login|log in/i }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText(/welcome, test farmer/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /recent predictions/i })).toBeVisible();
});

test("farmer dashboard switches between market and assistant modules", async ({ page }) => {
  await page.addInitScript((currentFarmer) => {
    localStorage.setItem("smart_crop_token", "e2e-token");
    localStorage.setItem("smart_crop_user", JSON.stringify(currentFarmer));
  }, farmer);
  await page.goto("/dashboard");
  await expect(page.getByText(/welcome, test farmer/i)).toBeVisible();

  await page.getByRole("button", { name: /market.*schemes/i }).first().click();
  await expect(page.getByRole("heading", { name: /market and government support/i })).toBeVisible();

  await page.getByRole("button", { name: /ask ai/i }).first().click();
  await expect(page.getByRole("heading", { name: "Ask AI" })).toBeVisible();
  await expect(page.locator("textarea")).toBeVisible();
});

test("market records fit a phone viewport without horizontal page overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript((currentFarmer) => {
    localStorage.setItem("smart_crop_token", "e2e-token");
    localStorage.setItem("smart_crop_user", JSON.stringify(currentFarmer));
  }, farmer);
  await page.goto("/dashboard");
  await page.getByRole("button", { name: /market.*schemes/i }).last().click();

  await expect(page.getByRole("heading", { name: /market and government support/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Pune" })).toBeVisible();
  await expect(page.locator(".market-records__table")).toBeHidden();
  const pageWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(pageWidth).toBeLessThanOrEqual(390);
});
