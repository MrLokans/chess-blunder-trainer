import type { ComponentChildren, VNode } from 'preact';
import { cloneElement, isValidElement } from 'preact';
import { useId } from 'preact/hooks';

export interface FormFieldProps {
  label: string;
  htmlFor?: string;
  helpText?: string;
  error?: string;
  required?: boolean;
  children: ComponentChildren;
}

interface ChildAriaProps {
  id?: string;
  name?: string;
  'aria-describedby'?: string;
  'aria-invalid'?: boolean;
  'aria-required'?: boolean;
}

export function FormField({ label, htmlFor, helpText, error, required, children }: FormFieldProps) {
  const generatedId = useId();
  const helpId = useId();
  const errorId = useId();

  const hasError = Boolean(error);
  const inputId = htmlFor ?? generatedId;
  const describedBy = hasError ? errorId : helpText ? helpId : undefined;

  const enhancedChild = isValidElement(children)
    ? cloneElement(children as VNode<ChildAriaProps>, {
        id: (children as VNode<ChildAriaProps>).props.id ?? inputId,
        'aria-describedby': describedBy,
        'aria-invalid': hasError || undefined,
        'aria-required': required || undefined,
      })
    : children;

  return (
    <div class={`form-field${hasError ? ' form-field--error' : ''}`}>
      <label class="form-field__label" htmlFor={inputId}>
        {label}
        {required && <span class="form-field__required" aria-hidden="true">*</span>}
      </label>
      <div class="form-field__control">{enhancedChild}</div>
      {hasError ? (
        <div id={errorId} class="form-field__error" role="alert">{error}</div>
      ) : helpText ? (
        <div id={helpId} class="form-field__help">{helpText}</div>
      ) : null}
    </div>
  );
}
