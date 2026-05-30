import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/preact';
import { EngineControls } from '../../src/game-review/EngineControls';

function baseProps() {
  return {
    analysisMode: true,
    multipv: 2,
    maxDepth: 20,
    depth: 18,
    showArrows: true,
    showThreats: false,
    exploring: false,
    onToggleAnalysis: vi.fn(),
    onMultiPv: vi.fn(),
    onMaxDepth: vi.fn(),
    onToggleArrows: vi.fn(),
    onToggleThreats: vi.fn(),
    onBackToGame: vi.fn(),
  };
}

describe('EngineControls', () => {
  it('renders the max-depth slider reflecting maxDepth', () => {
    const { container } = render(<EngineControls {...baseProps()} />);
    const range = container.querySelector('input[type="range"]') as HTMLInputElement;
    expect(range).not.toBeNull();
    expect(range.value).toBe('20');
  });

  it('calls onMaxDepth when the slider changes', () => {
    const props = baseProps();
    const { container } = render(<EngineControls {...props} />);
    const range = container.querySelector('input[type="range"]') as HTMLInputElement;
    range.value = '14';
    fireEvent.input(range);
    expect(props.onMaxDepth).toHaveBeenCalledWith(14);
  });

  it('renders the depth/max progress readout', () => {
    const { container } = render(<EngineControls {...baseProps()} />);
    // 18/20 → 90% fill
    const fill = container.querySelector('.engine-depth-progress__fill') as HTMLElement;
    expect(fill).not.toBeNull();
    expect(fill.style.width).toBe('90%');
  });

  it('calls onMultiPv from the segmented control', () => {
    const props = baseProps();
    const { getByText } = render(<EngineControls {...props} />);
    fireEvent.click(getByText('4'));
    expect(props.onMultiPv).toHaveBeenCalledWith(4);
  });

  it('hides analysis sub-controls when analysisMode is false', () => {
    const { container } = render(<EngineControls {...baseProps()} analysisMode={false} />);
    expect(container.querySelector('input[type="range"]')).toBeNull();
  });
});
