const TOKEN_KEY = "airport360_token";
const SITE_KEY = "airport360_active_site";

// VITE_API_URL points the built app at the deployed backend (e.g. Render).
// In local dev it stays empty and the Vite proxy forwards /v1 to localhost:8000.
const API_BASE = (import.meta.env.VITE_API_URL as string | undefined ?? "").replace(/\/+$/, "");

export { API_BASE };

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

export function getActiveSite(): number | null {
  const v = localStorage.getItem(SITE_KEY);
  return v ? Number(v) : null;
}

export function setActiveSite(siteId: number): void {
  localStorage.setItem(SITE_KEY, String(siteId));
}

export function clearActiveSite(): void {
  localStorage.removeItem(SITE_KEY);
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const site = getActiveSite();
  if (site) headers["X-Site-Id"] = String(site);
  return headers;
}

/** Multipart upload (e.g. video analysis). Does NOT set Content-Type so the browser adds the boundary. */
export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const headers = authHeaders();

  const resp = await fetch(`${API_BASE}/v1${path}`, { method: "POST", headers, body: form });
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

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = authHeaders(options.headers as Record<string, string> | undefined);
  headers["Content-Type"] = "application/json";

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
