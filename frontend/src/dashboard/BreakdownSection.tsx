import type { ComponentChildren } from 'preact';

interface BreakdownSectionProps {
  title: string;
  description: string;
  helpButton?: ComponentChildren;
  wide?: boolean;
  children: ComponentChildren;
}

export function BreakdownSection({ title, description, helpButton, wide = false, children }: BreakdownSectionProps) {
  return (
    <div class={`chart-container${wide ? ' chart-container--wide' : ''}`}>
      <h3 class="chart-title">
        {title}
        {helpButton}
      </h3>
      <p class="chart-description">{description}</p>
      {children}
    </div>
  );
}
