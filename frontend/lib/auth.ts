/**
 * Client-side auth utilities — powered by Clerk.
 *
 * Clerk manages the session lifecycle (sign-in, sign-up, token refresh).
 * We expose an async getToken() that returns the current Clerk session JWT
 * so lib/api.ts can attach it to every backend request without coupling to
 * React hooks.
 *
 * registerClerkTokenGetter() is called once by <ClerkTokenSync> (mounted in
 * the root layout) to wire Clerk's getToken into this module.
 */

type ClerkTokenGetter = () => Promise<string | null>;

let _clerkGetToken: ClerkTokenGetter | null = null;

/**
 * Called by <ClerkTokenSync> once the ClerkProvider is mounted.
 * Registers Clerk's hook-based getToken() for use outside React components.
 */
export function registerClerkTokenGetter(fn: ClerkTokenGetter): void {
  _clerkGetToken = fn;
}

/**
 * Returns the current Clerk session JWT, or null when not signed in.
 * Used by lib/api.ts to attach Authorization headers.
 */
export async function getToken(): Promise<string | null> {
  if (_clerkGetToken) return _clerkGetToken();
  return null;
}
