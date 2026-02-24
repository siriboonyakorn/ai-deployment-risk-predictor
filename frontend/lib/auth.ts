/**
 * Client-side auth utilities.
 * JWT is stored in localStorage under AUTH_TOKEN_KEY.
 */

const AUTH_TOKEN_KEY = "auth_token";

export interface AuthUser {
  id: number;
  username: string;
  email: string | null;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  const token = getToken();
  if (!token) return false;

  // Peek at the JWT expiry without a library — decode the payload (base64)
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return false;
    const payload = JSON.parse(atob(parts[1]));
    if (!payload.exp) return true; // no expiry claim → treat as valid
    return payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Login / logout
// ---------------------------------------------------------------------------

export function initiateGitHubLogin(): void {
  // Redirect browser to backend which then redirects to GitHub
  window.location.href = "/api/v1/auth/github/login/redirect";
}

export function logout(): void {
  clearToken();
  window.location.href = "/login";
}
