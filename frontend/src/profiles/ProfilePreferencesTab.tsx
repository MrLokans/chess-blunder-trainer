import { useState, useCallback } from 'preact/hooks';
import { client, ApiError } from '../shared/api';
import type { Profile } from '../types/profiles';
import { Button } from '../components/Button';
import { FormField } from '../components/FormField';
import { TextInput } from '../components/TextInput';
import { Toggle } from '../components/Toggle';
import { Alert } from '../components/Alert';
import { ConfirmDialog } from '../components/ConfirmDialog';

export interface ProfilePreferencesTabProps {
  profile: Profile;
  onProfileChange: (next: Profile) => void;
  onProfileDeleted: (id: number) => void;
  demoMode?: boolean;
}

interface Status {
  type: 'success' | 'error';
  text: string;
}

function maxGamesToString(value: number | null): string {
  return value === null ? '' : String(value);
}

function parseMaxGames(value: string): { ok: true; value: number | null } | { ok: false; error: string } {
  const trimmed = value.trim();
  if (trimmed === '') return { ok: true, value: null };
  const n = Number(trimmed);
  if (!Number.isInteger(n) || n <= 0) {
    return { ok: false, error: t('profiles.preferences.max_games_invalid') };
  }
  return { ok: true, value: n };
}

export function ProfilePreferencesTab({
  profile,
  onProfileChange,
  onProfileDeleted,
  demoMode = false,
}: ProfilePreferencesTabProps) {
  const [autoSync, setAutoSync] = useState(profile.preferences.auto_sync_enabled);
  const [maxGamesText, setMaxGamesText] = useState(maxGamesToString(profile.preferences.sync_max_games));
  const [maxGamesError, setMaxGamesError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<Status | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Form state is initialized once from `profile` and intentionally NOT
  // re-synced on parent re-renders — that would silently drop the user's
  // typed-but-unsaved edits whenever a sibling action (e.g. the Overview
  // tab promoting this profile) refreshes the parent's profile object.
  // Per-profile reset is handled by the parent passing `key={profile.id}`
  // to this component, which forces a fresh mount when the user selects
  // a different profile.

  const handleSave = useCallback(async () => {
    const parsed = parseMaxGames(maxGamesText);
    if (!parsed.ok) {
      setMaxGamesError(parsed.error);
      return;
    }
    setMaxGamesError(null);
    setSaveStatus(null);
    setSaving(true);
    try {
      const next = await client.profiles.update(profile.id, {
        preferences: {
          auto_sync_enabled: autoSync,
          sync_max_games: parsed.value,
        },
      });
      onProfileChange(next);
      setSaveStatus({ type: 'success', text: t('profiles.preferences.saved') });
    } catch (err) {
      const msg = err instanceof ApiError || err instanceof Error ? err.message : t('common.error');
      setSaveStatus({ type: 'error', text: t('profiles.preferences.save_failed', { error: msg }) });
    } finally {
      setSaving(false);
    }
  }, [profile.id, autoSync, maxGamesText, onProfileChange]);

  const handleDelete = useCallback(async (detachGames: boolean) => {
    setDeleteError(null);
    setDeleting(true);
    try {
      await client.profiles.delete(profile.id, detachGames);
      onProfileDeleted(profile.id);
    } catch (err) {
      const msg = err instanceof ApiError || err instanceof Error ? err.message : t('common.error');
      setDeleteError(t('profiles.preferences.delete_failed', { error: msg }));
    } finally {
      setDeleting(false);
    }
  }, [profile.id, onProfileDeleted]);

  return (
    <div class="profile-preferences">
      <FormField
        label={t('profiles.preferences.auto_sync')}
        helpText={t('profiles.preferences.auto_sync_help')}
      >
        <Toggle
          value={autoSync}
          onChange={setAutoSync}
          disabled={demoMode}
          ariaLabel={t('profiles.preferences.auto_sync')}
        />
      </FormField>

      <FormField
        label={t('profiles.preferences.max_games')}
        helpText={t('profiles.preferences.max_games_help')}
        error={maxGamesError ?? undefined}
      >
        <TextInput
          type="number"
          value={maxGamesText}
          onChange={setMaxGamesText}
          placeholder={t('profiles.preferences.max_games_placeholder')}
          disabled={demoMode}
          invalid={maxGamesError !== null}
        />
      </FormField>

      <div class="profile-preferences__actions">
        <Button
          variant="primary"
          onClick={() => { void handleSave(); }}
          loading={saving}
          disabled={demoMode}
        >
          {t('profiles.preferences.save')}
        </Button>
      </div>
      <Alert type={saveStatus?.type ?? 'success'} message={saveStatus?.text ?? null} />

      <hr class="profile-preferences__divider" />

      <section class="profile-preferences__danger">
        <h3 class="profile-preferences__danger-heading">
          {t('profiles.preferences.delete_heading')}
        </h3>
        <p class="profile-preferences__danger-body">
          {t('profiles.preferences.delete_explainer')}
        </p>
        <Button
          variant="danger"
          onClick={() => { setConfirmOpen(true); }}
          disabled={demoMode}
        >
          {t('profiles.preferences.delete_button')}
        </Button>
      </section>
      <Alert type="error" message={deleteError} />

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => { setConfirmOpen(false); }}
        title={t('profiles.delete.confirm_title', { username: profile.username })}
        message={t('profiles.delete.confirm_message')}
        confirmLabel={t('profiles.delete.detach_games')}
        cancelLabel={t('profiles.delete.cancel')}
        defaultFocus="confirm"
        onConfirm={() => { void handleDelete(true); }}
        secondaryAction={{
          label: t('profiles.delete.delete_games'),
          destructive: true,
          onConfirm: () => { void handleDelete(false); },
        }}
      />
      {deleting && (
        <p class="profile-preferences__deleting" role="status">
          {t('profiles.preferences.deleting')}
        </p>
      )}
    </div>
  );
}
