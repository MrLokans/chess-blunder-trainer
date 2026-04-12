import { type Page, type Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class ImportPage extends BasePage {
  readonly root: Locator;
  readonly pgnTextarea: Locator;
  readonly submitBtn: Locator;
  readonly errors: Locator;
  readonly spinner: Locator;

  constructor(page: Page) {
    super(page);
    this.root = page.locator('#import-root');
    this.pgnTextarea = page.locator('.pgn-textarea');
    this.submitBtn = this.root.getByRole('button', { name: /import/i });
    this.errors = page.locator('.import-errors');
    this.spinner = page.locator('.import-spinner');
  }

  async goto(): Promise<void> {
    await this.navigateTo('/import');
  }

  async expectLoaded(): Promise<void> {
    await expect(this.root).toBeVisible();
    await expect(this.pgnTextarea).toBeVisible();
  }

  async pastePGN(pgn: string): Promise<void> {
    await this.pgnTextarea.fill(pgn);
  }

  async submit(): Promise<void> {
    await this.submitBtn.click();
  }

  async expectImportComplete(): Promise<void> {
    await expect(this.spinner).not.toBeVisible({ timeout: 60_000 });
    const results = this.page.locator('.result-blunders');
    await expect(results).toBeVisible({ timeout: 60_000 });
  }

  async expectErrors(): Promise<void> {
    await expect(this.errors).toBeVisible();
  }
}
