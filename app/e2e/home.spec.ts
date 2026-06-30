import { expect, test } from '@playwright/test'

test('redirects unauthenticated users to login', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL('/login')
})
