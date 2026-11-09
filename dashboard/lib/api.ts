export const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"
).replace(/\/$/, "");

export const TOKEN_KEY = "store_admin_token";

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  if (!window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  form?: FormData;
  auth?: boolean;
  signal?: AbortSignal;
};

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, form, auth = true, signal } = options;
  const headers: Record<string, string> = {};
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  let payload: BodyInit | undefined;
  if (form) {
    payload = form;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: payload,
    signal,
    cache: "no-store",
  });

  if (response.status === 401 && auth) {
    setToken(null);
    redirectToLogin();
  }

  if (!response.ok) {
    let detail = response.statusText || "Request failed";
    let code: string | undefined;
    try {
      const data = await response.json();
      if (typeof data?.detail === "string") detail = data.detail;
      else if (Array.isArray(data?.detail)) {
        detail = data.detail
          .map((item: { msg?: string }) => item?.msg || "")
          .filter(Boolean)
          .join(", ");
      }
      code = data?.code;
    } catch {
      // keep the status text
    }
    throw new ApiError(detail, response.status, code);
  }

  if (response.status === 204) return undefined as T;
  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function downloadFile(path: string, filename: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, { headers: authHeaders() });
  if (!response.ok) {
    throw new ApiError("Download failed", response.status);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function getApiPublicUrl(): string {
  return API_BASE;
}
