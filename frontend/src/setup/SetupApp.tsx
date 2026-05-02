import { useState, useCallback, useRef } from 'preact/hooks';
import { ApiError, client } from '../shared/api';
import { debounce } from '../shared/debounce';
import type { ProfilePlatform, ProfileValidateResponse } from '../types/profiles';

type ValidationState =
  | 'idle'
  | 'checking'
  | 'valid'
  | 'invalid'
  | 'already_tracked'
  | 'rate_limited';

interface FieldState {
  value: string;
  validation: ValidationState;
  // Populated when validation found this username already attached to a
  // profile. Lets the submit path reuse the existing profile_id instead of
  // attempting (and failing with 409) to create a duplicate — handles the
  // partial-submit-then-reload edge case.
  knownProfileId: number | null;
}

interface SetupPhase {
  type: 'form' | 'importing' | 'analyzing';
}

function FieldStatus({ state, username }: { state: ValidationState; username: string }) {
  if (state === 'idle') return null;
  // `already_tracked` is informational, not an error: the submit path
  // recovers via `knownProfileId` and skips the create. Rendering it
  // green-ish ('valid') keeps visual signal consistent with behavior.
  // `rate_limited` is a soft warning that the submit path treats as
  // blocking — yellow keeps it distinct from both red (invalid) and
  // green (valid).
  const classMap: Record<ValidationState, string> = {
    idle: '',
    checking: 'field-validation checking',
    valid: 'field-validation valid',
    invalid: 'field-validation invalid',
    already_tracked: 'field-validation valid',
    rate_limited: 'field-validation warning',
  };
  const labelMap: Record<ValidationState, string> = {
    idle: '',
    checking: t('setup.validating'),
    valid: t('setup.username_valid'),
    invalid: t('setup.username_invalid'),
    already_tracked: t('setup.already_tracked', { username }),
    rate_limited: t('setup.rate_limited', { username }),
  };
  return (
    <span class={classMap[state]} role="status" aria-live="polite">
      {labelMap[state]}
    </span>
  );
}

function classifyValidation(result: ProfileValidateResponse): ValidationState {
  if (result.rate_limited) return 'rate_limited';
  if (result.already_tracked) return 'already_tracked';
  return result.exists ? 'valid' : 'invalid';
}

export function SetupApp() {
  const initialField: FieldState = { value: '', validation: 'idle', knownProfileId: null };
  const [lichess, setLichess] = useState(initialField);
  const [chesscom, setChesscom] = useState(initialField);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [phase, setPhase] = useState<SetupPhase>({ type: 'form' });
  const [progressMessage, setProgressMessage] = useState('');

  const SETUP_WAIT_MS = 15000;
  const POLL_INTERVAL_MS = 2000;

  async function validateField(
    platform: ProfilePlatform,
    username: string,
    setter: (updater: (prev: FieldState) => FieldState) => void,
    currentValueRef: { current: string },
  ): Promise<ValidationState> {
    if (!username) {
      setter(prev => ({ ...prev, validation: 'idle', knownProfileId: null }));
      return 'idle';
    }
    setter(prev => ({ ...prev, validation: 'checking' }));
    try {
      const result = await client.profiles.validate({ platform, username });
      if (currentValueRef.current.trim() !== username) return 'checking';
      const state = classifyValidation(result);
      setter(prev => ({
        ...prev,
        validation: state,
        knownProfileId: result.already_tracked ? result.profile_id : null,
      }));
      return state;
    } catch {
      if (currentValueRef.current.trim() !== username) return 'checking';
      setter(prev => ({ ...prev, validation: 'idle', knownProfileId: null }));
      return 'idle';
    }
  }

  const lichessValueRef = useRef('');
  const chesscomValueRef = useRef('');

  const debouncedValidateLichess = useCallback(
    debounce((username: string) => {
      void validateField('lichess', username, setLichess, lichessValueRef);
    }, 500),
    [],
  );

  const debouncedValidateChesscom = useCallback(
    debounce((username: string) => {
      void validateField('chesscom', username, setChesscom, chesscomValueRef);
    }, 500),
    [],
  );

  function handleLichessInput(e: Event) {
    const value = (e.currentTarget as HTMLInputElement).value;
    lichessValueRef.current = value;
    const trimmed = value.trim();
    setLichess({
      value,
      validation: trimmed ? 'checking' : 'idle',
      knownProfileId: null,
    });
    debouncedValidateLichess(trimmed);
  }

  function handleChesscomInput(e: Event) {
    const value = (e.currentTarget as HTMLInputElement).value;
    chesscomValueRef.current = value;
    const trimmed = value.trim();
    setChesscom({
      value,
      validation: trimmed ? 'checking' : 'idle',
      knownProfileId: null,
    });
    debouncedValidateChesscom(trimmed);
  }

  async function validateAllFields(): Promise<{
    lichessState: ValidationState;
    chesscomState: ValidationState;
  }> {
    const lichessUsername = lichess.value.trim();
    const chesscomUsername = chesscom.value.trim();

    const [lichessState, chesscomState] = await Promise.all([
      lichessUsername
        ? validateField('lichess', lichessUsername, setLichess, lichessValueRef)
        : Promise.resolve<ValidationState>('idle'),
      chesscomUsername
        ? validateField('chesscom', chesscomUsername, setChesscom, chesscomValueRef)
        : Promise.resolve<ValidationState>('idle'),
    ]);

    return { lichessState, chesscomState };
  }

  function getValidationErrors(
    lichessUsername: string,
    chesscomUsername: string,
    lichessState: ValidationState,
    chesscomState: ValidationState,
  ): string[] {
    const errors: string[] = [];
    if (lichessUsername && lichessState === 'invalid') {
      errors.push(t('setup.lichess_not_found', { username: lichessUsername }));
    }
    if (chesscomUsername && chesscomState === 'invalid') {
      errors.push(t('setup.chesscom_not_found', { username: chesscomUsername }));
    }
    // Block the submit when either upstream check came back rate-limited;
    // letting it through means `client.profiles.create`'s own existence
    // check would 503 with an unfriendly server message.
    if (lichessUsername && lichessState === 'rate_limited') {
      errors.push(t('setup.rate_limited', { username: lichessUsername }));
    }
    if (chesscomUsername && chesscomState === 'rate_limited') {
      errors.push(t('setup.rate_limited', { username: chesscomUsername }));
    }
    return errors;
  }

  async function dispatchProfileSubmission(
    platform: ProfilePlatform,
    username: string,
    knownProfileId: number | null,
  ): Promise<string> {
    let profileId = knownProfileId;
    if (profileId === null) {
      try {
        const profile = await client.profiles.create({
          platform,
          username,
          make_primary: true,
        });
        profileId = profile.id;
      } catch (err) {
        // Race: another request just created the same (platform, username).
        // Fall back to validate to recover the profile_id and continue.
        if (err instanceof ApiError && err.status === 409) {
          const recheck = await client.profiles.validate({ platform, username });
          if (!recheck.already_tracked || recheck.profile_id === null) throw err;
          profileId = recheck.profile_id;
        } else {
          throw err;
        }
      }
    }
    const { job_id } = await client.profiles.sync(profileId);
    return job_id;
  }

  async function waitForAnalysis(jobIds: string[]): Promise<void> {
    const deadline = Date.now() + SETUP_WAIT_MS;
    setProgressMessage(t('setup.importing'));
    setPhase({ type: 'importing' });

    while (Date.now() < deadline) {
      await new Promise<void>(r => setTimeout(r, POLL_INTERVAL_MS));
      try {
        const statusResp = await client.analysis.status();
        if (statusResp.status === 'completed') return;

        const jobs = await Promise.all(
          jobIds.map(id => client.jobs.getImportStatus(id).catch(() => null)),
        );
        const allDone = jobs.every(j => j && (j.status === 'completed' || j.status === 'failed'));
        if (allDone) {
          setProgressMessage(t('setup.analyzing'));
          setPhase({ type: 'analyzing' });
        }
      } catch {
        // continue polling
      }
    }
  }

  async function handleSubmit(e: Event) {
    e.preventDefault();
    setError(null);

    const lichessUsername = lichess.value.trim();
    const chesscomUsername = chesscom.value.trim();

    if (!lichessUsername && !chesscomUsername) {
      setError(t('setup.username_error'));
      return;
    }

    setSubmitting(true);

    const { lichessState, chesscomState } = await validateAllFields();
    const errors = getValidationErrors(lichessUsername, chesscomUsername, lichessState, chesscomState);

    if (errors.length > 0) {
      setError(errors.join(' '));
      setSubmitting(false);
      return;
    }

    const submissions: Array<{
      platform: ProfilePlatform;
      username: string;
      knownProfileId: number | null;
    }> = [];
    if (lichessUsername) {
      submissions.push({
        platform: 'lichess',
        username: lichessUsername,
        knownProfileId: lichess.knownProfileId,
      });
    }
    if (chesscomUsername) {
      submissions.push({
        platform: 'chesscom',
        username: chesscomUsername,
        knownProfileId: chesscom.knownProfileId,
      });
    }

    try {
      const jobIds: string[] = [];
      // Sequential, not Promise.all: a failed Lichess create should abort
      // before we kick off Chess.com. Promise.all would force per-result
      // error mapping and split-success semantics.
      for (const { platform, username, knownProfileId } of submissions) {
        const jobId = await dispatchProfileSubmission(platform, username, knownProfileId);
        jobIds.push(jobId);
      }
      await client.setup.markComplete();

      if (jobIds.length > 0) {
        await waitForAnalysis(jobIds);
      }

      trackEvent('Setup Completed', {
        has_lichess: lichessUsername ? 'yes' : 'no',
        has_chesscom: chesscomUsername ? 'yes' : 'no',
      });
      window.location.href = '/';
    } catch (err) {
      setError((err instanceof Error ? err.message : String(err)) || t('setup.failed'));
      setSubmitting(false);
      setPhase({ type: 'form' });
    }
  }

  const showProgress = phase.type === 'importing' || phase.type === 'analyzing';

  return (
    <div class="container">
      <div class="card">
        <h1>{t('setup.title')}</h1>
        <p class="subtitle">{t('setup.subtitle')}</p>

        <div class="alert alert-info visible">
          {t('setup.username_required')}
        </div>

        {error && (
          <div class="alert alert-error visible" role="alert">
            {error}
          </div>
        )}

        {!showProgress && (
          <form id="setupForm" onSubmit={(e) => { void handleSubmit(e); }}>
            <div class="form-group">
              <label for="lichess">{t('setup.lichess_label')}</label>
              <input
                type="text"
                id="lichess"
                name="lichess"
                placeholder={t('setup.lichess_placeholder')}
                value={lichess.value}
                onInput={handleLichessInput}
              />
              <FieldStatus state={lichess.validation} username={lichess.value.trim()} />
              <div class="help-text">{t('setup.lichess_help')}</div>
            </div>

            <div class="form-group">
              <label for="chesscom">{t('setup.chesscom_label')}</label>
              <input
                type="text"
                id="chesscom"
                name="chesscom"
                placeholder={t('setup.chesscom_placeholder')}
                value={chesscom.value}
                onInput={handleChesscomInput}
              />
              <FieldStatus state={chesscom.validation} username={chesscom.value.trim()} />
              <div class="help-text">{t('setup.chesscom_help')}</div>
            </div>

            <button type="submit" class="btn btn-primary" id="submitBtn" disabled={submitting}>
              {submitting ? t('setup.submitting') : t('setup.submit')}
            </button>
          </form>
        )}

        {showProgress && (
          <div id="setupProgress">
            <div class="setup-progress-spinner"></div>
            <p class="setup-progress-message">{progressMessage}</p>
          </div>
        )}

        <div class="footer">
          <span
            dangerouslySetInnerHTML={{
              __html: t('setup.help', { link: `<a href="https://github.com/anthropics/blunder-tutor">${t('setup.documentation')}</a>` }),
            }}
          />
        </div>
      </div>
    </div>
  );
}
