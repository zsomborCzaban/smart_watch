import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import * as api from './api';
import { useWatchStatus } from './hooks/useWatchStatus';
import type { HikingSession } from './types';

// Mock the API module
vi.mock('./api');

// Type for mocked hooks
interface MockedUseWatchStatus {
  isConnected: boolean;
  activeSession: HikingSession | null;
  isActiveSession: boolean;
}

// Mock the hook
vi.mock('./hooks/useWatchStatus');

// Mock child components to simplify testing
vi.mock('./components/ActiveSession', () => ({
  ActiveSession: ({ session }: { session: HikingSession }) => (
    <div data-testid="active-session">
      Active Session: {session.sessionId}
    </div>
  ),
}));

vi.mock('./components/SessionList', () => ({
  SessionList: ({
    sessions,
    onDelete,
  }: {
    sessions: HikingSession[];
    onDelete: (id: string) => void;
  }) => (
    <div data-testid="session-list">
      {sessions.length === 0 ? (
        <p>No sessions</p>
      ) : (
        sessions.map((s) => (
          <div key={s.sessionId} data-testid={`session-${s.sessionId}`}>
            {s.sessionId}
            <button onClick={() => onDelete(s.sessionId)}>Delete</button>
          </div>
        ))
      )}
    </div>
  ),
}));

vi.mock('./components/Settings', () => ({
  Settings: ({
    weight,
    onWeightChange,
  }: {
    weight: number;
    onWeightChange: (w: number) => void;
  }) => (
    <div data-testid="settings">
      Weight: {weight}
      <button onClick={() => onWeightChange(80)}>Change to 80</button>
    </div>
  ),
}));

describe('App', () => {
  const mockSessions: HikingSession[] = [
    {
      isActive: true,
      sessionId: '1',
      startTime: '2024-03-15T10:00:00Z',
      endTime: '',
      stepCount: 5000,
      burnedCalories: 350,
      distanceWalked: 3500,
      bodyWeightKg: 75,
    },
    {
      isActive: false,
      sessionId: '2',
      startTime: '2024-03-14T09:00:00Z',
      endTime: '2024-03-14T10:30:00Z',
      stepCount: 4000,
      burnedCalories: 300,
      distanceWalked: 3000,
      bodyWeightKg: 75,
    },
    {
      isActive: false,
      sessionId: '3',
      startTime: '2024-03-13T14:00:00Z',
      endTime: '2024-03-13T15:00:00Z',
      stepCount: 3000,
      burnedCalories: 200,
      distanceWalked: 2000,
      bodyWeightKg: 75,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock default return values with proper typing
    const mockGetAllSessions = api.getAllSessions as ReturnType<typeof vi.fn>;
    mockGetAllSessions.mockResolvedValue(mockSessions);

    const mockGetWeight = api.getWeight as ReturnType<typeof vi.fn>;
    mockGetWeight.mockResolvedValue(75);

    const mockDeleteSession = api.deleteSession as ReturnType<typeof vi.fn>;
    mockDeleteSession.mockResolvedValue(undefined);

    const mockSetWeight = api.setWeight as ReturnType<typeof vi.fn>;
    mockSetWeight.mockResolvedValue(undefined);

    const mockUseWatchStatus = useWatchStatus as ReturnType<typeof vi.fn>;
    mockUseWatchStatus.mockReturnValue({
      isConnected: false,
      activeSession: null,
      isActiveSession: false,
    } as MockedUseWatchStatus);
  });

  describe('Rendering', () => {
    it('should render the app header with title', async () => {
      render(<App />);
      await waitFor(() => {
        expect(screen.getByText('Hiking Tracker')).toBeInTheDocument();
      });
    });

    it('should render watch status section', async () => {
      render(<App />);
      await waitFor(() => {
        expect(screen.getByText(/Watch/)).toBeInTheDocument();
      });
    });

    it('should render Settings component', async () => {
      render(<App />);
      await waitFor(() => {
        expect(screen.getByTestId('settings')).toBeInTheDocument();
      });
    });

    it('should render SessionList component', async () => {
      render(<App />);
      await waitFor(() => {
        expect(screen.getByTestId('session-list')).toBeInTheDocument();
      });
    });
  });

  describe('Watch Connection Status', () => {
    it('should display disconnected status initially', async () => {
      const mockUseWatchStatus = useWatchStatus as ReturnType<typeof vi.fn>;
      mockUseWatchStatus.mockReturnValue({
        isConnected: false,
        activeSession: null,
        isActiveSession: false,
      } as MockedUseWatchStatus);

      render(<App />);
      await waitFor(() => {
        expect(screen.getByText('Watch Disconnected')).toBeInTheDocument();
      });
    });

    it('should display connected status when watch is connected', async () => {
      const mockUseWatchStatus = useWatchStatus as ReturnType<typeof vi.fn>;
      mockUseWatchStatus.mockReturnValue({
        isConnected: true,
        activeSession: null,
        isActiveSession: false,
      } as MockedUseWatchStatus);

      render(<App />);
      await waitFor(() => {
        expect(screen.getByText('Watch Connected')).toBeInTheDocument();
      });
    });

    it('should pass correct WebSocket URL to useWatchStatus', async () => {
      act(() => {
        render(<App />);
      });

      await waitFor(() => {
        const mockUseWatchStatus = useWatchStatus as ReturnType<typeof vi.fn>;
        expect(mockUseWatchStatus).toHaveBeenCalledWith(
          expect.stringMatching(/^ws:\/\/.*\/api\/ws$/)
        );
      });
    });

    it('should update status when connection changes', async () => {
      const mockUseWatchStatus = useWatchStatus as ReturnType<typeof vi.fn>;

      const { rerender } = render(<App />);
      await waitFor(() => {
        expect(screen.getByText('Watch Disconnected')).toBeInTheDocument();
      });

      // Mock connected state
      act(() => {
        mockUseWatchStatus.mockReturnValue({
          isConnected: true,
          activeSession: null,
          isActiveSession: false,
        } as MockedUseWatchStatus);
      });

      rerender(<App />);
      await waitFor(() => {
        expect(screen.getByText('Watch Connected')).toBeInTheDocument();
      });
    });
  });

  describe('Initial Data Loading', () => {
    it('should fetch sessions on mount', async () => {
      render(<App />);

      await waitFor(() => {
        const mockGetAllSessions = api.getAllSessions as ReturnType<typeof vi.fn>;
        expect(mockGetAllSessions).toHaveBeenCalled();
      });
    });

    it('should fetch weight on mount', async () => {
      render(<App />);

      await waitFor(() => {
        const mockGetWeight = api.getWeight as ReturnType<typeof vi.fn>;
        expect(mockGetWeight).toHaveBeenCalled();
      });
    });

    it('should display fetched weight in Settings', async () => {
      const mockGetWeight = api.getWeight as ReturnType<typeof vi.fn>;
      mockGetWeight.mockResolvedValue(72.5);

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText('Weight: 72.5')).toBeInTheDocument();
      });
    });
  });

  describe('Active Session Display', () => {
    it('should display no active session message when no active session', async () => {
      const mockGetAllSessions = api.getAllSessions as ReturnType<typeof vi.fn>;
      mockGetAllSessions.mockResolvedValue([
        {
          ...mockSessions[1],
          isActive: false,
        },
      ]);

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText('No active hiking session')).toBeInTheDocument();
      });
    });

    it('should display active session from API when available', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByTestId('active-session')).toBeInTheDocument();
        expect(screen.getByText('Active Session: 1')).toBeInTheDocument();
      });
    });

    it('should prioritize WebSocket active session over API session', async () => {
      const wsActiveSession: HikingSession = {
        isActive: true,
        sessionId: 'ws-session',
        startTime: '2024-03-15T12:00:00Z',
        endTime: '',
        stepCount: 1000,
        burnedCalories: 100,
        distanceWalked: 800,
        bodyWeightKg: 75,
      };

      const mockUseWatchStatus = useWatchStatus as ReturnType<typeof vi.fn>;
      mockUseWatchStatus.mockReturnValue({
        isConnected: true,
        activeSession: wsActiveSession,
        isActiveSession: true,
      } as MockedUseWatchStatus);

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText('Active Session: ws-session')).toBeInTheDocument();
      });
    });
  });

  describe('Session List Display', () => {
    it('should display only past sessions (non-active)', async () => {
      render(<App />);

      await waitFor(() => {
        expect(screen.getByTestId('session-list')).toBeInTheDocument();
        expect(screen.getByTestId('session-2')).toBeInTheDocument();
        expect(screen.getByTestId('session-3')).toBeInTheDocument();
      });
    });

    it('should not show active session in SessionList', async () => {
      render(<App />);

      await waitFor(() => {
        const sessionList = screen.getByTestId('session-list');
        expect(sessionList.textContent).not.toContain('Active Session: 1');
      });
    });

    it('should pass correct sessions to SessionList', async () => {
      const pastSessions = [mockSessions[1], mockSessions[2]];
      const mockGetAllSessions = api.getAllSessions as ReturnType<typeof vi.fn>;
      mockGetAllSessions.mockResolvedValue(mockSessions);

      render(<App />);

      await waitFor(() => {
        pastSessions.forEach((session) => {
          expect(screen.getByTestId(`session-${session.sessionId}`)).toBeInTheDocument();
        });
      });
    });
  });

  describe('Session Deletion', () => {
    it('should delete session when onDelete is called', async () => {
      const user = userEvent.setup();
      render(<App />);

      await waitFor(() => {
        expect(screen.getByTestId('session-2')).toBeInTheDocument();
      });

      const deleteButton = screen.getAllByText('Delete')[0];
      await user.click(deleteButton);

      await waitFor(() => {
        const mockDeleteSession = api.deleteSession as ReturnType<typeof vi.fn>;
        expect(mockDeleteSession).toHaveBeenCalledWith('2');
      });
    });

    it('should remove deleted session from list after deletion', async () => {
      const user = userEvent.setup();
      const mockGetAllSessions = api.getAllSessions as ReturnType<typeof vi.fn>;
      mockGetAllSessions.mockResolvedValue(mockSessions);

      render(<App />);

      await waitFor(() => {
        expect(screen.getByTestId('session-2')).toBeInTheDocument();
      });

      const deleteButton = screen.getAllByText('Delete')[0];
      await user.click(deleteButton);

      await waitFor(() => {
        expect(screen.queryByTestId('session-2')).not.toBeInTheDocument();
      });
    });

    it('should handle deletion error gracefully', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const mockDeleteSession = api.deleteSession as ReturnType<typeof vi.fn>;
      mockDeleteSession.mockRejectedValue(new Error('Delete failed'));

      render(<App />);

      await waitFor(() => {
        expect(screen.getByTestId('session-2')).toBeInTheDocument();
      });

      const deleteButton = screen.getAllByText('Delete')[0];
      await user.click(deleteButton);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalled();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Weight Changes', () => {
    it('should update weight when Settings calls onWeightChange', async () => {
      const user = userEvent.setup();
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText('Weight: 75')).toBeInTheDocument();
      });

      const changeButton = screen.getByText('Change to 80');
      await user.click(changeButton);

      await waitFor(() => {
        const mockSetWeight = api.setWeight as ReturnType<typeof vi.fn>;
        expect(mockSetWeight).toHaveBeenCalledWith(80);
      });
    });

    it('should update local state after successful weight change', async () => {
      const user = userEvent.setup();
      const mockGetWeight = api.getWeight as ReturnType<typeof vi.fn>;
      mockGetWeight.mockResolvedValue(75);
      const mockSetWeight = api.setWeight as ReturnType<typeof vi.fn>;
      mockSetWeight.mockResolvedValue(undefined);

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText('Weight: 75')).toBeInTheDocument();
      });

      const changeButton = screen.getByText('Change to 80');
      await user.click(changeButton);

      await waitFor(() => {
        expect(screen.getByText('Weight: 80')).toBeInTheDocument();
      });
    });

    it('should handle weight change error gracefully', async () => {
      const user = userEvent.setup();
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const mockSetWeight = api.setWeight as ReturnType<typeof vi.fn>;
      mockSetWeight.mockRejectedValue(new Error('Set weight failed'));

      render(<App />);

      await waitFor(() => {
        expect(screen.getByText('Weight: 75')).toBeInTheDocument();
      });

      const changeButton = screen.getByText('Change to 80');
      await user.click(changeButton);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalled();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Session Refetching', () => {
    it('should refetch sessions when isActiveSession changes from true to false', async () => {
      const mockUseWatchStatus = useWatchStatus as ReturnType<typeof vi.fn>;
      const mockGetAllSessions = api.getAllSessions as ReturnType<typeof vi.fn>;

      const { rerender } = render(<App />);

      await waitFor(() => {
        expect(mockGetAllSessions).toHaveBeenCalled();
      });

      // Clear initial calls
      vi.clearAllMocks();
      mockGetAllSessions.mockResolvedValue(mockSessions);
      mockUseWatchStatus.mockReturnValue({
        isConnected: true,
        activeSession: mockSessions[0],
        isActiveSession: true,
      } as MockedUseWatchStatus);

      act(() => {
        rerender(<App />);
      });

      // Simulate end of active session
      mockUseWatchStatus.mockReturnValue({
        isConnected: true,
        activeSession: null,
        isActiveSession: false,
      } as MockedUseWatchStatus);

      act(() => {
        rerender(<App />);
      });

      await waitFor(() => {
        expect(mockGetAllSessions).toHaveBeenCalled();
      });
    });

    it('should not refetch when isActiveSession is true', async () => {
      const mockUseWatchStatus = useWatchStatus as ReturnType<typeof vi.fn>;
      const mockGetAllSessions = api.getAllSessions as ReturnType<typeof vi.fn>;

      const { rerender } = render(<App />);

      await waitFor(() => {
        expect(mockGetAllSessions).toHaveBeenCalled();
      });

      vi.clearAllMocks();
      mockGetAllSessions.mockResolvedValue(mockSessions);
      mockUseWatchStatus.mockReturnValue({
        isConnected: true,
        activeSession: mockSessions[0],
        isActiveSession: true,
      } as MockedUseWatchStatus);

      act(() => {
        rerender(<App />);
      });

      expect(mockGetAllSessions).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should handle getAllSessions error on mount', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const mockGetAllSessions = api.getAllSessions as ReturnType<typeof vi.fn>;
      mockGetAllSessions.mockRejectedValue(new Error('Fetch failed'));

      render(<App />);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalled();
      });

      consoleErrorSpy.mockRestore();
    });

    it('should handle getWeight error on mount', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const mockGetWeight = api.getWeight as ReturnType<typeof vi.fn>;
      mockGetWeight.mockRejectedValue(new Error('Weight fetch failed'));

      render(<App />);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalled();
      });

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Data Flow Integration', () => {
    it('should handle complete add/update/delete cycle', async () => {
      const user = userEvent.setup();

      // Initial render
      render(<App />);

      await waitFor(() => {
        expect(screen.getByTestId('session-2')).toBeInTheDocument();
      });

      // Delete a session
      const deleteButton = screen.getAllByText('Delete')[0];
      await user.click(deleteButton);

      await waitFor(() => {
        const mockDeleteSession = api.deleteSession as ReturnType<typeof vi.fn>;
        expect(mockDeleteSession).toHaveBeenCalled();
      });

      // Verify session removed
      await waitFor(() => {
        expect(screen.queryByTestId('session-2')).not.toBeInTheDocument();
      });
    });

    it('should handle multiple operations in sequence', async () => {
      const user = userEvent.setup();
      render(<App />);

      await waitFor(() => {
        expect(screen.getByText('Weight: 75')).toBeInTheDocument();
      });

      // Change weight
      const changeButton = screen.getByText('Change to 80');
      await user.click(changeButton);

      await waitFor(() => {
        expect(screen.getByText('Weight: 80')).toBeInTheDocument();
      });

      // Verify all components still render
      expect(screen.getByTestId('active-session')).toBeInTheDocument();
      expect(screen.getByTestId('session-list')).toBeInTheDocument();
    });
  });
});
