import { useState } from "react";
import type { HikingSession } from "../types";
import { formatDate, formatDateTime } from "../format";

interface Props {
  sessions: HikingSession[];
  onDelete: (sessionId: string) => void;
}

export function SessionList({ sessions, onDelete }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (sessions.length === 0) {
    return (
      <section className="session-list">
        <h2>Past Sessions</h2>
        <p className="empty-message">No past sessions yet.</p>
      </section>
    );
  }

  return (
    <section className="session-list">
      <h2>Past Sessions</h2>
      {sessions.sort((a, b) => new Date(b.endTime) < new Date(a.endTime) ? -1 : 1).map((session) => {
        const isExpanded = expandedId === session.sessionId;
        return (
          <div key={session.sessionId} className="session-card">
            <div
              className="session-header"
              onClick={() =>
                setExpandedId(isExpanded ? null : session.sessionId)
              }
            >
              <span>
                {formatDate(session.startTime)} —{" "}
                {(session.distanceWalked / 1000).toFixed(2)} km
              </span>
              <span className="expand-icon">{isExpanded ? "▲" : "▼"}</span>
            </div>

            {isExpanded && (
              <div className="session-details">
                <div className="session-stats">
                  <div className="stat">
                    <span className="stat-label">Start</span>
                    <span className="stat-value">
                      {formatDateTime(session.startTime)}
                    </span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">End</span>
                    <span className="stat-value">
                      {formatDateTime(session.endTime)}
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
                  <div className="stat">
                    <span className="stat-label">Body Weight</span>
                    <span className="stat-value">
                      {session.bodyWeightKg.toFixed(1)} kg
                    </span>
                  </div>
                </div>
                <button
                  className="delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(session.sessionId);
                  }}
                >
                  Delete Session
                </button>
              </div>
            )}
          </div>
        );
      })}
    </section>
  );
}
