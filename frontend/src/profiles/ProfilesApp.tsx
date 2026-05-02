import { useEffect, useState, useCallback } from 'preact/hooks';
import { client, ApiError } from '../shared/api';
import type { Profile } from '../types/profiles';
import { ProfileList } from './ProfileList';
import { ProfileOverviewTab, type OverviewToast } from './ProfileOverviewTab';
import { ProfilePreferencesTab } from './ProfilePreferencesTab';
import { AddProfileModal } from './AddProfileModal';
import { Button } from '../components/Button';
import { EmptyState } from '../components/EmptyState';
import { Tabs, type TabDescriptor } from '../components/Tabs';
import { Modal } from '../components/Modal';
import { Alert } from '../components/Alert';

type DetailTab = 'overview' | 'preferences';

const DETAIL_TABS: TabDescriptor<DetailTab>[] = [
  { key: 'overview', label: 'profiles.detail.tabs.overview' },
  { key: 'preferences', label: 'profiles.detail.tabs.preferences' },
];

interface UrlParams {
  profileId: number | null;
  tab: DetailTab | null;
}

function readUrlParams(): UrlParams {
  if (typeof window === 'undefined') return { profileId: null, tab: null };
  const params = new URLSearchParams(window.location.search);
  const idStr = params.get('profile_id');
  const tabStr = params.get('tab');
  const profileId = idStr ? Number.parseInt(idStr, 10) : null;
  const tab: DetailTab | null = tabStr === 'overview' || tabStr === 'preferences' ? tabStr : null;
  return {
    profileId: Number.isFinite(profileId) ? profileId : null,
    tab,
  };
}

export interface ProfilesAppProps {
  demoMode?: boolean;
}

export function ProfilesApp({ demoMode = false }: ProfilesAppProps) {
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [addOpen, setAddOpen] = useState(false);
  // Lifted out of ProfileOverviewTab so the "Sync dispatched" toast survives a
  // tab switch — Tabs unmounts the inactive tab body, which would otherwise
  // drop the local state and lose the only signal that sync was kicked off.
  const [syncToast, setSyncToast] = useState<OverviewToast | null>(null);

  const loadProfiles = useCallback(async () => {
    try {
      const resp = await client.profiles.list();
      setProfiles(resp.profiles);
    } catch (err) {
      const msg = err instanceof ApiError || err instanceof Error ? err.message : t('common.error');
      setError(t('profiles.load_failed', { error: msg }));
      setProfiles([]);
    }
  }, []);

  useEffect(() => {
    void loadProfiles();
  }, [loadProfiles]);

  // Apply URL params once profiles are loaded.
  useEffect(() => {
    if (!profiles || profiles.length === 0) return;
    const { profileId, tab } = readUrlParams();
    const requestedExists = profileId !== null && profiles.some(p => p.id === profileId);
    const target = requestedExists ? profileId : profiles[0]?.id ?? null;
    setSelectedId(prev => prev ?? target);
    if (tab) setActiveTab(tab);

    // If the URL named a profile that doesn't exist (deleted, wrong link),
    // strip the bad param so a refresh doesn't keep showing it.
    if (profileId !== null && !requestedExists && typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.delete('profile_id');
      window.history.replaceState({}, '', url.toString());
    }
  }, [profiles]);

  const handleSelect = useCallback((id: number) => {
    setSelectedId(id);
  }, []);

  const handleProfileDeleted = useCallback((deletedId: number) => {
    setProfiles((prev) => prev?.filter((p) => p.id !== deletedId) ?? prev);
    setSelectedId((prev) => (prev === deletedId ? null : prev));
    setActiveTab('overview');
  }, []);

  const handleProfileChange = useCallback((next: Profile) => {
    setProfiles((prev) => {
      if (!prev) return prev;
      // PATCH `is_primary=true` clears the flag on every other profile of the
      // same platform (server-side invariant). Mirror that on the client so
      // we don't have to refetch.
      return prev.map((p) => {
        if (p.id === next.id) return next;
        if (next.is_primary && p.platform === next.platform) {
          return { ...p, is_primary: false };
        }
        return p;
      });
    });
  }, []);

  const handleAddOpen = useCallback(() => {
    setAddOpen(true);
  }, []);

  const handleAddClose = useCallback(() => {
    setAddOpen(false);
  }, []);

  const handleProfileCreated = useCallback((created: Profile) => {
    setProfiles((prev) => {
      if (!prev) return [created];
      // Mirror the server-side primary-flag invariant: a newly-created
      // primary profile clears the flag on every other profile of the same
      // platform.
      const next = created.is_primary
        ? prev.map((p) => (p.platform === created.platform ? { ...p, is_primary: false } : p))
        : prev;
      return [...next, created];
    });
    setSelectedId(created.id);
  }, []);

  if (profiles === null) {
    return <div class="profiles-app profiles-app--loading">{t('common.loading')}</div>;
  }

  if (profiles.length === 0) {
    return (
      <div class="profiles-app profiles-app--empty">
        <Alert type="error" message={error} />
        <EmptyState
          title={t('profiles.empty_state.title')}
          message={t('profiles.empty_state.message')}
          action={
            <Button variant="primary" onClick={handleAddOpen}>
              {t('profiles.empty_state.cta')}
            </Button>
          }
        />
        {demoMode ? (
          <DemoBlockedModal open={addOpen} onClose={handleAddClose} />
        ) : (
          <AddProfileModal
            open={addOpen}
            onClose={handleAddClose}
            onCreated={handleProfileCreated}
            existingProfiles={profiles}
          />
        )}
      </div>
    );
  }

  const selected = profiles.find(p => p.id === selectedId) ?? null;

  return (
    <div class="profiles-app">
      <Alert type="error" message={error} />
      {syncToast && <Alert type={syncToast.type} message={syncToast.text} />}
      <aside class="profiles-app__sidebar">
        <ProfileList
          profiles={profiles}
          selectedId={selectedId}
          onSelect={handleSelect}
        />
        <div class="profiles-app__sidebar-actions">
          <Button variant="primary" size="sm" onClick={handleAddOpen}>
            {t('profiles.add_button')}
          </Button>
        </div>
      </aside>
      <section class="profiles-app__detail">
        {selected ? (
          <Tabs<DetailTab>
            tabs={DETAIL_TABS.map(tab => ({ ...tab, label: t(tab.label) }))}
            value={activeTab}
            onChange={setActiveTab}
          >
            {/* `key={selected.id}` forces a fresh mount of the active tab body
                when the user selects a different profile — the cheapest way
                to reset Preferences-tab form state without an effect that
                would otherwise drop typed-but-unsaved edits on parent
                re-renders. */}
            {activeTab === 'overview' ? (
              <ProfileOverviewTab
                key={selected.id}
                profile={selected}
                onProfileChange={handleProfileChange}
                onSyncToast={setSyncToast}
                demoMode={demoMode}
              />
            ) : (
              <ProfilePreferencesTab
                key={selected.id}
                profile={selected}
                onProfileChange={handleProfileChange}
                onProfileDeleted={handleProfileDeleted}
                demoMode={demoMode}
              />
            )}
          </Tabs>
        ) : (
          <p class="profiles-app__hint">{t('profiles.select_hint')}</p>
        )}
      </section>
      {demoMode ? (
        <DemoBlockedModal open={addOpen} onClose={handleAddClose} />
      ) : (
        <AddProfileModal
          open={addOpen}
          onClose={handleAddClose}
          onCreated={handleProfileCreated}
          existingProfiles={profiles}
        />
      )}
    </div>
  );
}

interface DemoBlockedModalProps {
  open: boolean;
  onClose: () => void;
}

function DemoBlockedModal({ open, onClose }: DemoBlockedModalProps) {
  return (
    <Modal open={open} onClose={onClose} title={t('profiles.add_modal.title')} size="md">
      <p class="profiles-add-placeholder">
        {t('profiles.add_modal.demo_disabled')}
      </p>
    </Modal>
  );
}
