"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated, initiateGitHubLogin } from "@/lib/auth";

const features = [
  {
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <path d="M8 .25a7.75 7.75 0 1 0 0 15.5A7.75 7.75 0 0 0 8 .25Zm3.03 4.72-4.5 4.5a.75.75 0 0 1-1.06 0L3.72 7.72a.75.75 0 1 1 1.06-1.06l1.22 1.22 3.97-3.97a.75.75 0 1 1 1.06 1.06Z" />
      </svg>
    ),
    title: "AI Risk Scoring",
    desc: "Every commit scored 0–100 using ML models trained on deployment patterns.",
  },
  {
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <path d="M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z" />
      </svg>
    ),
    title: "GitHub Integration",
    desc: "Connect repositories in seconds — no manual configuration required.",
  },
  {
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <path d="M1.5 1.75V13.5h13.75a.75.75 0 0 1 0 1.5H.75a.75.75 0 0 1-.75-.75V1.75a.75.75 0 0 1 1.5 0Zm14.28 2.53-5.25 5.25a.75.75 0 0 1-1.06 0L7 7.06 4.28 9.78a.751.751 0 0 1-1.06-1.06l3.25-3.25a.75.75 0 0 1 1.06 0L10 7.94l4.72-4.72a.751.751 0 0 1 1.06 1.06Z" />
      </svg>
    ),
    title: "Real-time Dashboard",
    desc: "Live pipeline metrics, risk trends, and deployment health in one view.",
  },
  {
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <path d="M8.533.133a1.75 1.75 0 0 0-1.066 0l-5.25 1.68A1.75 1.75 0 0 0 1 3.48V8c0 3.572 2.111 6.26 5.49 7.773.374.165.644.165 1.021 0C10.888 14.26 13 11.573 13 8V3.48a1.75 1.75 0 0 0-1.217-1.667Z" />
      </svg>
    ),
    title: "Privacy First",
    desc: "Only commit metadata is analysed — your code never leaves GitHub.",
  },
];

const riskItems = [
  { sha: "a3f2c1d", label: "auth bypass hotfix", level: "HIGH", score: 87, color: "#ef4444" },
  { sha: "b7e8912", label: "user profile feature", level: "MED", score: 44, color: "#f59e0b" },
  { sha: "c1d4567", label: "update dependencies", level: "LOW", score: 11, color: "#22c55e" },
];

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace("/dashboard");
    }
  }, [router]);

  return (
    <div className="min-h-screen flex hero-grid" style={{ background: "var(--background)" }}>
      {/* Gradient glow top */}
      <div
        className="pointer-events-none fixed inset-0"
        style={{ background: "var(--gradient-hero)", zIndex: 0 }}
      />

      {/* LEFT PANEL — branding */}
      <div className="hidden lg:flex flex-col justify-between flex-1 px-16 py-14 relative z-10">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center text-white font-black text-sm glow-blue"
            style={{ background: "linear-gradient(135deg, #3b82f6, #1d4ed8)" }}
          >
            AI
          </div>
          <span className="font-bold text-base tracking-tight" style={{ color: "var(--foreground)" }}>
            Risk Predictor
          </span>
        </div>

        {/* Hero text */}
        <div className="space-y-7 max-w-lg">
          <div className="space-y-3">
            <div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold border"
              style={{
                background: "rgba(59,130,246,0.1)",
                borderColor: "rgba(59,130,246,0.25)",
                color: "#60a5fa",
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse inline-block" />
              AI-Powered · Open Source
            </div>
            <h1 className="text-5xl font-black tracking-tight leading-[1.1]" style={{ color: "var(--foreground)" }}>
              Predict deployment
              <br />
              <span style={{ color: "var(--accent-hover)" }}>risk before it ships.</span>
            </h1>
            <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
              Connect your GitHub repositories and get instant AI-powered risk scores
              for every commit — before it reaches production.
            </p>
          </div>

          {/* Feature list */}
          <div className="grid grid-cols-1 gap-3">
            {features.map((f) => (
              <div key={f.title} className="flex items-start gap-3">
                <div
                  className="mt-0.5 w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0"
                  style={{ background: "var(--accent-muted)", color: "var(--accent-hover)" }}
                >
                  {f.icon}
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
                    {f.title}
                  </div>
                  <div className="text-xs leading-relaxed mt-0.5" style={{ color: "var(--text-muted)" }}>
                    {f.desc}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Mini preview widget */}
        <div
          className="card-elevated rounded-xl p-4 space-y-2 max-w-sm"
          style={{ backdropFilter: "blur(20px)" }}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold" style={{ color: "var(--foreground)" }}>
              Recent Risk Analysis
            </span>
            <span
              className="text-[10px] font-bold px-2 py-0.5 rounded-full"
              style={{ background: "rgba(34,197,94,0.15)", color: "#22c55e" }}
            >
              LIVE
            </span>
          </div>
          {riskItems.map((r) => (
            <div
              key={r.sha}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs"
              style={{ background: "var(--surface)" }}
            >
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: r.color }} />
              <code className="font-mono" style={{ color: "var(--text-muted)" }}>{r.sha}</code>
              <span className="flex-1 truncate" style={{ color: "var(--foreground)" }}>
                {r.label}
              </span>
              <span
                className="font-bold px-2 py-0.5 rounded text-[10px]"
                style={{ background: `${r.color}18`, color: r.color }}
              >
                {r.level} {r.score}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* RIGHT PANEL — login card */}
      <div className="flex items-center justify-center w-full lg:w-[480px] flex-shrink-0 px-6 py-12 relative z-10">
        <div
          className="w-full max-w-sm card-elevated p-8 space-y-6 animate-fade-up"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 justify-center mb-2">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-black text-xs"
              style={{ background: "linear-gradient(135deg, #3b82f6, #1d4ed8)" }}
            >
              AI
            </div>
            <span className="font-bold" style={{ color: "var(--foreground)" }}>Risk Predictor</span>
          </div>

          {/* Header */}
          <div className="space-y-1.5 text-center">
            <h2 className="text-xl font-bold" style={{ color: "var(--foreground)" }}>
              Welcome back
            </h2>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              Sign in with GitHub to access your dashboard
            </p>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px" style={{ background: "var(--border-subtle)" }} />
            <span className="text-xs" style={{ color: "var(--text-dim)" }}>CONTINUE WITH</span>
            <div className="flex-1 h-px" style={{ background: "var(--border-subtle)" }} />
          </div>

          {/* GitHub button */}
          <button
            onClick={initiateGitHubLogin}
            className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl text-sm font-semibold transition-all cursor-pointer"
            style={{
              background: "var(--surface-overlay)",
              color: "var(--foreground)",
              border: "1px solid var(--border)",
            }}
            onMouseEnter={(e) => {
              const el = e.currentTarget;
              el.style.borderColor = "var(--accent)";
              el.style.background = "var(--accent-muted)";
              el.style.boxShadow = "0 0 20px var(--accent-glow)";
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget;
              el.style.borderColor = "var(--border)";
              el.style.background = "var(--surface-overlay)";
              el.style.boxShadow = "none";
            }}
          >
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
            </svg>
            Sign in with GitHub
          </button>

          {/* Trust indicators */}
          <div className="flex items-center justify-center gap-4 pt-1">
            {[
              { icon: "🔒", text: "Read-only access" },
              { icon: "🚫", text: "No code stored" },
              { icon: "🔑", text: "OAuth secured" },
            ].map((t) => (
              <div key={t.text} className="flex items-center gap-1 text-[11px]" style={{ color: "var(--text-muted)" }}>
                <span>{t.icon}</span>
                <span>{t.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
