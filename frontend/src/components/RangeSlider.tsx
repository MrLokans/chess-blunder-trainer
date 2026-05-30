export interface RangeSliderProps {
  min: number;
  max: number;
  value: number;
  onChange: (value: number) => void;
  id?: string;
  ariaLabel?: string;
}

export function RangeSlider({ min, max, value, onChange, id, ariaLabel }: RangeSliderProps) {
  return (
    <input
      type="range"
      class="range"
      id={id}
      min={min}
      max={max}
      value={value}
      aria-label={ariaLabel}
      onInput={(e) => { onChange(Number(e.currentTarget.value)); }}
    />
  );
}
