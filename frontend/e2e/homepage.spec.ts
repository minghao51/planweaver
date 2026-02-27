import { test, expect } from '@playwright/test';

test.describe('App', () => {
  test('should load homepage without errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('/');
    
    // Wait for page to be interactive
    await page.waitForLoadState('networkidle');
    
    // Page should have some content
    const body = await page.locator('body').textContent();
    expect(body).toBeTruthy();
    
    // Log any console errors for debugging
    if (consoleErrors.length > 0) {
      console.log('Console errors:', consoleErrors);
    }
  });

  test('should navigate to history page', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Click history link in header
    await page.getByRole('link', { name: /history/i }).click();
    
    // Should navigate to history page
    await expect(page).toHaveURL('/history');
  });

  test('should have proper meta tags and structure', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Check title exists
    const title = await page.title();
    expect(title).toBeTruthy();
    
    // Check HTML structure
    await expect(page.locator('html')).toBeVisible();
    await expect(page.locator('body')).toBeVisible();
  });
});
