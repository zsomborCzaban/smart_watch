import { useState } from "react";
import { ActiveSession } from "./components/ActiveSession";
import { SessionList } from "./components/SessionList";
import { Settings } from "./components/Settings";
import type { HikingSession } from "./types";
import "./App.css";

const MOCK_SESSIONS: HikingSession[] = [
  {
    isActive: true,
    sessionId: "s1",
    startTime: new Date(Date.now() - 3600_000).toISOString(),
    endTime: "",
    stepCount: 4230,
    burnedCalories: 285.4,
    distanceWalked: 3120,
  },
  {
    isActive: false,
    sessionId: "s2",
    startTime: "2026-03-11T08:00:00Z",
    endTime: "2026-03-11T11:30:00Z",
    stepCount: 12450,
    burnedCalories: 820.3,
    distanceWalked: 9200,
  },
  {
    isActive: false,
    sessionId: "s3",
    startTime: "2026-03-09T14:00:00Z",
    endTime: "2026-03-09T16:15:00Z",
    stepCount: 7800,
    burnedCalories: 510.0,
    distanceWalked: 5700,
  },
];

function App() {
  const [sessions, setSessions] = useState<HikingSession[]>(MOCK_SESSIONS);
  const [weight, setWeight] = useState(75);
  const [isWatchConnected] = useState(true);

  const activeSession = sessions.find((s) => s.isActive) ?? null;
  const pastSessions = sessions.filter((s) => !s.isActive);

  const handleDelete = (sessionId: string) => {
    setSessions((prev) => prev.filter((s) => s.sessionId !== sessionId));
  };

  return (
    <div className="app">
      <div className="app-header">
        <h1>Hiking Tracker</h1>
        <div className="watch-status">
          <span className={`status-dot ${isWatchConnected ? "connected" : "disconnected"}`} />
          <span className={`status-text ${isWatchConnected ? "connected" : "disconnected"}`}>
            {isWatchConnected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      {activeSession ? (
        <ActiveSession session={activeSession} />
      ) : (
        <div className="no-active-card">
          <p>No active hiking session</p>
        </div>
      )}

      <Settings
        weight={weight}
        onWeightChange={setWeight}
      />

      <SessionList sessions={pastSessions} onDelete={handleDelete} />
    </div>
  );
}

export default App;
