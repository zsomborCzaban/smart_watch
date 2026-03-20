import { describe, it, expect } from 'vitest';
import { formatDate, formatDateTime, parseIsoInterval } from './format';

describe('format.ts', () => {
  describe('formatDate', () => {
    it('should format ISO date string to short format', () => {
      const result = formatDate('2024-03-15T14:30:00Z');
      expect(result).toMatch(/Mar|15|Fri/);
    });

    it('should handle different dates correctly', () => {
      const result = formatDate('2024-01-01T00:00:00Z');
      expect(result).toContain('Jan');
    });
  });

  describe('formatDateTime', () => {
    it('should format ISO datetime string correctly', () => {
      const result = formatDateTime('2024-03-15T14:30:00Z');
      expect(result).toMatch(/\d{4}|Mar|15/);
    });

    it('should return "—" for empty/falsy input', () => {
      expect(formatDateTime('')).toBe('—');
      expect(formatDateTime(null as unknown as string)).toBe('—');
      expect(formatDateTime(undefined as unknown as string)).toBe('—');
    });

    it('should handle various ISO datetime formats', () => {
      const result = formatDateTime('2024-12-25T23:59:00Z');
      expect(result).toBeTruthy();
      expect(result).not.toBe('—');
    });
  });

  describe('parseIsoInterval', () => {
    it('should parse ISO 8601 duration with all components', () => {
      const result = parseIsoInterval('PT2H30M45S');
      expect(result).toEqual({ hours: 2, minutes: 30, seconds: 45 });
    });

    it('should parse ISO 8601 duration with only hours', () => {
      const result = parseIsoInterval('PT5H');
      expect(result).toEqual({ hours: 5, minutes: 0, seconds: 0 });
    });

    it('should parse ISO 8601 duration with only minutes', () => {
      const result = parseIsoInterval('PT45M');
      expect(result).toEqual({ hours: 0, minutes: 45, seconds: 0 });
    });

    it('should parse ISO 8601 duration with only seconds', () => {
      const result = parseIsoInterval('PT30S');
      expect(result).toEqual({ hours: 0, minutes: 0, seconds: 30 });
    });

    it('should parse ISO 8601 duration with hours and minutes', () => {
      const result = parseIsoInterval('PT1H30M');
      expect(result).toEqual({ hours: 1, minutes: 30, seconds: 0 });
    });

    it('should parse ISO 8601 duration with minutes and seconds', () => {
      const result = parseIsoInterval('PT15M20S');
      expect(result).toEqual({ hours: 0, minutes: 15, seconds: 20 });
    });

    it('should return zero values for invalid input', () => {
      const result = parseIsoInterval('invalid');
      expect(result).toEqual({ hours: 0, minutes: 0, seconds: 0 });
    });

    it('should return zero values for undefined input', () => {
      const result = parseIsoInterval(undefined);
      expect(result).toEqual({ hours: 0, minutes: 0, seconds: 0 });
    });

    it('should return zero values for empty string', () => {
      const result = parseIsoInterval('');
      expect(result).toEqual({ hours: 0, minutes: 0, seconds: 0 });
    });

    it('should handle large time values', () => {
      const result = parseIsoInterval('PT100H999M999S');
      expect(result).toEqual({ hours: 100, minutes: 999, seconds: 999 });
    });
  });
});
