import { useState, useRef, useEffect, useCallback } from 'preact/hooks';

export interface DropdownOption {
  value: string;
  label: string;
}

interface DropdownProps {
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
}

export function Dropdown({ options, value, onChange }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const selectedLabel = options.find(o => o.value === value)?.label ?? '';

  const handleSelect = useCallback((optionValue: string) => {
    onChange(optionValue);
    setOpen(false);
  }, [onChange]);

  useEffect(() => {
    if (!open) return;

    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }

    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }

    document.addEventListener('click', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('click', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  return (
    <div class="custom-dropdown" ref={wrapperRef}>
      <button
        type="button"
        class="custom-dropdown__trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => { setOpen(!open); }}
        onKeyDown={(e) => { if (e.key === 'Escape') setOpen(false); }}
      >
        <span class="custom-dropdown__label">{selectedLabel}</span>
        <span class="custom-dropdown__arrow">
          <svg width="12" height="8" viewBox="0 0 12 8" fill="none">
            <path d="M1 1l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </span>
      </button>
      {open && (
        <ul class="custom-dropdown__options custom-dropdown__options--open" role="listbox">
          {options.map(opt => (
            <li
              key={opt.value}
              class={`custom-dropdown__option${opt.value === value ? ' custom-dropdown__option--selected' : ''}`}
              role="option"
              aria-selected={opt.value === value}
              onClick={() => { handleSelect(opt.value); }}
            >
              {opt.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
