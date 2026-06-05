import type { ComponentChildren } from 'preact';

export interface SectionProps {
  title?: string;
  children: ComponentChildren;
}

export function Section({ title, children }: SectionProps) {
  return (
    <section>
      {title && <h2>{title}</h2>}
      {children}
    </section>
  );
}
