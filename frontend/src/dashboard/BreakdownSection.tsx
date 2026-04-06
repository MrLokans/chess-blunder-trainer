import type { ComponentChildren } from 'preact';

interface BreakdownSectionProps {
  title: string;
  description: string;
  helpButton?: ComponentChildren;
  children: ComponentChildren;
}

export function BreakdownSection({ title, description, helpButton, children }: BreakdownSectionProps) {
  return (
    <div class="chart-container">
      <div class="chart-title">
        {title}
        {helpButton}
      </div>
      <p class="chart-description">{description}</p>
      {children}
    </div>
  );
}
