import type { ComponentChildren } from 'preact';

export interface EmptyStateProps {
  icon?: ComponentChildren;
  title: string;
  message: string;
  action?: ComponentChildren;
}

export function EmptyState({ icon, title, message, action }: EmptyStateProps) {
  return (
    <div class="empty-state">
      {icon && <div class="empty-state-icon">{icon}</div>}
      <h2 class="empty-state-title">{title}</h2>
      <p class="empty-state-message">{message}</p>
      {action && <div class="empty-state-actions">{action}</div>}
    </div>
  );
}
