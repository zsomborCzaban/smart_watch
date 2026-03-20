import { useEffect, useState } from "react";
import { ActiveSession } from "./components/ActiveSession";
import { SessionList } from "./components/SessionList";
import { Settings } from "./components/Settings";
import { useWatchStatus } from "./hooks/useWatchStatus";
import type { HikingSession } from "./types";
import * as api from "./api";
import "./App.css";

function App() {
  const [sessions, setSessions] = useState<HikingSession[]>([]);
  const [weight, setWeight] = useState(0);
  const {
    isConnected: isWatchConnected,
    activeSession: wshActiveSession,
    isActiveSession,
  } = useWatchStatus(`ws://${window.location.host}/api/ws`);

  useEffect(() => {
    api.getAllSessions().then(setSessions).catch(console.error);
    api.getWeight().then(setWeight).catch(console.error);
  }, []);

  useEffect(() => {
    if (!isActiveSession) {
      api.getAllSessions().then(setSessions).catch(console.error);
    }
  }, [isActiveSession]);

  const activeSession = sessions.find((s) => s.isActive) ?? null;
  const activeDisplayedSession = wshActiveSession ?? activeSession;
  const pastSessions = sessions.filter((s) => !s.isActive);

  const handleDelete = async (sessionId: string) => {
    try {
      await api.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.sessionId !== sessionId));
    } catch (e) {
      console.error(e);
    }
  };

  const handleWeightChange = async (newWeight: number) => {
    try {
      await api.setWeight(newWeight);
      setWeight(newWeight);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="app">
      <div className="app-header">
        <h1>Hiking Tracker</h1>
        <div className="watch-status">
          <span
            className={`status-dot ${isWatchConnected ? "connected" : "disconnected"}`}
          />
          <span
            className={`status-text ${isWatchConnected ? "connected" : "disconnected"}`}
          >
            {isWatchConnected ? "Watch Connected" : "Watch Disconnected"}
          </span>
        </div>
      </div>

      {activeDisplayedSession ? (
        <ActiveSession session={activeDisplayedSession} />
      ) : (
        <div className="no-active-card">
          <p>No active hiking session</p>
        </div>
      )}

      <Settings weight={weight} onWeightChange={handleWeightChange} />

      <SessionList sessions={pastSessions} onDelete={handleDelete} />
    </div>
  );
}

export default App;
