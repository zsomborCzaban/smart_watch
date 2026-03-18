import { formatDateTime, parseIsoInterval } from "../format";
import type { HikingSession } from "../types";

interface Props {
  session: HikingSession;
}

export function ActiveSession({ session }: Props) {
  const elapsedTime = parseIsoInterval(session.hikeSessionTime);
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
            <span className="stat-value">{session.stepCount}</span>
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
          <div className="stat">
            <span className="stat-label">Elapsed time:</span>
            <span className="stat-value">
              {elapsedTime.hours.toString().padStart(2, "0")}:{elapsedTime.minutes.toString().padStart(2, "0")}:{elapsedTime.seconds.toString().padStart(2, "0")}
            </span>
          </div>
          <div className="stat">
            <span className="stat-label">Status:</span>
            <span className="stat-value">
              {session.isPaused ? "Paused" : "Active"}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
