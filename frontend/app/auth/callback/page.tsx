"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";

/**
 * Legacy callback route kept for backward compatibility.
 * Clerk handles OAuth callbacks at /sso-callback.
 * Any request here is redirected to the appropriate destination.
 */
export default function AuthCallbackPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();

  useEffect(() => {
    if (!isLoaded) return;
    router.replace(isSignedIn ? "/dashboard" : "/login");
  }, [isLoaded, isSignedIn, router]);

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
          Redirecting...
        </p>
      </div>
    </div>
  );
}

