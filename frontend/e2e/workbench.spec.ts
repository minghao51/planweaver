import { expect, test } from '@playwright/test';
import { installApiMocks } from './fixtures';

test.beforeEach(async ({ page }) => {
  await installApiMocks(page);
});

test('opens the workbench and adds a manual baseline candidate', async ({ page }) => {
  await page.goto('/workbench');

  await expect(page.getByRole('heading', { name: /open a real session/i })).toBeVisible();

  await page.getByRole('button', { name: /build an internal release checklist workflow/i }).click();
  await expect(page.getByRole('button', { name: /task-first rollout/i })).toBeVisible();
  await page.getByRole('button', { name: /open workbench/i }).click();

  await expect(page.getByRole('heading', { name: /planning workbench/i })).toBeVisible();
  await expect(page.getByText(/reduced handoffs and simplified approval gates/i)).toBeVisible();

  await page.getByRole('button', { name: /manual plan/i }).click();
  await page.getByLabel(/^title$/i).fill('Operator checklist baseline');
  await page.getByLabel(/summary/i).fill('A concise manual rollout baseline.');
  await page.getByLabel(/plan steps/i).fill('Audit current release checklist\nPilot the flow with one team');
  await page.getByRole('button', { name: /add manual plan/i }).click();

  await expect(page.getByText(/manual plan added to the candidate pool/i)).toHaveCount(0);
  await expect(page.getByRole('columnheader', { name: /operator checklist baseline/i })).toBeVisible();
});
