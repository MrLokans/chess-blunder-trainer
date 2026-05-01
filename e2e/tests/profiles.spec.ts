import type { APIRequestContext, Page } from '@playwright/test';
import { test, expect } from '../fixtures/app.fixture';

// `DrNykterstein` is Magnus Carlsen's Lichess account — well-known stable
// public profile, used here so the create flow's upstream existence check
// (`ensure_upstream_username_exists`) hits a real, always-existing user.
// Playwright's `page.route()` can only intercept browser requests, not the
// Python backend's outbound Lichess calls, so a real username is the
// pragmatic way to keep the test deterministic for create.
const REAL_USER = 'DrNykterstein';

interface ValidateResponse {
  exists: boolean;
  already_tracked: boolean;
  profile_id: number | null;
  rate_limited: boolean;
}

async function deleteAllProfiles(request: APIRequestContext) {
  const resp = await request.get('/api/profiles');
  if (!resp.ok()) return;
  const body = (await resp.json()) as { profiles: Array<{ id: number }> };
  for (const p of body.profiles) {
    await request.delete(`/api/profiles/${String(p.id)}?detach_games=true`);
  }
}

/**
 * Mock just the front-end-facing /api/profiles/validate so the test doesn't
 * depend on Lichess timing for the validation step. The create endpoint
 * still hits real Lichess (no way to intercept from Playwright) but that's
 * fine because `DrNykterstein` is a stable real user.
 */
async function mockValidate(
  page: Page,
  exists: boolean,
  alreadyTracked: boolean,
) {
  await page.route('**/api/profiles/validate', async (route) => {
    const body: ValidateResponse = {
      exists,
      already_tracked: alreadyTracked,
      profile_id: alreadyTracked ? 1 : null,
      rate_limited: false,
    };
    await route.fulfill({ status: 200, body: JSON.stringify(body) });
  });
}

test.describe('Profiles page — five core flows', () => {
  test.describe.configure({ mode: 'serial' });

  test.beforeAll(async ({ request }) => {
    await deleteAllProfiles(request);
  });

  test.afterAll(async ({ request }) => {
    await deleteAllProfiles(request);
  });

  test('1. empty state shows add CTA, opens modal', async ({ profilesPage, page }) => {
    await mockValidate(page, true, false);

    await profilesPage.goto();
    await profilesPage.expectLoaded();

    await expect(profilesPage.emptyStateCta).toBeVisible();
    await profilesPage.emptyStateCta.click();
    await expect(profilesPage.modal).toBeVisible();
  });

  test('2. add first profile lands it in the sidebar with primary badge', async ({
    profilesPage,
    page,
  }) => {
    await mockValidate(page, true, false);

    await profilesPage.goto();
    await profilesPage.openAddModal();
    await profilesPage.fillUsername(REAL_USER);
    await profilesPage.waitForValidation();
    await profilesPage.submitAddModal();

    // Sidebar should show the profile after the modal closes.
    await expect(profilesPage.modal).toBeHidden({ timeout: 15_000 });
    await expect(profilesPage.cardForUsername(REAL_USER)).toBeVisible();
    await expect(profilesPage.cardForUsername(REAL_USER)).toContainText(/Primary/i);
  });

  test('3. validate-duplicate disables the submit button', async ({
    profilesPage,
    page,
  }) => {
    await mockValidate(page, true, true);

    await profilesPage.goto();
    await profilesPage.openAddModal();
    await profilesPage.fillUsername(REAL_USER);

    // Submit stays disabled because validation reports already_tracked.
    await expect(profilesPage.modalSubmit).toBeDisabled();
    await expect(page.getByRole('alert')).toContainText(/already tracked/i);

    await profilesPage.modalCancel.click();
    await expect(profilesPage.modal).toBeHidden();
  });

  test('4. edit preferences persists across reload', async ({ profilesPage, page }) => {
    await profilesPage.goto();
    await profilesPage.cardForUsername(REAL_USER).click();
    await profilesPage.tablistPreferences.click();

    // Toggle auto-sync off, set max games to 50. Wait for the PATCH to land.
    const toggle = profilesPage.autoSyncToggle;
    await expect(toggle).toHaveAttribute('aria-checked', 'true');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-checked', 'false');

    await profilesPage.maxGamesInput.fill('50');

    const patchPromise = page.waitForResponse(
      (resp) => resp.url().includes('/api/profiles/') && resp.request().method() === 'PATCH',
    );
    await profilesPage.preferencesSaveButton.click();
    const patchResp = await patchPromise;
    expect(patchResp.status()).toBe(200);

    // Reload + re-select profile. Preferences tab should show the saved values.
    await profilesPage.goto();
    await profilesPage.cardForUsername(REAL_USER).click();
    await profilesPage.tablistPreferences.click();
    await expect(profilesPage.autoSyncToggle).toHaveAttribute('aria-checked', 'false');
    await expect(profilesPage.maxGamesInput).toHaveValue('50');
  });

  test('5. delete with detach removes the profile from the sidebar', async ({
    profilesPage,
    page,
  }) => {
    await profilesPage.goto();
    await profilesPage.cardForUsername(REAL_USER).click();
    await profilesPage.tablistPreferences.click();
    await profilesPage.preferencesDeleteButton.click();

    // Confirm dialog opens with three actions: Cancel, Detach (focused), Delete games too.
    await expect(profilesPage.confirmDialog).toBeVisible();
    await profilesPage.confirmDetach.click();

    // Profile vanishes from sidebar.
    await expect(profilesPage.cardForUsername(REAL_USER)).toBeHidden();

    // After the only profile is gone, the empty state CTA returns.
    await expect(page.getByRole('button', { name: /Add your first profile/i }))
      .toBeVisible();
  });
});
