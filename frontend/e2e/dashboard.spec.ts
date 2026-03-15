import { test, expect } from "@playwright/test";

test.describe("Dashboard Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("access_token", "test-token");
    });
    await page.goto("/dashboard");
  });

  test("should load dashboard page", async ({ page }) => {
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator("main")).toBeVisible();
  });

  test("should display KPI/metric cards", async ({ page }) => {
    const cards = page.locator(".metric-card, .card");
    await expect(cards.first()).toBeVisible({ timeout: 10000 });
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
  });

  test("should show page title in topbar", async ({ page }) => {
    const header = page.locator("header");
    await expect(header).toBeVisible();
    await expect(header).toContainText("Command Center");
  });

  test("should have responsive layout", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    const sidebar = page.locator("aside");
    await expect(sidebar).toBeVisible();

    await page.setViewportSize({ width: 375, height: 667 });
    await expect(sidebar).not.toBeVisible();

    const menuButton = page.locator('button[aria-label="Toggle sidebar"]');
    await expect(menuButton).toBeVisible();
  });

  test("should display connection status", async ({ page }) => {
    const status = page.locator("text=Connected");
    await expect(status).toBeVisible();
  });

  test("should have working navigation links", async ({ page }) => {
    const patientsLink = page.locator('aside a[href="/patients"]');
    if (await patientsLink.isVisible()) {
      await patientsLink.click();
      await expect(page).toHaveURL(/\/patients/);
    }
  });

  test("should render without errors", async ({ page }) => {
    await page.waitForTimeout(2000);
    await expect(page.locator("main")).toBeVisible();
  });
});
