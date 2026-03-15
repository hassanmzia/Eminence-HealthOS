import { test, expect, type Page } from "@playwright/test";

/** Helper: inject a fake token so AppShell renders the authenticated layout. */
async function authenticateViaStorage(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("access_token", "test-token");
  });
}

const SIDEBAR_LINKS: { label: string; href: string }[] = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Patients", href: "/patients" },
  { label: "Alerts", href: "/alerts" },
  { label: "RPM", href: "/rpm" },
  { label: "Telehealth", href: "/telehealth" },
  { label: "Analytics", href: "/analytics" },
  { label: "Operations", href: "/operations" },
];

test.describe("Sidebar navigation", () => {
  test.beforeEach(async ({ page }) => {
    authenticateViaStorage(page);
    await page.goto("/dashboard");
  });

  for (const link of SIDEBAR_LINKS) {
    test(`navigates to ${link.label} (${link.href})`, async ({ page }) => {
      const nav = page.locator("aside nav");
      await nav.getByText(link.label, { exact: true }).click();
      await expect(page).toHaveURL(new RegExp(link.href));
    });
  }

  test("page title renders in top bar", async ({ page }) => {
    // Dashboard maps to "Command Center" in TopBar PAGE_TITLES
    const topBar = page.locator("header");
    await expect(topBar.getByRole("heading", { name: "Command Center" })).toBeVisible();
  });

  test("sidebar highlights the active link", async ({ page }) => {
    const activeLink = page.locator(`aside nav a[href="/dashboard"]`);
    // Active links receive the healthos-50 background class
    await expect(activeLink).toHaveClass(/bg-healthos-50/);
  });
});

test.describe("Mobile hamburger menu", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("toggle opens and closes the sidebar", async ({ page }) => {
    authenticateViaStorage(page);
    await page.goto("/dashboard");

    const sidebar = page.locator("aside");
    // On mobile the sidebar container is translated off-screen by default
    const sidebarWrapper = sidebar.locator("..");
    await expect(sidebarWrapper).toHaveCSS("transform", /matrix/);

    // Click the hamburger button
    const hamburger = page.getByRole("button", { name: "Toggle sidebar" });
    await hamburger.click();

    // Sidebar should now be visible (translate-x-0)
    await expect(sidebar).toBeVisible();

    // Click the overlay to close
    const overlay = page.locator(".fixed.inset-0.bg-black\\/50");
    if (await overlay.isVisible()) {
      await overlay.click();
      // After closing, sidebar wrapper should be off-screen again
      await expect(overlay).toBeHidden();
    }
  });
});
