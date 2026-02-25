"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth, useSignIn } from "@clerk/nextjs";

// ---------------------------------------------------------------------------
// Risk preview widget — animates through fake commits
// ---------------------------------------------------------------------------

const PREVIEW_COMMITS = [
  {
    sha: "a1b2c3d",
    message: "hotfix: patch critical auth bypass",
    risk: 87,
    level: "HIGH" as const,
  },
  {
    sha: "e4f5a6b",
    message: "refactor: extract payment service",
    risk: 42,
    level: "MEDIUM" as const,
  },
  {
    sha: "7c8d9e0",
    message: "docs: update README examples",
    risk: 8,
    level: "LOW" as const,
  },
  {
    sha: "f1e2d3c",
    message: "feat: add user dashboard metrics",
    risk: 34,
    level: "MEDIUM" as const,
  },
];

function RiskPreviewWidget() {
  const [activeIdx, setActiveIdx] = useState(0);

  useEffect(() => {
    const id = setInterval(
      () => setActiveIdx((i) => (i + 1) % PREVIEW_COMMITS.length),
      2400
    );
    return () => clearInterval(id);
  }, []);

  const active = PREVIEW_COMMITS[activeIdx];
  const color =
    active.level === "HIGH"
      ? "#ef4444"
      : active.level === "MEDIUM"
      ? "#f59e0b"
      : "#22c55e";

  return (
    <div
      className="rounded-2xl p-5 w-full max-w-sm mx-auto shadow-2xl"
      style={{
        background: "rgba(15,20,30,0.95)",
        border: "1px solid rgba(255,255,255,0.08)",
        backdropFilter: "blur(12px)",
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div
          className="w-2 h-2 rounded-full"
          style={{ background: "var(--accent)" }}
        />
        <span
          className="text-xs font-semibold tracking-wider uppercase"
          style={{ color: "var(--text-muted)" }}
        >
          Live Risk Analysis
        </span>
      </div>

      {/* Commit rows */}
      <div className="space-y-2 mb-4">
        {PREVIEW_COMMITS.map((c, i) => {
          const c2 =
            c.level === "HIGH"
              ? "#ef4444"
              : c.level === "MEDIUM"
              ? "#f59e0b"
              : "#22c55e";
          const isActive = i === activeIdx;
          return (
            <div
              key={c.sha}
              className="flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-300"
              style={{
                background: isActive
                  ? "rgba(59,130,246,0.1)"
                  : "rgba(255,255,255,0.03)",
                border: isActive
                  ? "1px solid rgba(59,130,246,0.3)"
                  : "1px solid transparent",
                opacity: isActive ? 1 : 0.5,
              }}
            >
              <div
                className="font-mono text-xs flex-shrink-0"
                style={{ color: "rgba(255,255,255,0.4)" }}
              >
                {c.sha}
              </div>
              <div
                className="flex-1 text-xs truncate"
                style={{ color: isActive ? "#e2e8f0" : "rgba(255,255,255,0.5)" }}
              >
                {c.message}
              </div>
              <div
                className="text-xs font-bold flex-shrink-0"
                style={{ color: c2 }}
              >
                {c.risk}
              </div>
            </div>
          );
        })}
      </div>

      {/* Active commit detail */}
      <div
        className="rounded-xl p-4 space-y-2"
        style={{ background: "rgba(255,255,255,0.04)" }}
      >
        <div className="flex items-center justify-between">
          <span
            className="text-xs"
            style={{ color: "rgba(255,255,255,0.45)" }}
          >
            Risk Score
          </span>
          <span
            className="text-xs font-semibold px-2 py-0.5 rounded-full"
            style={{
              background: `${color}22`,
              color,
              border: `1px solid ${color}44`,
            }}
          >
            {active.level}
          </span>
        </div>
        <div className="flex items-end gap-1">
          <span className="text-3xl font-bold" style={{ color }}>
            {active.risk}
          </span>
          <span
            className="text-sm mb-1"
            style={{ color: "rgba(255,255,255,0.3)" }}
          >
            / 100
          </span>
        </div>
        <div
          className="h-1.5 rounded-full overflow-hidden"
          style={{ background: "rgba(255,255,255,0.08)" }}
        >
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${active.risk}%`, background: color }}
          />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

const FEATURES = [
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
        <path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
        <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z" />
      </svg>
    ),
    title: "Commit-level Scoring",
    description:
      "Every commit gets a 0–100 risk score based on size, complexity, and keyword signals in the message.",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
        <path d="M1.5 1.75V13.5h13.75a.75.75 0 0 1 0 1.5H.75a.75.75 0 0 1-.75-.75V1.75a.75.75 0 0 1 1.5 0Zm14.28 2.53-5.25 5.25a.75.75 0 0 1-1.06 0L7 7.06 4.28 9.78a.75.75 0 0 1-1.06-1.06l3.25-3.25a.75.75 0 0 1 1.06 0L9 7.94l4.72-4.72a.75.75 0 1 1 1.06 1.06Z" />
      </svg>
    ),
    title: "Trend Dashboard",
    description:
      "See risk trends across branches and time. Spot patterns before they become incidents.",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
        <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm5.879-4.773 4.264 2.559a.25.25 0 0 1 0 .428l-4.264 2.559A.25.25 0 0 1 7 8.559V3.442a.25.25 0 0 1 .379-.215Z" />
      </svg>
    ),
    title: "Instant Analysis",
    description:
      "Results in milliseconds. Fits naturally into PR review and CI/CD workflows with zero friction.",
  },
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
        <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8Z" />
      </svg>
    ),
    title: "GitHub OAuth",
    description:
      "Connect with one click. We read your repos and commits — never write, never store code.",
  },
];

const STEPS = [
  {
    number: "01",
    title: "Connect your repository",
    description:
      "Authenticate with GitHub and import any public or private repository in seconds.",
  },
  {
    number: "02",
    title: "Browse commits",
    description:
      "Navigate your full commit history or let the webhook surface new commits automatically.",
  },
  {
    number: "03",
    title: "Get the risk score",
    description:
      "Our model analyzes message patterns, diff size, and file count to produce a 0–100 risk score.",
  },
];

export default function HomePage() {
  const router = useRouter();
  const { isSignedIn } = useAuth();
  const { signIn } = useSignIn();

  const handleSignIn = async () => {
    await signIn?.authenticateWithRedirect({
      strategy: "oauth_github",
      redirectUrl: "/sso-callback",
      redirectUrlComplete: "/dashboard",
    });
  };

  // Must run after hydration so server and client initial renders match.
  useEffect(() => {
    // redirect already-authenticated users to the dashboard
    if (isSignedIn) router.prefetch("/dashboard");
  }, [isSignedIn, router]);

  return (
    <div
      className="min-h-screen"
      style={{ background: "var(--background)", color: "var(--foreground)" }}
    >
      {/* ── Navbar ──────────────────────────────────────────── */}
      <nav
        className="sticky top-0 z-50 flex items-center justify-between px-6 py-3 border-b"
        style={{
          borderColor: "var(--border-subtle)",
          background: "rgba(10,14,22,0.85)",
          backdropFilter: "blur(12px)",
        }}
      >
        <div className="flex items-center gap-2">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{
              background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 16 16"
              fill="white"
            >
              <path d="M11.28 6.78a.75.75 0 0 0-1.06-1.06L7.25 8.69 5.78 7.22a.75.75 0 0 0-1.06 1.06l2 2a.75.75 0 0 0 1.06 0l3.5-3.5Z" />
              <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0Zm-1.5 0a6.5 6.5 0 1 0-13 0 6.5 6.5 0 0 0 13 0Z" />
            </svg>
          </div>
          <span className="font-semibold text-sm">RiskPredict</span>
        </div>

        <div className="flex items-center gap-3">
          {isSignedIn ? (
            <button
              onClick={() => router.push("/dashboard")}
              className="btn-primary px-4 py-1.5 text-sm"
            >
              Go to Dashboard →
            </button>
          ) : (
            <button
              onClick={handleSignIn}
              className="btn-primary px-4 py-1.5 text-sm flex items-center gap-2"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
              </svg>
              Sign in with GitHub
            </button>
          )}
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* Background grid */}
        <div
          className="absolute inset-0 hero-grid opacity-40"
          aria-hidden="true"
        />
        {/* Radial glow */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(59,130,246,0.18) 0%, transparent 70%)",
          }}
          aria-hidden="true"
        />

        <div className="relative max-w-6xl mx-auto px-6 pt-20 pb-16">
          <div className="flex flex-col lg:flex-row items-center gap-12">
            {/* Left */}
            <div className="flex-1 text-center lg:text-left animate-fade-up">
              <div
                className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium mb-6"
                style={{
                  background: "rgba(59,130,246,0.12)",
                  border: "1px solid rgba(59,130,246,0.3)",
                  color: "var(--accent)",
                }}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-current" />
                AI-Powered Deployment Safety
              </div>

              <h1
                className="text-4xl lg:text-5xl font-bold leading-tight mb-5"
                style={{ color: "var(--foreground)" }}
              >
                Predict deployment risk{" "}
                <span
                  style={{
                    background:
                      "linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                  }}
                >
                  before it ships
                </span>
              </h1>

              <p
                className="text-base lg:text-lg leading-relaxed mb-8 max-w-lg mx-auto lg:mx-0"
                style={{ color: "var(--text-secondary)" }}
              >
                Connect your GitHub repository and get an instant AI risk score
                for every commit — before you merge or deploy.
              </p>

              <div className="flex flex-col sm:flex-row gap-3 justify-center lg:justify-start">
                {isSignedIn ? (
                  <button
                    onClick={() => router.push("/dashboard")}
                    className="btn-primary px-6 py-3 text-sm font-semibold"
                  >
                    Go to Dashboard →
                  </button>
                ) : (
                  <>
                    <button
                      onClick={handleSignIn}
                      className="btn-primary px-6 py-3 text-sm font-semibold flex items-center justify-center gap-2"
                    >
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 16 16"
                        fill="currentColor"
                      >
                        <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
                      </svg>
                      Start for free — GitHub
                    </button>
                    <button
                      onClick={() => {
                        document
                          .getElementById("how-it-works")
                          ?.scrollIntoView({ behavior: "smooth" });
                      }}
                      className="btn-ghost px-6 py-3 text-sm font-semibold"
                    >
                      See how it works ↓
                    </button>
                  </>
                )}
              </div>

              <p
                className="text-xs mt-4"
                style={{ color: "var(--text-muted)" }}
              >
                Free to use · No card required · Read-only GitHub access
              </p>
            </div>

            {/* Right — animated widget */}
            <div className="flex-shrink-0 w-full max-w-xs lg:max-w-sm">
              <RiskPreviewWidget />
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center mb-10">
          <h2
            className="text-2xl font-bold mb-2"
            style={{ color: "var(--foreground)" }}
          >
            Everything you need to ship safely
          </h2>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            From first commit to production — stay ahead of risky changes.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="rounded-xl p-5 space-y-3 hover:brightness-110 transition-all"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
              }}
            >
              <div style={{ color: "var(--accent)" }}>{f.icon}</div>
              <h3
                className="text-sm font-semibold"
                style={{ color: "var(--foreground)" }}
              >
                {f.title}
              </h3>
              <p className="text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                {f.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ────────────────────────────────────── */}
      <section
        id="how-it-works"
        className="max-w-6xl mx-auto px-6 py-16 border-t"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <div className="text-center mb-10">
          <h2
            className="text-2xl font-bold mb-2"
            style={{ color: "var(--foreground)" }}
          >
            Up and running in 60 seconds
          </h2>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            No SDK, no YAML config, no CI changes required.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {STEPS.map((s, i) => (
            <div key={s.number} className="flex gap-4">
              <div className="flex-shrink-0 flex flex-col items-center">
                <div
                  className="w-8 h-8 rounded-full text-sm font-bold flex items-center justify-center flex-shrink-0"
                  style={{
                    background: "rgba(59,130,246,0.15)",
                    color: "var(--accent)",
                    border: "1px solid rgba(59,130,246,0.3)",
                  }}
                >
                  {s.number}
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className="w-px flex-1 mt-2 hidden md:block"
                    style={{ background: "var(--border-subtle)" }}
                  />
                )}
              </div>
              <div className="pb-6">
                <h3
                  className="text-sm font-semibold mb-1"
                  style={{ color: "var(--foreground)" }}
                >
                  {s.title}
                </h3>
                <p
                  className="text-xs leading-relaxed"
                  style={{ color: "var(--text-muted)" }}
                >
                  {s.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA banner ──────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 py-8 mb-12">
        <div
          className="rounded-2xl p-8 flex flex-col sm:flex-row items-center justify-between gap-6"
          style={{
            background:
              "linear-gradient(135deg, rgba(59,130,246,0.15) 0%, rgba(139,92,246,0.1) 100%)",
            border: "1px solid rgba(59,130,246,0.25)",
          }}
        >
          <div>
            <h3
              className="text-lg font-bold mb-1"
              style={{ color: "var(--foreground)" }}
            >
              Ready to stop flying blind?
            </h3>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              Join developers who check risk scores before every deploy.
            </p>
          </div>
          {isSignedIn ? (
            <button
              onClick={() => router.push("/dashboard")}
              className="btn-primary px-6 py-2.5 text-sm font-semibold flex-shrink-0"
            >
              Open Dashboard →
            </button>
          ) : (
            <button
              onClick={handleSignIn}
              className="btn-primary px-6 py-2.5 text-sm font-semibold flex-shrink-0 flex items-center gap-2"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
              </svg>
              Get started for free
            </button>
          )}
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────── */}
      <footer
        className="border-t px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-3"
        style={{
          borderColor: "var(--border-subtle)",
          background: "var(--surface)",
        }}
      >
        <div className="flex items-center gap-2">
          <div
            className="w-5 h-5 rounded flex items-center justify-center"
            style={{
              background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            }}
          >
            <svg width="10" height="10" viewBox="0 0 16 16" fill="white">
              <path d="M11.28 6.78a.75.75 0 0 0-1.06-1.06L7.25 8.69 5.78 7.22a.75.75 0 0 0-1.06 1.06l2 2a.75.75 0 0 0 1.06 0l3.5-3.5Z" />
              <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0Zm-1.5 0a6.5 6.5 0 1 0-13 0 6.5 6.5 0 0 0 13 0Z" />
            </svg>
          </div>
          <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
            RiskPredict
          </span>
        </div>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Read-only GitHub access · No code stored · MIT licensed
        </p>
        <div className="flex items-center gap-4">
          <Link
            href="/login"
            className="text-xs hover:opacity-80 transition-opacity"
            style={{ color: "var(--text-muted)" }}
          >
            Sign in
          </Link>
        </div>
      </footer>
    </div>
  );
}
