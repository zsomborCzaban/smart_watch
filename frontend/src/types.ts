export interface HikingSession {
  isActive: boolean;
  sessionId: string;
  startTime: string;
  endTime: string;
  stepCount: number;
  burnedCalories: number;
  distanceWalked: number;
}
