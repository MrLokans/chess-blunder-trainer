import { client } from './api.js';

export async function loadConfiguredUsernames() {
  try {
    return await client.settings.getUsernames();
  } catch (err) {
    console.error('Failed to load configured usernames:', err);
  }
  return {};
}
