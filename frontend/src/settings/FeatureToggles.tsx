import { useState, useCallback } from 'preact/hooks';
import type { FeatureGroup } from './types';

interface FeatureTogglesProps {
  groups: FeatureGroup[];
  onSave: (flags: Record<string, boolean>) => Promise<unknown>;
  onFeatureChanged?: (featureId: string, enabled: boolean) => void;
}

export function FeatureToggles({ groups, onSave, onFeatureChanged }: FeatureTogglesProps) {
  const [features, setFeatures] = useState(() => {
    const map: Record<string, boolean> = {};
    for (const group of groups) {
      for (const f of group.features) {
        map[f.id] = f.enabled;
      }
    }
    return map;
  });

  const handleToggle = useCallback(async (featureId: string, newValue: boolean) => {
    setFeatures(prev => ({ ...prev, [featureId]: newValue }));

    try {
      await onSave({ [featureId]: newValue });
      if (window.__features) window.__features[featureId] = newValue;
      if (onFeatureChanged) onFeatureChanged(featureId, newValue);
    } catch {
      setFeatures(prev => ({ ...prev, [featureId]: !newValue }));
    }
  }, [onSave, onFeatureChanged]);

  return (
    <div class="feature-toggles">
      {groups.map(group => (
        <div class="feature-group" key={group.label}>
          <div class="feature-group-title">{t(group.label)}</div>
          {group.features.map(f => (
            <label class="feature-toggle-row" key={f.id}>
              <input
                type="checkbox"
                class="feature-toggle"
                checked={features[f.id] ?? false}
                onChange={() => { void handleToggle(f.id, !(features[f.id] ?? false)); }}
                aria-label={t(f.label)}
              />
              <span>{t(f.label)}</span>
            </label>
          ))}
        </div>
      ))}
    </div>
  );
}
