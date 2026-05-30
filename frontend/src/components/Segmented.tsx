export interface SegmentedOption<T> {
  label: string;
  value: T;
}

export interface SegmentedProps<T> {
  options: SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel?: string;
}

export function Segmented<T>({ options, value, onChange, ariaLabel }: SegmentedProps<T>) {
  return (
    <div class="segmented" role="group" aria-label={ariaLabel}>
      {options.map(opt => (
        <button
          key={String(opt.value)}
          type="button"
          class={`segmented__btn${opt.value === value ? ' segmented__btn--active' : ''}`}
          aria-pressed={opt.value === value}
          onClick={() => { onChange(opt.value); }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
