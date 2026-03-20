import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from './api';

describe('api.ts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getAllSessions', () => {
    it('should fetch all sessions successfully', async () => {
      const mockSessions = [
        {
          isActive: false,
          sessionId: '1',
          startTime: '2024-01-01T10:00:00Z',
          endTime: '2024-01-01T11:00:00Z',
          stepCount: 1000,
          burnedCalories: 200,
          distanceWalked: 800,
          bodyWeightKg: 70,
        },
      ];

      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockSessions),
          } as Response)
        )
      );

      const result = await api.getAllSessions();
      expect(result).toEqual(mockSessions);
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/allSessions');
    });

    it('should throw error when fetch fails', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: false,
          } as Response)
        )
      );

      await expect(api.getAllSessions()).rejects.toThrow('Failed to fetch sessions');
    });

    it('should throw error on network error', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() => Promise.reject(new Error('Network error')))
      );

      await expect(api.getAllSessions()).rejects.toThrow('Network error');
    });
  });

  describe('deleteSession', () => {
    it('should delete session successfully', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: true,
          } as Response)
        )
      );

      await api.deleteSession('session-123');
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/session/session-123', {
        method: 'DELETE',
      });
    });

    it('should encode special characters in session ID', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: true,
          } as Response)
        )
      );

      await api.deleteSession('session/with spaces');
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/session/session%2Fwith%20spaces', {
        method: 'DELETE',
      });
    });

    it('should throw error when delete fails', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: false,
          } as Response)
        )
      );

      await expect(api.deleteSession('session-123')).rejects.toThrow('Failed to delete session');
    });
  });

  describe('getWeight', () => {
    it('should fetch weight successfully', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ weight: 75 }),
          } as Response)
        )
      );

      const result = await api.getWeight();
      expect(result).toBe(75);
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/weight');
    });

    it('should throw error when fetch fails', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: false,
          } as Response)
        )
      );

      await expect(api.getWeight()).rejects.toThrow('Failed to fetch weight');
    });

    it('should handle decimal weights', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ weight: 75.5 }),
          } as Response)
        )
      );

      const result = await api.getWeight();
      expect(result).toBe(75.5);
    });
  });

  describe('setWeight', () => {
    it('should set weight successfully', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: true,
          } as Response)
        )
      );

      await api.setWeight(80);
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/setWeight', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weight: 80 }),
      });
    });

    it('should handle decimal weights', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: true,
          } as Response)
        )
      );

      await api.setWeight(82.5);
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/setWeight', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weight: 82.5 }),
      });
    });

    it('should throw error when set fails', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn(() =>
          Promise.resolve({
            ok: false,
          } as Response)
        )
      );

      await expect(api.setWeight(80)).rejects.toThrow('Failed to set weight');
    });
  });
});
