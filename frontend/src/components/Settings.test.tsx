import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Settings } from './Settings';

describe('Settings', () => {
  it('should render settings button', () => {
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('should show settings toggle with down arrow initially', () => {
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);
    expect(screen.getByText('▼')).toBeInTheDocument();
  });

  it('should not show weight input initially', () => {
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);
    expect(screen.queryByDisplayValue('70')).not.toBeInTheDocument();
  });

  it('should open settings panel on button click', async () => {
    const user = userEvent.setup();
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);

    const settingsButton = screen.getByRole('button', { name: /Settings/ });
    await user.click(settingsButton);

    expect(screen.getByDisplayValue('70')).toBeInTheDocument();
  });

  it('should show up arrow when settings open', async () => {
    const user = userEvent.setup();
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);

    const settingsButton = screen.getByRole('button', { name: /Settings/ });
    await user.click(settingsButton);

    expect(screen.getByText('▲')).toBeInTheDocument();
    expect(screen.queryByText('▼')).not.toBeInTheDocument();
  });

  it('should close settings panel on button click again', async () => {
    const user = userEvent.setup();
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);

    const settingsButton = screen.getByRole('button', { name: /Settings/ });

    // Open
    await user.click(settingsButton);
    expect(screen.getByDisplayValue('70')).toBeInTheDocument();

    // Close
    await user.click(settingsButton);
    expect(screen.queryByDisplayValue('70')).not.toBeInTheDocument();
  });

  it('should update weight input value on change', async () => {
    const user = userEvent.setup();
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);

    const settingsButton = screen.getByRole('button', { name: /Settings/ });
    await user.click(settingsButton);

    const input = screen.getByDisplayValue('70') as HTMLInputElement;
    await user.clear(input);
    await user.type(input, '75');

    expect(input.value).toBe('75');
  });

  it('should call onWeightChange with new weight on save', async () => {
    const user = userEvent.setup();
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);

    const settingsButton = screen.getByRole('button', { name: /Settings/ });
    await user.click(settingsButton);

    const input = screen.getByDisplayValue('70');
    await user.clear(input);
    await user.type(input, '80');

    const saveButton = screen.getByRole('button', { name: 'Save' });
    await user.click(saveButton);

    expect(onWeightChange).toHaveBeenCalledWith(80);
  });

  it('should handle decimal weight values', async () => {
    const user = userEvent.setup();
    const onWeightChange = vi.fn();
    render(<Settings weight={70.5} onWeightChange={onWeightChange} />);

    const settingsButton = screen.getByRole('button', { name: /Settings/ });
    await user.click(settingsButton);

    const input = screen.getByDisplayValue('70.5');
    await user.clear(input);
    await user.type(input, '75.75');

    const saveButton = screen.getByRole('button', { name: 'Save' });
    await user.click(saveButton);

    expect(onWeightChange).toHaveBeenCalledWith(75.75);
  });

  it('should not call onWeightChange for invalid input', async () => {
    const user = userEvent.setup();
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);

    const settingsButton = screen.getByRole('button', { name: /Settings/ });
    await user.click(settingsButton);

    const input = screen.getByDisplayValue('70');
    await user.clear(input);
    await user.type(input, 'abc');

    const saveButton = screen.getByRole('button', { name: 'Save' });
    await user.click(saveButton);

    expect(onWeightChange).not.toHaveBeenCalled();
  });

  it('should not call onWeightChange for negative weight', async () => {
    const user = userEvent.setup();
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);

    const settingsButton = screen.getByRole('button', { name: /Settings/ });
    await user.click(settingsButton);

    const input = screen.getByDisplayValue('70');
    await user.clear(input);
    await user.type(input, '-50');

    const saveButton = screen.getByRole('button', { name: 'Save' });
    await user.click(saveButton);

    expect(onWeightChange).not.toHaveBeenCalled();
  });

  it('should not call onWeightChange for zero weight', async () => {
    const user = userEvent.setup();
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);

    const settingsButton = screen.getByRole('button', { name: /Settings/ });
    await user.click(settingsButton);

    const input = screen.getByDisplayValue('70');
    await user.clear(input);
    await user.type(input, '0');

    const saveButton = screen.getByRole('button', { name: 'Save' });
    await user.click(saveButton);

    expect(onWeightChange).not.toHaveBeenCalled();
  });

  it('should update input when weight prop changes', async () => {
    const onWeightChange = vi.fn();
    const { rerender } = render(<Settings weight={70} onWeightChange={onWeightChange} />);

    const settingsButton = screen.getByRole('button', { name: /Settings/ });
    await userEvent.setup().click(settingsButton);

    expect(screen.getByDisplayValue('70')).toBeInTheDocument();

    rerender(<Settings weight={80} onWeightChange={onWeightChange} />);

    expect(screen.getByDisplayValue('80')).toBeInTheDocument();
  });

  it('should have correct input attributes', async () => {
    const user = userEvent.setup();
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);

    const settingsButton = screen.getByRole('button', { name: /Settings/ });
    await user.click(settingsButton);

    const input = screen.getByDisplayValue('70') as HTMLInputElement;
    expect(input.type).toBe('number');
    expect(input.min).toBe('1');
    expect(input.step).toBe('0.1');
  });

  it('should display weight label', async () => {
    const user = userEvent.setup();
    const onWeightChange = vi.fn();
    render(<Settings weight={70} onWeightChange={onWeightChange} />);

    const settingsButton = screen.getByRole('button', { name: /Settings/ });
    await user.click(settingsButton);

    expect(screen.getByText('Weight (kg)')).toBeInTheDocument();
  });
});
