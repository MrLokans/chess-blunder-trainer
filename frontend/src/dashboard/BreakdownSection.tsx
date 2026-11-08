import type { ComponentChildren } from 'preact';

interface BreakdownSectionProps {
  title: string;
  description: string;
  helpButton?: ComponentChildren;
  wide?: boolean;
  id?: string;
  children: ComponentChildren;
}

export function BreakdownSection({ title, description, helpButton, wide = false, id, children }: BreakdownSectionProps) {
  return (
    <div id={id} class={`chart-container${wide ? ' chart-container--wide' : ''}`}>
      <h3 class="chart-title">
        {title}
        {helpButton}
      </h3>
      <p class="chart-description">{description}</p>
      {children}
    </div>
  );
}
