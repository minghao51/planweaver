import { expect, test } from '@playwright/test';
import { installApiMocks } from './fixtures';

test.beforeEach(async ({ page }) => {
  await installApiMocks(page);
});

test('creates a new plan and lands in the clarification stage', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: /start a new plan/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /blog generation/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /planner fast/i })).toBeVisible();

  await page.getByPlaceholder(/architect a microservices deployment/i).fill('Launch a support portal for customer success.');
  await page.getByRole('button', { name: /commence planning/i }).click();

  await expect(page).toHaveURL(/\/plans\/session-question$/);
  await expect(page.getByRole('heading', { name: /clarification required/i })).toBeVisible();
  await page.getByPlaceholder(/provide context or answer here/i).fill('Customer success managers triaging inbound requests.');
  await expect(page.getByRole('button', { name: /submit implementation context/i })).toBeEnabled();
});
