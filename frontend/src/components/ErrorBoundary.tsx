import { Component } from 'preact';
import type { ComponentChildren } from 'preact';
import { Button } from './Button';

interface Props {
  children: ComponentChildren;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error): void {
    console.error('Uncaught error in component tree:', error);
  }

  render() {
    if (this.state.error) {
      return (
        <div class="error-boundary" role="alert">
          <h2>{t('common.error')}</h2>
          <p>{t('common.error_boundary_message')}</p>
          <Button variant="primary" onClick={() => { window.location.reload(); }}>
            {t('common.reload')}
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
