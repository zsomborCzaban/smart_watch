import { formatDateTime } from "../format";
import type { HikingSession } from "../types";

interface Props {
  session: HikingSession;
}

export function ActiveSession({ session }: Props) {
  return (
    <section className="active-session">
      <h2>Active Session</h2>
      <div className="session-card active">
        <div className="session-stats">
          <div className="stat">
            <span className="stat-label">Started</span>
            <span className="stat-value">
              {formatDateTime(session.startTime)}
            </span>
          </div>
          <div className="stat">
            <span className="stat-label">Steps</span>
            <span className="stat-value">
              {session.stepCount}
            </span>
          </div>
          <div className="stat">
            <span className="stat-label">Calories</span>
            <span className="stat-value">
              {session.burnedCalories.toFixed(1)} kcal
            </span>
          </div>
          <div className="stat">
            <span className="stat-label">Distance</span>
            <span className="stat-value">
              {(session.distanceWalked / 1000).toFixed(2)} km
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
