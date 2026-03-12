import { useEffect, useState } from "react";
import { ActiveSession } from "./components/ActiveSession";
import { SessionList } from "./components/SessionList";
import { Settings } from "./components/Settings";
import type { HikingSession } from "./types";
import * as api from "./api";
import "./App.css";

function App() {
  const [sessions, setSessions] = useState<HikingSession[]>([]);
  const [weight, setWeight] = useState(75);
  const [isWatchConnected] = useState(false);

  useEffect(() => {
    api.getAllSessions().then(setSessions).catch(console.error);
    api.getWeight().then(setWeight).catch(console.error);
  }, []);

  const activeSession = sessions.find((s) => s.isActive) ?? null;
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
        onWeightChange={handleWeightChange}
      />

      <SessionList sessions={pastSessions} onDelete={handleDelete} />
    </div>
  );
}

export default App;
