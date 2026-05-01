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
    this.addButton = page.getByRole('button', { name: /Add profile|Add your first profile/i });
    this.emptyStateCta = page.getByRole('button', { name: /Add your first profile/i });
    this.modal = page.getByRole('dialog');
    this.platformDropdown = this.modal.getByRole('button', { expanded: false }).first();
    this.usernameInput = this.modal.getByRole('textbox');
    this.modalSubmit = this.modal.getByRole('button', { name: /Add profile/i });
    this.modalCancel = this.modal.getByRole('button', { name: /Cancel/i });
    this.tablistOverview = page.getByRole('tab', { name: /Overview/i });
    this.tablistPreferences = page.getByRole('tab', { name: /Preferences/i });
    this.preferencesSaveButton = page.getByRole('button', { name: /Save preferences/i });
    this.preferencesDeleteButton = page.getByRole('button', { name: /Delete profile/i });
    this.autoSyncToggle = page.getByRole('switch');
    this.maxGamesInput = page.getByRole('spinbutton');
    this.confirmDialog = page.getByRole('dialog');
    this.confirmDetach = page.getByRole('button', { name: /Detach/i });
    this.confirmDeleteGames = page.getByRole('button', { name: /Delete games too/i });
    this.confirmCancel = page.getByRole('button', { name: /Cancel/i });
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
    return this.sidebar.locator('.profile-list__item', { hasText: username.toLowerCase() });
  }
}
