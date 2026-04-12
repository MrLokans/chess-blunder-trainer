import { type Page, type Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class TrainerPage extends BasePage {
  readonly board: Locator;
  readonly boardWrapper: Locator;
  readonly resultCard: Locator;
  readonly feedbackTitle: Locator;
  readonly feedbackDetail: Locator;
  readonly bestMoveDisplay: Locator;
  readonly movePrompt: Locator;
  readonly emptyState: Locator;
  readonly submitBtn: Locator;
  readonly resetBtn: Locator;
  readonly showBestBtn: Locator;
  readonly nextBtn: Locator;
  readonly vimInput: Locator;
  readonly vimInputField: Locator;
  readonly vimInputError: Locator;
  readonly evalValue: Locator;
  readonly filtersToggleBtn: Locator;
  readonly filtersCountBadge: Locator;
  readonly vimSuggestions: Locator;

  constructor(page: Page) {
    super(page);
    this.board = page.locator('#board');
    this.boardWrapper = page.locator('#boardWrapper');
    this.resultCard = page.locator('#boardResultCard');
    this.feedbackTitle = page.locator('#feedbackTitle');
    this.feedbackDetail = page.locator('#feedbackDetail');
    this.bestMoveDisplay = page.locator('#bestMoveDisplay');
    this.movePrompt = page.locator('#movePrompt');
    this.emptyState = page.locator('#emptyState');
    this.submitBtn = page.locator('#submitBtn');
    this.resetBtn = page.locator('#resetBtn');
    this.showBestBtn = page.locator('#showBestBtn');
    this.nextBtn = page.locator('#nextBtn');
    this.vimInput = page.locator('#vimInput');
    this.vimInputField = page.locator('#vimInputField');
    this.vimInputError = page.locator('#vimInputError');
    this.evalValue = page.locator('#evalValue');
    this.filtersToggleBtn = page.locator('#filtersToggleBtn');
    this.filtersCountBadge = page.locator('#filtersCountBadge');
    this.vimSuggestions = page.locator('#vimSuggestions');
  }

  async goto(): Promise<void> {
    await this.navigateTo('/');
  }

  async loadSpecificPuzzle(gameId: string, ply: number): Promise<void> {
    const responsePromise = this.page.waitForResponse(
      resp => resp.url().includes('/api/puzzle/specific') && resp.status() === 200,
    );
    await this.page.goto(`/?game_id=${gameId}&ply=${String(ply)}`);
    await responsePromise;
    await expect(this.board).toBeVisible();
  }

  async expectLoaded(): Promise<void> {
    await expect(this.board).toBeVisible();
  }

  async expectEmptyStateVisible(): Promise<void> {
    await expect(this.emptyState).toBeVisible();
  }

  async expectBoardOrEmptyState(): Promise<void> {
    const combined = this.page.locator('#board, #emptyState');
    await expect(combined.first()).toBeVisible();
  }

  async expectPuzzleLoaded(): Promise<void> {
    await expect(this.board).toBeVisible();
    await expect(this.movePrompt).toBeVisible();
  }

  // --- Click-based moves ---
  // TODO: Add clickSquare(square) and makeMove(from, to) methods.
  // Requires spike on how Chessground renders squares and handles orientation.
  // Vim mode covers move submission flow; click-based interaction is untested.

  // --- Vim mode ---

  async openVimMode(): Promise<void> {
    await this.page.keyboard.press(':');
    await expect(this.vimInput).toHaveClass(/active/);
  }

  async typeVimMove(san: string): Promise<void> {
    await this.openVimMode();
    await this.vimInputField.fill(san);
    await this.vimInputField.press('Enter');
  }

  async typeVimMoveAndWaitForSubmit(san: string): Promise<void> {
    const responsePromise = this.page.waitForResponse('**/api/submit');
    await this.typeVimMove(san);
    await responsePromise;
  }

  async expectVimError(): Promise<void> {
    await expect(this.vimInputError).toBeVisible();
  }

  async closeVimMode(): Promise<void> {
    await this.vimInputField.press('Escape');
  }

  // --- Feedback assertions ---

  async expectCorrectFeedback(): Promise<void> {
    await expect(this.resultCard).toBeVisible();
    await expect(this.resultCard).toHaveClass(/accent-correct/);
  }

  async expectWrongFeedback(): Promise<void> {
    await expect(this.resultCard).toBeVisible();
    await expect(this.resultCard).toHaveClass(/accent-blunder|accent-revealed/);
  }

  async expectBestMoveRevealed(): Promise<void> {
    await expect(this.resultCard).toBeVisible();
    await expect(this.resultCard).toHaveClass(/best-revealed/);
    await expect(this.bestMoveDisplay).toBeVisible();
  }

  // --- Controls ---

  async clickNext(): Promise<void> {
    const responsePromise = this.page.waitForResponse(
      resp => resp.url().includes('/api/puzzle') && resp.status() === 200,
    );
    await this.nextBtn.click();
    await responsePromise;
  }

  async pressNext(): Promise<void> {
    const responsePromise = this.page.waitForResponse(
      resp => resp.url().includes('/api/puzzle') && resp.status() === 200,
    );
    await this.page.keyboard.press('n');
    await responsePromise;
  }

  async clickShowBest(): Promise<void> {
    await this.showBestBtn.click();
  }

  async pressShowBest(): Promise<void> {
    await this.page.keyboard.press('b');
  }

  async clickReset(): Promise<void> {
    await this.resetBtn.click();
  }

  // --- Filters ---

  async toggleFiltersPanel(): Promise<void> {
    await this.filtersToggleBtn.click();
  }

  async uncheckGameTypeFilter(gameType: string): Promise<void> {
    const section = this.page.locator('.game-type-filter');
    await expect(section).toBeVisible();
    const label = section.locator('label.filter-checkbox-label', { hasText: new RegExp(gameType, 'i') });
    await label.click();
  }

  async setColorFilter(color: 'white' | 'black' | 'both'): Promise<void> {
    const section = this.page.locator('.color-filter');
    await expect(section).toBeVisible();
    const label = section.locator('label.filter-radio-label', { hasText: new RegExp(color, 'i') });
    await label.click();
  }

  async clearFilters(): Promise<void> {
    const clearBtn = this.page.getByRole('button', { name: /clear/i });
    await clearBtn.click();
  }

  async expectActiveFilterCount(minCount: number): Promise<void> {
    await expect(this.filtersCountBadge).toBeVisible();
    await expect(this.filtersCountBadge).not.toHaveText('0');
    if (minCount > 1) {
      await expect(this.filtersCountBadge).toContainText(String(minCount));
    }
  }

  // --- Context info ---

  async getContextTags(): Promise<string[]> {
    const tags = this.page.locator('.context-tag');
    return await tags.allTextContents();
  }
}
