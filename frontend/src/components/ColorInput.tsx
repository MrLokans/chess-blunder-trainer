import { useState, useEffect, useCallback } from 'preact/hooks';

export interface ColorInputProps {
  value: string;
  onChange: (value: string) => void;
}

const HEX_PATTERN = /^#[0-9A-Fa-f]{6}$/;

export function ColorInput({ value, onChange }: ColorInputProps) {
  const [localHex, setLocalHex] = useState(value.toUpperCase());

  useEffect(() => {
    setLocalHex(value.toUpperCase());
  }, [value]);

  const handleColorChange = useCallback((e: Event) => {
    const input = e.target as HTMLInputElement;
    const upper = input.value.toUpperCase();
    setLocalHex(upper);
    onChange(upper);
  }, [onChange]);

  const handleHexInput = useCallback((e: Event) => {
    const input = e.target as HTMLInputElement;
    setLocalHex(input.value);
    let val = input.value.trim();
    if (!val.startsWith('#')) val = '#' + val;
    if (HEX_PATTERN.test(val)) {
      onChange(val.toUpperCase());
    }
  }, [onChange]);

  return (
    <span class="color-input-pair">
      <input
        type="color"
        value={value.toLowerCase()}
        aria-label="color picker"
        onInput={handleColorChange}
      />
      <input
        type="text"
        value={localHex}
        aria-label="hex value"
        onInput={handleHexInput}
      />
    </span>
  );
}
