import type { ComponentChildren } from 'preact';

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ComponentChildren;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  const heading = (
    <h2>{title}</h2>
  );

  return (
    <header class="page-header">
      {actions ? (
        <div class="flex items-center justify-between">
          {heading}
          <div class="page-header__actions">{actions}</div>
        </div>
      ) : (
        heading
      )}
      {subtitle && <p class="subtitle">{subtitle}</p>}
    </header>
  );
}
