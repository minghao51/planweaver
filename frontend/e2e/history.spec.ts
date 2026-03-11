import { expect, test } from '@playwright/test';
import { installApiMocks } from './fixtures';

test.beforeEach(async ({ page }) => {
  await installApiMocks(page);
});

test('filters session history by text and status', async ({ page }) => {
  await page.goto('/history');

  await expect(page.getByRole('heading', { name: /weave history/i })).toBeVisible();
  await expect(page.getByText(/build an internal release checklist workflow/i)).toBeVisible();
  await expect(page.getByText(/migrate analytics dashboards to the new schema/i)).toBeVisible();

  await page.getByPlaceholder(/search by intent or id/i).fill('analytics');
  await expect(page.getByText(/migrate analytics dashboards to the new schema/i)).toBeVisible();
  await expect(page.getByText(/build an internal release checklist workflow/i)).toHaveCount(0);

  await page.getByRole('combobox').selectOption('COMPLETED');
  await expect(page.getByText(/migrate analytics dashboards to the new schema/i)).toBeVisible();
});
