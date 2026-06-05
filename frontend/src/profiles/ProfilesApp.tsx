import { useEffect, useState, useCallback } from 'preact/hooks';
import { client, ApiError } from '../shared/api';
import { useAsyncData } from '../hooks/useAsyncData';
import { AsyncBoundary } from '../components/feedback/AsyncBoundary';
import type { Profile } from '../types/profiles';
import { ProfileList } from './ProfileList';
import { ProfileOverviewTab, type OverviewToast } from './ProfileOverviewTab';
import { ProfilePreferencesTab } from './ProfilePreferencesTab';
import { AddProfileModal } from './AddProfileModal';
import { Button } from '../components/primitives/Button';
import { EmptyState } from '../components/layout/EmptyState';
import { Tabs, type TabDescriptor } from '../components/layout/Tabs';
import { Modal } from '../components/feedback/Modal';
import { Alert } from '../components/feedback/Alert';

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
  // useAsyncData owns the fetch + loading/error/empty rendering via
  // AsyncBoundary. The loaded list still needs to be locally mutable
  // (create/delete/primary-flag edits splice it without a refetch), so the
  // fetch result is mirrored into ProfilesView's own state below.
  const state = useAsyncData<Profile[]>(
    async () => {
      try {
        return (await client.profiles.list()).profiles;
      } catch (err) {
        const msg =
          err instanceof ApiError || err instanceof Error ? err.message : t('common.error');
        throw new Error(t('profiles.load_failed', { error: msg }));
      }
    },
    [],
  );

  // The empty case is interactive (it can create the first profile and then
  // transition into the populated view sharing the same local list state), so
  // ProfilesView owns its own empty rendering. Suppress AsyncBoundary's empty
  // slot — it only handles loading + error here.
  return (
    <AsyncBoundary state={state} isEmpty={() => false}>
      {(profiles) => (
        <ProfilesView initialProfiles={profiles} demoMode={demoMode} />
      )}
    </AsyncBoundary>
  );
}

interface ProfilesViewProps {
  initialProfiles: Profile[];
  demoMode: boolean;
}

function ProfilesView({ initialProfiles, demoMode }: ProfilesViewProps) {
  const [profiles, setProfiles] = useState(initialProfiles);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [addOpen, setAddOpen] = useState(false);
  // Lifted out of ProfileOverviewTab so the "Sync dispatched" toast survives a
  // tab switch — Tabs unmounts the inactive tab body, which would otherwise
  // drop the local state and lose the only signal that sync was kicked off.
  const [syncToast, setSyncToast] = useState<OverviewToast | null>(null);

  // Apply URL params once profiles are loaded.
  useEffect(() => {
    if (profiles.length === 0) return;
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
    setProfiles((prev) => prev.filter((p) => p.id !== deletedId));
    setSelectedId((prev) => (prev === deletedId ? null : prev));
    setActiveTab('overview');
  }, []);

  const handleProfileChange = useCallback((next: Profile) => {
    setProfiles((prev) => {
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

  // Deleting the last profile empties the locally-mirrored list. AsyncBoundary
  // only gates on the original fetch, so render the empty surface here.
  if (profiles.length === 0) {
    return (
      <div class="profiles-app profiles-app--empty">
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
