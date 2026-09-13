import type { ComponentChildren } from 'preact';

interface BreakdownSectionProps {
  title: string;
  description: string;
  helpButton?: ComponentChildren;
  scopeNote?: string;
  children: ComponentChildren;
}

export function BreakdownSection({ title, description, helpButton, scopeNote, children }: BreakdownSectionProps) {
  return (
    <div class="chart-container">
      <div class="chart-title">
        {title}
        {helpButton}
      </div>
      <p class="chart-description">{description}</p>
      {scopeNote && <p class="dashboard-scope-note">{scopeNote}</p>}
      {children}
    </div>
  );
}
