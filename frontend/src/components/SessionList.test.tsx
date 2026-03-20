import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SessionList } from './SessionList';
import type { HikingSession } from '../types';

describe('SessionList', () => {
  const mockSessions: HikingSession[] = [
    {
      isActive: false,
      sessionId: '1',
      startTime: '2024-03-10T09:00:00Z',
      endTime: '2024-03-10T10:30:00Z',
      stepCount: 4000,
      burnedCalories: 250,
      distanceWalked: 3000,
      bodyWeightKg: 70,
    },
    {
      isActive: false,
      sessionId: '2',
      startTime: '2024-03-08T14:00:00Z',
      endTime: '2024-03-08T15:15:00Z',
      stepCount: 3500,
      burnedCalories: 200,
      distanceWalked: 2500,
      bodyWeightKg: 70,
    },
  ];

  it('should render session list section', () => {
    const onDelete = vi.fn();
    render(<SessionList sessions={mockSessions} onDelete={onDelete} />);
    expect(screen.getByText('Past Sessions')).toBeInTheDocument();
  });

  it('should display empty message when no sessions', () => {
    const onDelete = vi.fn();
    render(<SessionList sessions={[]} onDelete={onDelete} />);
    expect(screen.getByText('No past sessions yet.')).toBeInTheDocument();
  });

  it('should display all sessions', () => {
    const onDelete = vi.fn();
    render(<SessionList sessions={mockSessions} onDelete={onDelete} />);
    // Check for distance values in headers
    expect(screen.getByText(/3.00 km/)).toBeInTheDocument();
    expect(screen.getByText(/2.50 km/)).toBeInTheDocument();
  });

  it('should sort sessions by end time newest first', () => {
    const onDelete = vi.fn();
    const unsortedSessions: HikingSession[] = [
      {
        ...mockSessions[1],
        endTime: '2024-03-08T15:15:00Z',
      },
      {
        ...mockSessions[0],
        endTime: '2024-03-10T10:30:00Z',
      },
    ];

    render(<SessionList sessions={unsortedSessions} onDelete={onDelete} />);
    const sessionHeaders = screen.getAllByText(/km/);
    // Newest session (3.00 km) should appear first
    expect(sessionHeaders[0].textContent).toContain('3.00 km');
  });

  it('should expand session details on click', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();

    render(<SessionList sessions={mockSessions} onDelete={onDelete} />);

    const sessionHeader = screen.getAllByText(/km/)[0];
    await user.click(sessionHeader);

    // Should show expanded details
    expect(screen.getByText('Start')).toBeInTheDocument();
    expect(screen.getByText('End')).toBeInTheDocument();
    expect(screen.getByText('Steps')).toBeInTheDocument();
    expect(screen.getByText('Calories')).toBeInTheDocument();
    expect(screen.getByText('Distance')).toBeInTheDocument();
    expect(screen.getByText('Body Weight')).toBeInTheDocument();
  });

  it('should show delete button when expanded', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();

    render(<SessionList sessions={mockSessions} onDelete={onDelete} />);

    const sessionHeader = screen.getAllByText(/km/)[0];
    await user.click(sessionHeader);

    expect(screen.getByText('Delete Session')).toBeInTheDocument();
  });

  it('should call onDelete with session ID', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();

    render(<SessionList sessions={mockSessions} onDelete={onDelete} />);

    const sessionHeader = screen.getAllByText(/km/)[0];
    await user.click(sessionHeader);

    const deleteButton = screen.getByText('Delete Session');
    await user.click(deleteButton);

    expect(onDelete).toHaveBeenCalledWith('1');
  });

  it('should collapse session when clicked again', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();

    render(<SessionList sessions={mockSessions} onDelete={onDelete} />);

    const sessionHeader = screen.getAllByText(/km/)[0];

    // Expand
    await user.click(sessionHeader);
    expect(screen.getByText('Delete Session')).toBeInTheDocument();

    // Collapse
    await user.click(sessionHeader);
    expect(screen.queryByText('Delete Session')).not.toBeInTheDocument();
  });

  it('should display correct session data in expanded view', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();

    render(<SessionList sessions={mockSessions} onDelete={onDelete} />);

    const sessionHeader = screen.getAllByText(/km/)[0];
    await user.click(sessionHeader);

    expect(screen.getByText('4000')).toBeInTheDocument();
    expect(screen.getByText('250.0 kcal')).toBeInTheDocument();
    expect(screen.getByText('3.00 km')).toBeInTheDocument();
    expect(screen.getByText('70.0 kg')).toBeInTheDocument();
  });

  it('should toggle expand icon', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();

    render(<SessionList sessions={mockSessions} onDelete={onDelete} />);

    const expandIcons = document.querySelectorAll('.expand-icon');
    const initialIcon = expandIcons[0].textContent;

    await user.click(expandIcons[0]);

    // Icon should change
    expect(expandIcons[0].textContent).not.toBe(initialIcon);
  });

  it('should handle multiple sessions expansion independently', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();

    render(<SessionList sessions={mockSessions} onDelete={onDelete} />);

    const headers = screen.getAllByText(/km/);

    // Expand first session
    await user.click(headers[0]);
    expect(screen.getByText('4000')).toBeInTheDocument();

    // Expand second session should not show first session details
    await user.click(headers[1]);
    expect(screen.getByText('3500')).toBeInTheDocument();

    // First session details should be hidden now
    expect(screen.queryByText('4000')).not.toBeInTheDocument();
  });
});
