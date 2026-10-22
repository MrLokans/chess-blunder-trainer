import { type Page, type Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class ProfilesPage extends BasePage {
  readonly root: Locator;
  readonly addButton: Locator;
  readonly emptyStateCta: Locator;
  readonly modal: Locator;
  readonly platformDropdown: Locator;
  readonly usernameInput: Locator;
  readonly modalSubmit: Locator;
  readonly modalCancel: Locator;
  readonly sidebar: Locator;
  readonly tablistOverview: Locator;
  readonly tablistPreferences: Locator;
  readonly preferencesSaveButton: Locator;
  readonly preferencesDeleteButton: Locator;
  readonly autoSyncToggle: Locator;
  readonly maxGamesInput: Locator;
  readonly confirmDialog: Locator;
  readonly confirmDetach: Locator;
  readonly confirmDeleteGames: Locator;
  readonly confirmCancel: Locator;

  constructor(page: Page) {
    super(page);
    this.root = page.locator('#profiles-root');
    this.sidebar = page.locator('.profile-list');
    // The "add" trigger has two locations depending on state: empty CTA or
    // sidebar button. Both ultimately open the same modal.
    this.addButton = page.getByTestId('profile-add').or(page.getByTestId('profile-add-first'));
    this.emptyStateCta = page.getByTestId('profile-add-first');
    this.modal = page.getByRole('dialog');
    this.platformDropdown = this.modal.getByRole('button', { expanded: false }).first();
    this.usernameInput = this.modal.getByRole('textbox');
    this.modalSubmit = page.getByTestId('add-profile-submit');
    this.modalCancel = page.getByTestId('add-profile-cancel');
    this.tablistOverview = page.getByTestId('tab-overview');
    this.tablistPreferences = page.getByTestId('tab-preferences');
    this.preferencesSaveButton = page.getByTestId('profile-preferences-save');
    this.preferencesDeleteButton = page.getByTestId('profile-delete');
    this.autoSyncToggle = page.getByRole('switch');
    this.maxGamesInput = page.getByRole('spinbutton');
    this.confirmDialog = page.getByRole('dialog');
    this.confirmDetach = page.getByTestId('confirm-dialog-confirm');
    this.confirmDeleteGames = page.getByTestId('confirm-dialog-secondary');
    this.confirmCancel = page.getByTestId('confirm-dialog-cancel');
  }

  async goto(): Promise<void> {
    await this.navigateTo('/profiles');
  }

  async expectLoaded(): Promise<void> {
    await expect(this.root).toBeVisible();
  }

  async openAddModal(): Promise<void> {
    await this.addButton.first().click();
    await expect(this.modal).toBeVisible();
  }

  async fillUsername(username: string): Promise<void> {
    await this.usernameInput.fill(username);
  }

  async waitForValidation(): Promise<void> {
    // Submit button is disabled until validation completes successfully.
    // We wait up to 10s for the debounced validation + Lichess API call.
    await expect(this.modalSubmit).toBeEnabled({ timeout: 10_000 });
  }

  async submitAddModal(): Promise<void> {
    await this.modalSubmit.click();
  }

  /** Sidebar card containing the given username (case-insensitive match). */
  cardForUsername(username: string): Locator {
    // eslint-disable-next-line no-restricted-syntax -- matches user data, not UI text
    return this.sidebar.locator('.profile-list__item', { hasText: username.toLowerCase() });
  }
}
