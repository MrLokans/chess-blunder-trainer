import type { ComponentChildren } from 'preact';
import { useCallback, useId } from 'preact/hooks';

export interface TabDescriptor<K extends string = string> {
  key: K;
  label: string;
  badge?: string | number;
  disabled?: boolean;
}

export interface TabsProps<K extends string = string> {
  tabs: TabDescriptor<K>[];
  value: K;
  onChange: (key: K) => void;
  children?: ComponentChildren;
}

export function Tabs<K extends string = string>({
  tabs,
  value,
  onChange,
  children,
}: TabsProps<K>) {
  const groupId = useId();

  const moveFocusTo = useCallback((startIndex: number, dir: 1 | -1) => {
    if (tabs.length === 0) return;
    const tryFrom = (i: number) => {
      let pos = i;
      for (let step = 0; step < tabs.length; step += 1) {
        const tab = tabs[pos];
        if (tab && !tab.disabled) {
          onChange(tab.key);
          return;
        }
        pos = (pos + dir + tabs.length) % tabs.length;
      }
    };
    tryFrom((startIndex + dir + tabs.length) % tabs.length);
  }, [tabs, onChange]);

  const handleKeyDown = useCallback((e: KeyboardEvent, currentIndex: number) => {
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      moveFocusTo(currentIndex, 1);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      moveFocusTo(currentIndex, -1);
    } else if (e.key === 'Home') {
      e.preventDefault();
      moveFocusTo(-1, 1);
    } else if (e.key === 'End') {
      e.preventDefault();
      moveFocusTo(tabs.length, -1);
    }
  }, [tabs, moveFocusTo]);

  const tabId = (key: K) => `${groupId}-tab-${key}`;
  const panelId = (key: K) => `${groupId}-panel-${key}`;

  return (
    <div class="tabs">
      <div class="tabs__bar" role="tablist">
        {tabs.map((tab, i) => {
          const active = tab.key === value;
          return (
            <button
              key={tab.key}
              id={tabId(tab.key)}
              type="button"
              role="tab"
              aria-selected={active}
              aria-controls={panelId(tab.key)}
              tabIndex={active ? 0 : -1}
              disabled={tab.disabled}
              class={`tabs__tab${active ? ' tabs__tab--active' : ''}${tab.disabled ? ' tabs__tab--disabled' : ''}`}
              onClick={() => { if (!tab.disabled) onChange(tab.key); }}
              onKeyDown={(e) => { handleKeyDown(e, i); }}
            >
              <span class="tabs__label">{tab.label}</span>
              {tab.badge !== undefined && (
                <span class="tabs__badge">{tab.badge}</span>
              )}
            </button>
          );
        })}
      </div>
      <div
        key={value}
        id={panelId(value)}
        class="tabs__panel"
        role="tabpanel"
        aria-labelledby={tabId(value)}
        tabIndex={0}
      >
        {children}
      </div>
    </div>
  );
}
