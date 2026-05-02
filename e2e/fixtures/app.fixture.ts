import { test as base } from '@playwright/test';
import { TrainerPage } from '../pages/trainer.page';
import { SetupPage } from '../pages/setup.page';
import { DashboardPage } from '../pages/dashboard.page';
import { SettingsPage } from '../pages/settings.page';
import { ImportPage } from '../pages/import.page';
import { ManagementPage } from '../pages/management.page';
import { GameReviewPage } from '../pages/game-review.page';
import { ProfilesPage } from '../pages/profiles.page';

type AppFixtures = {
  trainerPage: TrainerPage;
  setupPage: SetupPage;
  dashboardPage: DashboardPage;
  settingsPage: SettingsPage;
  importPage: ImportPage;
  managementPage: ManagementPage;
  gameReviewPage: GameReviewPage;
  profilesPage: ProfilesPage;
};

export const test = base.extend<AppFixtures>({
  trainerPage: async ({ page }, use) => {
    await use(new TrainerPage(page));
  },
  setupPage: async ({ page }, use) => {
    await use(new SetupPage(page));
  },
  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },
  settingsPage: async ({ page }, use) => {
    await use(new SettingsPage(page));
  },
  importPage: async ({ page }, use) => {
    await use(new ImportPage(page));
  },
  managementPage: async ({ page }, use) => {
    await use(new ManagementPage(page));
  },
  gameReviewPage: async ({ page }, use) => {
    await use(new GameReviewPage(page));
  },
  profilesPage: async ({ page }, use) => {
    await use(new ProfilesPage(page));
  },
});

export { expect } from '@playwright/test';
