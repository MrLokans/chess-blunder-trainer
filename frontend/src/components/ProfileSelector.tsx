import type { Profile } from '../types/profiles';
import { PLATFORM_LABEL } from '../types/profiles';

export interface ProfileSelectorProps {
  profiles: Profile[];
  value: number | null;
  onChange: (profileId: number) => void;
  disabled?: boolean;
  ariaLabel?: string;
  id?: string;
}

export function ProfileSelector({
  profiles,
  value,
  onChange,
  disabled = false,
  ariaLabel,
  id,
}: ProfileSelectorProps) {
  function handleChange(e: Event) {
    const next = (e.currentTarget as HTMLSelectElement).value;
    const parsed = Number.parseInt(next, 10);
    if (!Number.isNaN(parsed)) onChange(parsed);
  }

  return (
    <select
      id={id}
      class="profile-selector"
      value={value ?? ''}
      disabled={disabled || profiles.length === 0}
      aria-label={ariaLabel}
      onChange={handleChange}
    >
      {profiles.map((profile) => (
        <option key={profile.id} value={profile.id}>
          {`${PLATFORM_LABEL[profile.platform]} — ${profile.username}${profile.is_primary ? ` (${t('profiles.list.primary_indicator')})` : ''}`}
        </option>
      ))}
    </select>
  );
}
