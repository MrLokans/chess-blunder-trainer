export type TextInputType = 'text' | 'email' | 'password' | 'number';

export interface TextInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  autoComplete?: string;
  type?: TextInputType;
  id?: string;
  name?: string;
  invalid?: boolean;
  required?: boolean;
  minLength?: number;
  // Injected by FormField via cloneElement; forwarded so label/error
  // associations reach the native input.
  'aria-describedby'?: string;
  'aria-required'?: boolean;
  'aria-invalid'?: boolean;
}

export function TextInput({
  value, onChange, placeholder, disabled = false, autoComplete,
  type = 'text', id, name, invalid = false, required, minLength,
  'aria-describedby': ariaDescribedby,
  'aria-required': ariaRequired,
  'aria-invalid': ariaInvalid,
}: TextInputProps) {
  return (
    <input
      // Preact 11 types <input> as a union keyed on a literal `type`, which a union-typed
      // value can't match; the lint rule checks the attribute alone and misses that.
      // eslint-disable-next-line @typescript-eslint/no-unnecessary-type-assertion
      type={type as 'text'}
      id={id}
      name={name}
      class={`text-input${invalid ? ' text-input--invalid' : ''}`}
      value={value}
      placeholder={placeholder}
      disabled={disabled}
      autoComplete={autoComplete}
      required={required}
      minLength={minLength}
      aria-describedby={ariaDescribedby}
      aria-required={ariaRequired || undefined}
      aria-invalid={invalid || ariaInvalid || undefined}
      onInput={(e) => { onChange(e.currentTarget.value); }}
    />
  );
}
