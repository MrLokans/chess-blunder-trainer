import { useState, useRef, useEffect, useCallback } from 'preact/hooks';

export interface DropdownOption {
  value: string;
  label: string;
}

export interface DropdownProps {
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
}

export function Dropdown({ options, value, onChange }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const selectedLabel = options.find(o => o.value === value)?.label ?? '';

  const handleSelect = useCallback((optionValue: string) => {
    onChange(optionValue);
    setOpen(false);
    setFocusedIndex(-1);
  }, [onChange]);

  const handleOpen = useCallback(() => {
    setOpen(true);
    const currentIndex = options.findIndex(o => o.value === value);
    setFocusedIndex(currentIndex >= 0 ? currentIndex : 0);
  }, [options, value]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!open) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleOpen();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown': {
        e.preventDefault();
        setFocusedIndex(i => (i + 1) % options.length);
        break;
      }
      case 'ArrowUp': {
        e.preventDefault();
        setFocusedIndex(i => (i - 1 + options.length) % options.length);
        break;
      }
      case 'Enter':
      case ' ': {
        e.preventDefault();
        const focused = options[focusedIndex];
        if (focused) handleSelect(focused.value);
        break;
      }
      case 'Escape': {
        e.preventDefault();
        setOpen(false);
        setFocusedIndex(-1);
        break;
      }
      case 'Home': {
        e.preventDefault();
        setFocusedIndex(0);
        break;
      }
      case 'End': {
        e.preventDefault();
        setFocusedIndex(options.length - 1);
        break;
      }
    }
  }, [open, options, focusedIndex, handleSelect, handleOpen]);

  useEffect(() => {
    if (!open) return;

    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
        setFocusedIndex(-1);
      }
    }

    document.addEventListener('click', handleClickOutside);
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [open]);

  return (
    <div class="custom-dropdown" ref={wrapperRef}>
      <button
        type="button"
        class="custom-dropdown__trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => { open ? setOpen(false) : handleOpen(); }}
        onKeyDown={handleKeyDown}
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
          {options.map((opt, i) => (
            <li
              key={opt.value}
              class={
                'custom-dropdown__option'
                + (opt.value === value ? ' custom-dropdown__option--selected' : '')
                + (i === focusedIndex ? ' custom-dropdown__option--focused' : '')
              }
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
