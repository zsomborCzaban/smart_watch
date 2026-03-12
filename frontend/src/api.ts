import type { HikingSession } from "./types";

const BASE_URL = "/api";

export async function getActiveSession(): Promise<HikingSession | null> {
  const res = await fetch(`${BASE_URL}/activeSession`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch active session");
  return res.json();
}

export async function getAllSessions(): Promise<HikingSession[]> {
  const res = await fetch(`${BASE_URL}/allSessions`);
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return res.json();
}

export async function deleteSession(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/session/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete session");
}

export async function getWeight(): Promise<number> {
  const res = await fetch(`${BASE_URL}/weight`);
  if (!res.ok) throw new Error("Failed to fetch weight");
  const data = await res.json();
  return data.weight;
}

export async function setWeight(weight: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/setWeight`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ weight }),
  });
  if (!res.ok) throw new Error("Failed to set weight");
}
