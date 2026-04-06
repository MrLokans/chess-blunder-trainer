import { useCallback } from 'preact/hooks';

interface ColorInputProps {
  value: string;
  onChange: (value: string) => void;
}

const HEX_PATTERN = /^#[0-9A-Fa-f]{6}$/;

export function ColorInput({ value, onChange }: ColorInputProps) {
  const handleColorChange = useCallback((e: Event) => {
    const input = e.target as HTMLInputElement;
    onChange(input.value.toUpperCase());
  }, [onChange]);

  const handleHexChange = useCallback((e: Event) => {
    const input = e.target as HTMLInputElement;
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
        value={value.toUpperCase()}
        aria-label="hex value"
        onInput={handleHexChange}
      />
    </span>
  );
}
