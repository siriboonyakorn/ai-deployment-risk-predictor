"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setToken, isAuthenticated } from "@/lib/auth";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const token = searchParams.get("token");

  // Derive error state at render time — no setState needed inside the effect
  const errorMessage = !token
    ? "No token received from GitHub. Please try logging in again."
    : token && !isAuthenticated()
    ? "The received token appears to be invalid or expired."
    : null;

  // Store the token before first render triggers the effect
  if (token) {
    setToken(token);
  }

  useEffect(() => {
    if (!token || errorMessage) return;
    router.replace("/dashboard");
  }, [token, errorMessage, router]);

  if (errorMessage) {
    return (
      <div
        className="flex items-center justify-center min-h-screen"
        style={{ background: "var(--background)" }}
      >
        <div className="card-elevated p-8 flex flex-col items-center gap-4 max-w-sm w-full text-center">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)" }}
          >
            <svg width="18" height="18" viewBox="0 0 16 16" fill="#ef4444">
              <path d="M4.47.22A.749.749 0 0 1 5 0h6c.199 0 .389.079.53.22l4.25 4.25c.141.14.22.331.22.53v6a.749.749 0 0 1-.22.53l-4.25 4.25A.749.749 0 0 1 11 16H5a.749.749 0 0 1-.53-.22L.22 11.53A.749.749 0 0 1 0 11V5c0-.199.079-.389.22-.53Zm.84 1.28L1.5 5.31v5.38l3.81 3.81h5.38l3.81-3.81V5.31L10.69 1.5ZM8 4a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z" />
            </svg>
          </div>
          <div>
            <h2 className="font-semibold mb-1" style={{ color: "var(--foreground)" }}>
              Authentication failed
            </h2>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              {errorMessage}
            </p>
          </div>
          <a
            href="/login"
            className="px-4 py-2 rounded-md text-sm font-semibold transition-colors"
            style={{ background: "var(--accent)", color: "#fff" }}
          >
            Back to Login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex items-center justify-center min-h-screen"
      style={{ background: "var(--background)" }}
    >
      <div className="flex flex-col items-center gap-3">
        <div
          className="w-8 h-8 rounded-full border-2 animate-spin"
          style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
        />
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Signing you in…
        </p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div
          className="flex items-center justify-center min-h-screen"
          style={{ background: "var(--background)" }}
        >
          <div
            className="w-8 h-8 rounded-full border-2 animate-spin"
            style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
          />
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
