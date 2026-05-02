export interface ToggleProps {
  value: boolean;
  onChange: (value: boolean) => void;
  label?: string;
  disabled?: boolean;
  id?: string;
  ariaLabel?: string;
}

export function Toggle({ value, onChange, label, disabled = false, id, ariaLabel }: ToggleProps) {
  const handleClick = () => {
    if (!disabled) onChange(!value);
  };

  return (
    <span class={`toggle${disabled ? ' toggle--disabled' : ''}`} onClick={handleClick}>
      <button
        type="button"
        id={id}
        role="switch"
        aria-checked={value}
        aria-label={ariaLabel ?? label}
        disabled={disabled}
        class={`toggle__track${value ? ' toggle__track--on' : ''}`}
        onClick={(e) => { e.stopPropagation(); handleClick(); }}
      >
        <span class="toggle__thumb" aria-hidden="true" />
      </button>
      {label && <span class="toggle__label">{label}</span>}
    </span>
  );
}
