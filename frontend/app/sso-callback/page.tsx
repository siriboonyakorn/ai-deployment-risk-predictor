import { AuthenticateWithRedirectCallback } from "@clerk/nextjs";

/**
 * Handles the OAuth redirect from Clerk after the user authenticates
 * with a social provider (GitHub, Google, etc.).
 * Clerk completes the session handshake and then redirects to
 * NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL (/dashboard).
 */
export default function SSOCallbackPage() {
  return <AuthenticateWithRedirectCallback />;
}
