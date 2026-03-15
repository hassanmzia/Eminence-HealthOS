import { test, expect, type Page } from "@playwright/test";

async function authenticateViaStorage(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("access_token", "test-token");
  });
}

test.describe("Command Palette (Cmd+K)", () => {
  test.beforeEach(async ({ page }) => {
    authenticateViaStorage(page);
    await page.goto("/dashboard");
  });

  test("Cmd+K opens command palette", async ({ page }) => {
    await page.keyboard.press("Meta+k");
    const palette = page.locator('input[placeholder="Search pages, features, tools..."]');
    await expect(palette).toBeVisible();
    await expect(palette).toBeFocused();
  });

  test("Ctrl+K opens command palette (non-Mac)", async ({ page }) => {
    await page.keyboard.press("Control+k");
    const palette = page.locator('input[placeholder="Search pages, features, tools..."]');
    await expect(palette).toBeVisible();
  });

  test("search filtering narrows results", async ({ page }) => {
    await page.keyboard.press("Meta+k");
    const input = page.locator('input[placeholder="Search pages, features, tools..."]');
    await input.fill("Telehealth");

    // Should show the Telehealth result
    await expect(page.getByRole("button", { name: /Telehealth/ })).toBeVisible();

    // Items that do not match should be hidden
    await expect(page.locator('[data-index]')).toHaveCount(1);
  });

  test("shows no results message for gibberish query", async ({ page }) => {
    await page.keyboard.press("Meta+k");
    const input = page.locator('input[placeholder="Search pages, features, tools..."]');
    await input.fill("xyznonexistent999");

    await expect(page.getByText(/No results for/)).toBeVisible();
  });

  test("keyboard navigation with arrow keys and enter", async ({ page }) => {
    await page.keyboard.press("Meta+k");
    const input = page.locator('input[placeholder="Search pages, features, tools..."]');
    await input.fill("Patient");

    // Wait for results to appear
    await expect(page.locator('[data-index="0"]')).toBeVisible();

    // Press ArrowDown to move selection
    await page.keyboard.press("ArrowDown");

    // The second item should now be highlighted
    const secondItem = page.locator('[data-index="1"]');
    await expect(secondItem).toHaveClass(/bg-healthos-50/);

    // Press Enter to navigate
    await page.keyboard.press("Enter");

    // Palette should close
    await expect(input).toBeHidden();
  });

  test("Escape closes the command palette", async ({ page }) => {
    await page.keyboard.press("Meta+k");
    const input = page.locator('input[placeholder="Search pages, features, tools..."]');
    await expect(input).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(input).toBeHidden();
  });

  test("clicking backdrop closes the command palette", async ({ page }) => {
    await page.keyboard.press("Meta+k");
    const input = page.locator('input[placeholder="Search pages, features, tools..."]');
    await expect(input).toBeVisible();

    // Click the backdrop overlay
    const backdrop = page.locator(".fixed.inset-0 .bg-black\\/50, .fixed.inset-0.bg-black\\/50").first();
    await backdrop.click({ position: { x: 10, y: 10 } });
    await expect(input).toBeHidden();
  });
});
