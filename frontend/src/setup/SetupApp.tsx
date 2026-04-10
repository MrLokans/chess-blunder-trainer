import { useState, useCallback, useRef } from 'preact/hooks';
import { client } from '../shared/api';
import { debounce } from '../shared/debounce';

type ValidationState = 'idle' | 'checking' | 'valid' | 'invalid';

interface FieldState {
  value: string;
  validation: ValidationState;
}

interface SetupPhase {
  type: 'form' | 'importing' | 'analyzing';
}

function FieldStatus({ state }: { state: ValidationState }) {
  if (state === 'idle') return null;
  const classMap: Record<ValidationState, string> = {
    idle: '',
    checking: 'field-validation checking',
    valid: 'field-validation valid',
    invalid: 'field-validation invalid',
  };
  const labelMap: Record<ValidationState, string> = {
    idle: '',
    checking: t('setup.validating'),
    valid: t('setup.username_valid'),
    invalid: t('setup.username_invalid'),
  };
  return <span class={classMap[state]}>{labelMap[state]}</span>;
}

export function SetupApp() {
  const [lichess, setLichess] = useState<FieldState>({ value: '', validation: 'idle' });
  const [chesscom, setChesscom] = useState<FieldState>({ value: '', validation: 'idle' });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [phase, setPhase] = useState<SetupPhase>({ type: 'form' });
  const [progressMessage, setProgressMessage] = useState('');

  const SETUP_WAIT_MS = 15000;
  const POLL_INTERVAL_MS = 2000;

  async function validateField(
    platform: string,
    username: string,
    setter: (updater: (prev: FieldState) => FieldState) => void,
    currentValueRef: { current: string },
  ): Promise<ValidationState> {
    if (!username) {
      setter(prev => ({ ...prev, validation: 'idle' }));
      return 'idle';
    }
    setter(prev => ({ ...prev, validation: 'checking' }));
    try {
      const result = await client.setup.validateUsername(platform, username);
      if (currentValueRef.current.trim() !== username) return 'checking';
      const state: ValidationState = result.valid ? 'valid' : 'invalid';
      setter(prev => ({ ...prev, validation: state }));
      return state;
    } catch {
      if (currentValueRef.current.trim() !== username) return 'checking';
      setter(prev => ({ ...prev, validation: 'idle' }));
      return 'idle';
    }
  }

  const lichessValueRef = useRef('');
  const chesscomValueRef = useRef('');

  const debouncedValidateLichess = useCallback(
    debounce((username: string) => {
      validateField('lichess', username, setLichess, lichessValueRef);
    }, 500),
    [],
  );

  const debouncedValidateChesscom = useCallback(
    debounce((username: string) => {
      validateField('chesscom', username, setChesscom, chesscomValueRef);
    }, 500),
    [],
  );

  function handleLichessInput(e: Event) {
    const value = (e.currentTarget as HTMLInputElement).value;
    lichessValueRef.current = value;
    const trimmed = value.trim();
    setLichess({ value, validation: trimmed ? 'checking' : 'idle' });
    debouncedValidateLichess(trimmed);
  }

  function handleChesscomInput(e: Event) {
    const value = (e.currentTarget as HTMLInputElement).value;
    chesscomValueRef.current = value;
    const trimmed = value.trim();
    setChesscom({ value, validation: trimmed ? 'checking' : 'idle' });
    debouncedValidateChesscom(trimmed);
  }

  async function validateAllFields(): Promise<{ lichessState: ValidationState; chesscomState: ValidationState }> {
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
    return errors;
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

    try {
      const result = await client.setup.complete({ lichess: lichessUsername, chesscom: chesscomUsername });
      const jobIds = result.import_job_ids ?? [];

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
          <form id="setupForm" onSubmit={handleSubmit}>
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
              <FieldStatus state={lichess.validation} />
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
              <FieldStatus state={chesscom.validation} />
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
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{
              __html: t('setup.help', { link: `<a href="https://github.com/anthropics/blunder-tutor">${t('setup.documentation')}</a>` }),
            }}
          />
        </div>
      </div>
    </div>
  );
}
