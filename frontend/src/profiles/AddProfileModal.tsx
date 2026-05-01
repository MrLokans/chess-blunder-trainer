import { useState, useCallback, useEffect, useMemo, useRef } from 'preact/hooks';
import { client, ApiError } from '../shared/api';
import type { Profile, ProfilePlatform, ProfileValidateResponse } from '../types/profiles';
import { Modal } from '../components/Modal';
import { Button } from '../components/Button';
import { FormField } from '../components/FormField';
import { TextInput } from '../components/TextInput';
import { Toggle } from '../components/Toggle';
import { Dropdown } from '../components/Dropdown';
import { Alert } from '../components/Alert';
import { debounce } from '../shared/debounce';

const VALIDATE_DEBOUNCE_MS = 500;

const PLATFORM_OPTIONS = [
  { value: 'lichess', label: 'Lichess' },
  { value: 'chesscom', label: 'Chess.com' },
];

type ValidationState =
  | { status: 'idle' }
  | { status: 'checking' }
  | { status: 'valid'; username: string }
  | { status: 'not_found' }
  | { status: 'already_tracked' }
  | { status: 'rate_limited' }
  | { status: 'error'; message: string };

export interface AddProfileModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (profile: Profile) => void;
  existingProfiles: Profile[];
}

function platformHasProfile(profiles: Profile[], platform: ProfilePlatform): boolean {
  return profiles.some((p) => p.platform === platform);
}

function validationToError(state: ValidationState): string | undefined {
  switch (state.status) {
    case 'not_found':
      return t('profiles.add_modal.validation.not_found');
    case 'already_tracked':
      return t('profiles.add_modal.validation.already_tracked');
    case 'rate_limited':
      return t('profiles.add_modal.validation.rate_limited');
    case 'error':
      return state.message;
    default:
      return undefined;
  }
}

export function AddProfileModal({ open, onClose, onCreated, existingProfiles }: AddProfileModalProps) {
  const [platform, setPlatform] = useState<ProfilePlatform>('lichess');
  const [username, setUsername] = useState('');
  const [makePrimary, setMakePrimary] = useState(true);
  const [validation, setValidation] = useState<ValidationState>({ status: 'idle' });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Track which (platform, username) was last validated so a stale debounced
  // call from a prior keystroke can't overwrite a fresher result.
  const latestRequestRef = useRef(0);

  // When the user opens the modal, default `make_primary` to true unless a
  // profile already exists for the currently-selected platform.
  useEffect(() => {
    if (!open) return;
    setMakePrimary(!platformHasProfile(existingProfiles, platform));
    setValidation({ status: 'idle' });
    setSubmitError(null);
    setUsername('');
  }, [open, existingProfiles, platform]);

  // Re-evaluate the make-primary default when the user switches platform.
  useEffect(() => {
    setMakePrimary(!platformHasProfile(existingProfiles, platform));
  }, [platform, existingProfiles]);

  const runValidation = useCallback(async (p: ProfilePlatform, u: string) => {
    const requestId = latestRequestRef.current + 1;
    latestRequestRef.current = requestId;
    setValidation({ status: 'checking' });
    try {
      const resp: ProfileValidateResponse = await client.profiles.validate({ platform: p, username: u });
      if (latestRequestRef.current !== requestId) return; // superseded
      if (resp.rate_limited) {
        setValidation({ status: 'rate_limited' });
      } else if (!resp.exists) {
        setValidation({ status: 'not_found' });
      } else if (resp.already_tracked) {
        setValidation({ status: 'already_tracked' });
      } else {
        setValidation({ status: 'valid', username: u });
      }
    } catch (err) {
      if (latestRequestRef.current !== requestId) return;
      const msg = err instanceof ApiError || err instanceof Error ? err.message : t('common.error');
      setValidation({ status: 'error', message: msg });
    }
  }, []);

  const debouncedValidate = useMemo(
    () => debounce((p: ProfilePlatform, u: string) => { void runValidation(p, u); }, VALIDATE_DEBOUNCE_MS),
    [runValidation],
  );

  const handleUsernameChange = useCallback((value: string) => {
    setUsername(value);
    setValidation({ status: 'idle' });
    if (value.trim().length === 0) return;
    debouncedValidate(platform, value.trim());
  }, [debouncedValidate, platform]);

  const handlePlatformChange = useCallback((value: string) => {
    if (value !== 'lichess' && value !== 'chesscom') return;
    setPlatform(value);
    setValidation({ status: 'idle' });
    if (username.trim().length > 0) {
      debouncedValidate(value, username.trim());
    }
  }, [debouncedValidate, username]);

  const canSubmit = validation.status === 'valid' && validation.username === username.trim() && !submitting;

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const created = await client.profiles.create({
        platform,
        username: username.trim(),
        make_primary: makePrimary,
      });
      onCreated(created);
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setSubmitError(t('profiles.add_modal.race_conflict'));
      } else {
        const msg = err instanceof ApiError || err instanceof Error ? err.message : t('common.error');
        setSubmitError(t('profiles.add_modal.create_failed', { error: msg }));
      }
    } finally {
      setSubmitting(false);
    }
  }, [canSubmit, platform, username, makePrimary, onCreated, onClose]);

  const validationError = validationToError(validation);
  const validationHint = validation.status === 'checking'
    ? t('profiles.add_modal.validation.checking')
    : validation.status === 'valid'
      ? t('profiles.add_modal.validation.valid', { username: validation.username })
      : undefined;

  return (
    <Modal open={open} onClose={onClose} title={t('profiles.add_modal.title')} size="md">
      <div class="add-profile-form">
        <FormField label={t('profiles.add_modal.platform_label')}>
          <Dropdown options={PLATFORM_OPTIONS} value={platform} onChange={handlePlatformChange} />
        </FormField>

        <FormField
          label={t('profiles.add_modal.username_label')}
          helpText={validationHint}
          error={validationError}
        >
          <TextInput
            value={username}
            onChange={handleUsernameChange}
            placeholder={t('profiles.add_modal.username_placeholder')}
            invalid={validationError !== undefined}
            autoComplete="off"
          />
        </FormField>

        <FormField
          label={t('profiles.add_modal.primary_label')}
          helpText={t('profiles.add_modal.primary_help')}
        >
          <Toggle value={makePrimary} onChange={setMakePrimary} />
        </FormField>

        <Alert type="error" message={submitError} />

        <div class="add-profile-form__actions">
          <Button variant="ghost" onClick={onClose}>
            {t('profiles.add_modal.cancel')}
          </Button>
          <Button
            variant="primary"
            onClick={() => { void handleSubmit(); }}
            disabled={!canSubmit}
            loading={submitting}
          >
            {t('profiles.add_modal.submit')}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
