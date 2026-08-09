const TOKEN_KEY = "airport360_token";

// VITE_API_URL points the built app at the deployed backend (e.g. Render).
// In local dev it stays empty and the Vite proxy forwards /v1 to localhost:8000.
const API_BASE = (import.meta.env.VITE_API_URL as string | undefined ?? "").replace(/\/+$/, "");

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: { id: number; name: string };
  site_id: number;
  active: boolean;
};

export type TokenResponse = { access_token: string; user: User };

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${API_BASE}/v1${path}`, { ...options, headers });
  if (resp.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`;
    try {
      const body = await resp.json();
      detail = Array.isArray(body.detail)
        ? body.detail.map((d: { msg: string }) => d.msg).join("; ")
        : body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}
