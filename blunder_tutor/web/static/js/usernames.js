export async function loadConfiguredUsernames() {
  try {
    const resp = await fetch('/api/settings/usernames');
    if (resp.ok) {
      return await resp.json();
    }
  } catch (err) {
    console.error('Failed to load configured usernames:', err);
  }
  return {};
}
