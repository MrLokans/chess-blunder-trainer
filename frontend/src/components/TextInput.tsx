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
}

export function TextInput({
  value,
  onChange,
  placeholder,
  disabled = false,
  autoComplete,
  type = 'text',
  id,
  name,
  invalid = false,
}: TextInputProps) {
  return (
    <input
      type={type}
      id={id}
      name={name}
      class={`text-input${invalid ? ' text-input--invalid' : ''}`}
      value={value}
      placeholder={placeholder}
      disabled={disabled}
      autoComplete={autoComplete}
      aria-invalid={invalid || undefined}
      onInput={(e) => { onChange(e.currentTarget.value); }}
    />
  );
}
