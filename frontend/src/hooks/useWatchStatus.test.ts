import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWatchStatus } from './useWatchStatus';

interface MockWebSocket {
  url: string;
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
  onclose: ((event: CloseEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  close: ReturnType<typeof vi.fn>;
  send: ReturnType<typeof vi.fn>;
}

describe('useWatchStatus', () => {
  let WebSocketMockFn: ReturnType<typeof vi.fn>;
  let wsInstances: MockWebSocket[] = [];

  // Helper to get first instance with proper typing
  function getFirstWsInstance(): MockWebSocket {
    const instance = wsInstances[0];
    if (!instance) {
      throw new Error('No WebSocket instance created');
    }
    return instance;
  }

  beforeEach(() => {
    vi.useFakeTimers();
    wsInstances = [];

    // Create a mock WebSocket class
    WebSocketMockFn = vi.fn(function (this: MockWebSocket, url: string) {
      this.url = url;
      this.onopen = null;
      this.onmessage = null;
      this.onclose = null;
      this.onerror = null;
      this.close = vi.fn();
      this.send = vi.fn();
      wsInstances.push(this);
    });

    vi.stubGlobal('WebSocket', WebSocketMockFn);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    wsInstances = [];
  });

  it('should initialize with disconnected state', () => {
    const { result } = renderHook(() => useWatchStatus('ws://localhost:8080'));

    expect(result.current.isConnected).toBe(false);
    expect(result.current.activeSession).toBe(null);
    expect(result.current.isActiveSession).toBe(false);
  });

  it('should create WebSocket with correct URL', () => {
    const url = 'ws://example.com:8080';
    renderHook(() => useWatchStatus(url));

    expect(WebSocketMockFn).toHaveBeenCalledWith(url);
    expect(wsInstances).toHaveLength(1);
    expect(getFirstWsInstance().url).toBe(url);
  });

  it('should close WebSocket on error', () => {
    renderHook(() => useWatchStatus('ws://localhost:8080'));

    const wsInstance = getFirstWsInstance();

    act(() => {
      wsInstance.onerror!(new Event('error'));
    });

    expect(wsInstance.close).toHaveBeenCalled();
  });

  it('should cleanup on unmount', () => {
    const { unmount } = renderHook(() => useWatchStatus('ws://localhost:8080'));

    const wsInstance = getFirstWsInstance();

    unmount();

    expect(wsInstance.close).toHaveBeenCalled();
  });

  it('should attempt reconnection after close', () => {
    renderHook(() => useWatchStatus('ws://localhost:8080'));

    const wsInstance = getFirstWsInstance();

    act(() => {
      wsInstance.onclose!(new CloseEvent('close'));
    });

    // Should have set a timeout to reconnect
    expect(vi.getTimerCount()).toBeGreaterThan(0);

    // Advance timers by 3 seconds
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    // Should have created a new WebSocket
    expect(wsInstances).toHaveLength(2);
  });

  it('should recreate WebSocket when URL changes', () => {
    const { rerender } = renderHook(
      ({ url }: { url: string }) => useWatchStatus(url),
      { initialProps: { url: 'ws://localhost:8080' } }
    );

    const firstWs = getFirstWsInstance();

    act(() => {
      rerender({ url: 'ws://localhost:9090' });
    });

    expect(firstWs.close).toHaveBeenCalled();
    expect(WebSocketMockFn).toHaveBeenCalledWith('ws://localhost:9090');
  });

  it('should handle malformed JSON gracefully', () => {
    renderHook(() => useWatchStatus('ws://localhost:8080'));

    const wsInstance = getFirstWsInstance();

    // Should not throw
    expect(() => {
      act(() => {
        wsInstance.onmessage!(new MessageEvent('message', { data: 'not valid json' }));
      });
    }).not.toThrow();
  });

  it('should ignore messages without type field', () => {
    renderHook(() => useWatchStatus('ws://localhost:8080'));

    const wsInstance = getFirstWsInstance();

    // Should not throw
    expect(() => {
      act(() => {
        wsInstance.onmessage!(new MessageEvent('message', {
          data: JSON.stringify({ isActive: true, connected: true })
        }));
      });
    }).not.toThrow();
  });

  it('should parse valid session_update messages', () => {
    renderHook(() => useWatchStatus('ws://localhost:8080'));

    const wsInstance = getFirstWsInstance();

    const sessionData = {
      type: 'session_update',
      isActive: true,
      connected: true,
      sessionId: '123',
      startTime: '2024-01-01T10:00:00Z',
      endTime: '',
      stepCount: 500,
      burnedCalories: 100,
      distanceWalked: 1000,
      bodyWeightKg: 70,
    };

    // Should not throw when processing valid message
    expect(() => {
      act(() => {
        wsInstance.onmessage!(new MessageEvent('message', {
          data: JSON.stringify(sessionData)
        }));
      });
    }).not.toThrow();
  });
});
