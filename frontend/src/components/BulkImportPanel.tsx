import { useEffect, useState } from 'preact/hooks';
import type { Profile } from '../types/profiles';
import { EmptyState } from './EmptyState';
import { ImportLauncher } from './ImportLauncher';
import { ProfileSelector } from './ProfileSelector';
import type { ExternalJobStatus } from './JobCard';

export interface BulkImportPanelProps {
  profiles: Profile[];
  loading?: boolean;
  demoMode?: boolean;
  externalStatus?: ExternalJobStatus;
  onImportStarted: (jobId: string) => void;
}

function pickInitialProfileId(profiles: Profile[]): number | null {
  const head = profiles[0];
  if (head === undefined) return null;
  const primary = profiles.find((p) => p.is_primary);
  return (primary ?? head).id;
}

export function BulkImportPanel({
  profiles,
  loading = false,
  demoMode = false,
  externalStatus,
  onImportStarted,
}: BulkImportPanelProps) {
  const [selectedId, setSelectedId] = useState<number | null>(() => pickInitialProfileId(profiles));

  // Re-derive the default selection when the profile list changes (initial
  // fetch resolves, a profile gets added/deleted, primary toggle flips). If
  // the previously selected profile is gone, fall back to the new primary.
  useEffect(() => {
    setSelectedId((prev) => {
      if (prev !== null && profiles.some((p) => p.id === prev)) return prev;
      return pickInitialProfileId(profiles);
    });
  }, [profiles]);

  if (loading) {
    return <p class="section-description">{t('common.loading')}</p>;
  }

  if (profiles.length === 0) {
    return (
      <EmptyState
        title={t('profiles.bulk_import.empty_title')}
        message={t('profiles.bulk_import.empty_message')}
        action={
          <a class="btn btn--primary btn--md" href="/profiles">
            {t('profiles.bulk_import.empty_cta')}
          </a>
        }
      />
    );
  }

  // The empty-list case is handled above; profiles[0] is guaranteed defined,
  // and the useEffect above keeps selectedId valid against the current list,
  // so the find() fallback only fires during the brief render between a
  // profile deletion and the effect rerunning.
  const head = profiles[0] as Profile;
  const selected = profiles.find((p) => p.id === selectedId) ?? head;

  return (
    <div class="bulk-import-panel">
      <div class="form-group">
        <label for="bulk-import-profile">{t('profiles.bulk_import.profile_label')}</label>
        <ProfileSelector
          id="bulk-import-profile"
          profiles={profiles}
          value={selected.id}
          onChange={setSelectedId}
          ariaLabel={t('profiles.bulk_import.profile_label')}
        />
      </div>
      <ImportLauncher
        profile={selected}
        demoMode={demoMode}
        externalStatus={externalStatus}
        onImportStarted={onImportStarted}
      />
    </div>
  );
}
