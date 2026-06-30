import { expect, test } from '@playwright/test'

test('redirects unauthenticated user to login', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL('/login')
})
