import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { FormField } from '../../src/components/FormField';

describe('FormField', () => {
  test('renders label and child', () => {
    render(
      <FormField label="Username">
        <input data-testid="child" />
      </FormField>,
    );
    expect(screen.getByText('Username')).toBeDefined();
    expect(screen.getByTestId('child')).toBeDefined();
  });

  test('renders helpText when no error', () => {
    render(
      <FormField label="X" helpText="Pick something good">
        <input />
      </FormField>,
    );
    expect(screen.getByText('Pick something good')).toBeDefined();
  });

  test('error replaces helpText and uses role=alert', () => {
    render(
      <FormField label="X" helpText="hint" error="Required">
        <input />
      </FormField>,
    );
    expect(screen.getByRole('alert').textContent).toBe('Required');
    expect(screen.queryByText('hint')).toBeNull();
  });

  test('error variant adds modifier class', () => {
    const { container } = render(
      <FormField label="X" error="bad">
        <input />
      </FormField>,
    );
    expect(container.firstElementChild?.className).toContain('form-field--error');
  });

  test('required marker appears when required', () => {
    const { container } = render(
      <FormField label="X" required>
        <input />
      </FormField>,
    );
    expect(container.querySelector('.form-field__required')).not.toBeNull();
  });

  test('htmlFor wires up to label and child id', () => {
    const { container } = render(
      <FormField label="X" htmlFor="my-input">
        <input />
      </FormField>,
    );
    expect(container.querySelector('label')?.getAttribute('for')).toBe('my-input');
    expect(container.querySelector('input')?.getAttribute('id')).toBe('my-input');
  });

  test('auto-generates an id and wires label + child when htmlFor omitted', () => {
    const { container } = render(
      <FormField label="X">
        <input />
      </FormField>,
    );
    const labelFor = container.querySelector('label')?.getAttribute('for');
    const inputId = container.querySelector('input')?.getAttribute('id');
    expect(labelFor).not.toBeNull();
    expect(inputId).toBe(labelFor);
  });

  test('helpText is wired via aria-describedby', () => {
    const { container } = render(
      <FormField label="X" helpText="explain">
        <input />
      </FormField>,
    );
    const describedBy = container.querySelector('input')?.getAttribute('aria-describedby');
    if (!describedBy) throw new Error('aria-describedby missing');
    expect(document.getElementById(describedBy)?.textContent).toBe('explain');
  });

  test('error wires aria-describedby + aria-invalid on the child', () => {
    const { container } = render(
      <FormField label="X" error="nope">
        <input />
      </FormField>,
    );
    const input = container.querySelector('input');
    const describedBy = input?.getAttribute('aria-describedby');
    if (!describedBy) throw new Error('aria-describedby missing');
    expect(input?.getAttribute('aria-invalid')).toBe('true');
    expect(document.getElementById(describedBy)?.textContent).toBe('nope');
  });

  test('required wires aria-required on the child', () => {
    const { container } = render(
      <FormField label="X" required>
        <input />
      </FormField>,
    );
    expect(container.querySelector('input')?.getAttribute('aria-required')).toBe('true');
  });
});
