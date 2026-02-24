"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated, initiateGitHubLogin } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();

  // Already logged in → go straight to dashboard
  useEffect(() => {
    if (isAuthenticated()) {
      router.replace("/dashboard");
    }
  }, [router]);

  return (
    <div
      className="flex items-center justify-center min-h-screen"
      style={{ background: "var(--background)" }}
    >
      <div
        className="card p-10 flex flex-col items-center gap-6 w-full max-w-sm"
        style={{ border: "1px solid var(--border)" }}
      >
        {/* Logo / title */}
        <div className="flex flex-col items-center gap-2 text-center">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center mb-1"
            style={{ background: "rgba(47,129,247,0.15)", border: "1px solid rgba(47,129,247,0.3)" }}
          >
            {/* Shield icon */}
            <svg width="24" height="24" viewBox="0 0 16 16" fill="#2f81f7">
              <path d="M8.533.133a1.75 1.75 0 0 0-1.066 0l-5.25 1.68A1.75 1.75 0 0 0 1 3.48V8c0 3.572 2.111 6.26 5.49 7.773.374.165.644.165 1.021 0C10.888 14.26 13 11.573 13 8V3.48a1.75 1.75 0 0 0-1.217-1.667Zm-.61 1.429a.25.25 0 0 1 .153 0l5.25 1.68a.25.25 0 0 1 .174.238V8c0 2.996-1.768 5.257-4.753 6.607a.344.344 0 0 1-.146 0C5.268 13.257 3.5 10.996 3.5 8V3.48a.25.25 0 0 1 .174-.238Z" />
            </svg>
          </div>
          <h1 className="text-xl font-bold" style={{ color: "var(--foreground)" }}>
            AI Deployment Risk
          </h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Predict deployment risk before your code reaches production.
          </p>
        </div>

        {/* Divider */}
        <div className="w-full h-px" style={{ background: "var(--border-subtle)" }} />

        {/* GitHub login button */}
        <button
          onClick={initiateGitHubLogin}
          className="w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-md text-sm font-semibold transition-colors cursor-pointer"
          style={{
            background: "var(--surface-raised)",
            color: "var(--foreground)",
            border: "1px solid var(--border)",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--accent)";
            (e.currentTarget as HTMLButtonElement).style.background = "rgba(47,129,247,0.08)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border)";
            (e.currentTarget as HTMLButtonElement).style.background = "var(--surface-raised)";
          }}
        >
          {/* GitHub mark */}
          <svg width="18" height="18" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
          </svg>
          Sign in with GitHub
        </button>

        <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>
          Only repository metadata is accessed. No code is stored.
        </p>
      </div>
    </div>
  );
}
