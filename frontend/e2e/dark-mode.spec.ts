import { test, expect, type Page } from "@playwright/test";

async function authenticateViaStorage(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("access_token", "test-token");
  });
}

test.describe("Dark mode", () => {
  test.beforeEach(async ({ page }) => {
    authenticateViaStorage(page);
  });

  test("toggle button switches to dark mode", async ({ page }) => {
    await page.goto("/dashboard");

    const toggleBtn = page.getByRole("button", { name: "Toggle dark mode" });
    await expect(toggleBtn).toBeVisible();

    // Click to enable dark mode
    await toggleBtn.click();

    // The <html> element should have the "dark" class
    const htmlEl = page.locator("html");
    await expect(htmlEl).toHaveClass(/dark/);
  });

  test("toggle button switches back to light mode", async ({ page }) => {
    // Seed dark mode preference
    await page.addInitScript(() => {
      localStorage.setItem("healthos-theme", "dark");
    });
    await page.goto("/dashboard");

    const htmlEl = page.locator("html");
    await expect(htmlEl).toHaveClass(/dark/);

    // Toggle back to light
    const toggleBtn = page.getByRole("button", { name: "Toggle dark mode" });
    await toggleBtn.click();

    await expect(htmlEl).not.toHaveClass(/dark/);
  });

  test("persists theme choice in localStorage", async ({ page }) => {
    await page.goto("/dashboard");

    const toggleBtn = page.getByRole("button", { name: "Toggle dark mode" });
    await toggleBtn.click();

    const stored = await page.evaluate(() => localStorage.getItem("healthos-theme"));
    expect(stored).toBe("dark");

    // Toggle again
    await toggleBtn.click();
    const storedAfter = await page.evaluate(() => localStorage.getItem("healthos-theme"));
    expect(storedAfter).toBe("light");
  });

  test("respects system preference when no stored theme", async ({ page }) => {
    // Emulate dark color scheme at OS level
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto("/dashboard");

    // The inline script in layout.tsx should add the dark class based on
    // prefers-color-scheme when there is no stored theme
    const htmlEl = page.locator("html");
    await expect(htmlEl).toHaveClass(/dark/);
  });

  test("respects system preference for light mode", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/dashboard");

    const htmlEl = page.locator("html");
    await expect(htmlEl).not.toHaveClass(/dark/);
  });
});
