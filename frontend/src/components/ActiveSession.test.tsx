import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ActiveSession } from './ActiveSession';
import type { HikingSession } from '../types';

describe('ActiveSession', () => {
  const mockSession: HikingSession = {
    isActive: true,
    sessionId: '123',
    startTime: '2024-03-15T10:00:00Z',
    endTime: '2024-03-15T11:30:00Z',
    stepCount: 5000,
    burnedCalories: 350.5,
    distanceWalked: 3500,
    bodyWeightKg: 75,
    hikeSessionTime: 'PT1H30M45S',
    isPaused: false,
  };

  it('should render active session section', () => {
    render(<ActiveSession session={mockSession} />);
    expect(screen.getByText('Active Session')).toBeInTheDocument();
  });

  it('should display session start time', () => {
    render(<ActiveSession session={mockSession} />);
    expect(screen.getByText(/2024|Mar|15/)).toBeInTheDocument();
  });

  it('should display step count', () => {
    render(<ActiveSession session={mockSession} />);
    expect(screen.getByText('5000')).toBeInTheDocument();
  });

  it('should display burned calories with one decimal place', () => {
    render(<ActiveSession session={mockSession} />);
    expect(screen.getByText('350.5 kcal')).toBeInTheDocument();
  });

  it('should display distance in kilometers with two decimal places', () => {
    render(<ActiveSession session={mockSession} />);
    expect(screen.getByText('3.50 km')).toBeInTheDocument();
  });

  it('should display elapsed time in HH:MM:SS format', () => {
    render(<ActiveSession session={mockSession} />);
    expect(screen.getByText('01:30:45')).toBeInTheDocument();
  });

  it('should display Active status when not paused', () => {
    render(<ActiveSession session={mockSession} />);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('should display Paused status when paused', () => {
    const pausedSession: HikingSession = {
      ...mockSession,
      isPaused: true,
    };
    render(<ActiveSession session={pausedSession} />);
    expect(screen.getByText('Paused')).toBeInTheDocument();
  });

  it('should handle zero values correctly', () => {
    const zeroSession: HikingSession = {
      ...mockSession,
      stepCount: 0,
      burnedCalories: 0,
      distanceWalked: 0,
    };
    render(<ActiveSession session={zeroSession} />);
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('0.0 kcal')).toBeInTheDocument();
    expect(screen.getByText('0.00 km')).toBeInTheDocument();
  });

  it('should handle large values', () => {
    const largeSession: HikingSession = {
      ...mockSession,
      stepCount: 50000,
      burnedCalories: 5000.75,
      distanceWalked: 35000,
    };
    render(<ActiveSession session={largeSession} />);
    expect(screen.getByText('50000')).toBeInTheDocument();
    expect(screen.getByText('5000.8 kcal')).toBeInTheDocument();
    expect(screen.getByText('35.00 km')).toBeInTheDocument();
  });

  it('should parse and display ISO duration with only hours', () => {
    const sessionWithHoursOnly: HikingSession = {
      ...mockSession,
      hikeSessionTime: 'PT2H',
    };
    render(<ActiveSession session={sessionWithHoursOnly} />);
    expect(screen.getByText('02:00:00')).toBeInTheDocument();
  });

  it('should parse and display ISO duration with only minutes', () => {
    const sessionWithMinutesOnly: HikingSession = {
      ...mockSession,
      hikeSessionTime: 'PT45M',
    };
    render(<ActiveSession session={sessionWithMinutesOnly} />);
    expect(screen.getByText('00:45:00')).toBeInTheDocument();
  });
});
