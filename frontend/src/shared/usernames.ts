import { client } from './api';

export async function loadConfiguredUsernames(): Promise<Record<string, string>> {
  try {
    return await client.settings.getUsernames() as Record<string, string>;
  } catch (err: unknown) {
    console.error('Failed to load configured usernames:', err);
  }
  return {};
}
