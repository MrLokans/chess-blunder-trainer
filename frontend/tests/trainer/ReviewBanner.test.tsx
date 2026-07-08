import { describe, test, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { ReviewBanner } from '../../src/trainer/components/ReviewBanner';

describe('ReviewBanner', () => {
  test('renders nothing when no reviews are due', () => {
    const { container } = render(<ReviewBanner dueCount={0} onStart={() => {}} />);
    expect(container.innerHTML).toBe('');
  });

  test('shows the due count via i18n', () => {
    render(<ReviewBanner dueCount={7} onStart={() => {}} />);
    const banner = screen.getByTestId('srs-review-banner');
    expect(banner.textContent).toContain('trainer.srs.banner');
  });

  test('fires onStart when the button is clicked', () => {
    const onStart = vi.fn();
    render(<ReviewBanner dueCount={3} onStart={onStart} />);
    fireEvent.click(screen.getByTestId('srs-start-review'));
    expect(onStart).toHaveBeenCalledTimes(1);
  });
});
