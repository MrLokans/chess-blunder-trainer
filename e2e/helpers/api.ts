import { type APIRequestContext } from '@playwright/test';

export async function enableFeatureFlags(
  request: APIRequestContext,
  flags: Record<string, boolean>,
): Promise<void> {
  const response = await request.post('/api/settings/features', {
    data: { features: flags },
  });
  if (!response.ok()) {
    throw new Error(`Failed to set feature flags: ${String(response.status())}`);
  }
}

export async function resetFeatureFlags(
  request: APIRequestContext,
  flags: Record<string, boolean>,
): Promise<void> {
  await enableFeatureFlags(request, flags);
}
