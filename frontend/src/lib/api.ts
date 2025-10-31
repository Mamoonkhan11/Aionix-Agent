const API_BASE = "http://localhost:4000/api";

export async function getUsers() {
  const res = await fetch(`${API_BASE}/users`);
  return res.json();
}

export async function getTasks() {
  const res = await fetch(`${API_BASE}/tasks`);
  return res.json();
}