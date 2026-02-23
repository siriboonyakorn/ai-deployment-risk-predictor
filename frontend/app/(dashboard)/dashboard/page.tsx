"use client";

import { useEffect, useState } from "react";
import { api, HealthResponse, Repository } from "@/lib/api";

// ---------------------------------------------------------------------------
// Stat Card
// ---------------------------------------------------------------------------
function StatCard({
  label,
  value,
  sub,
  accent,
  live,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  accent?: string;
  live?: boolean;
}) {
  return (
    <div
      className="card p-5 flex flex-col gap-2"
      style={{ borderColor: accent ? `${accent}40` : undefined }}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
          {label}
        </span>
        {live && (
          <span className="flex items-center gap-1 text-[10px] font-semibold" style={{ color: "#3fb950" }}>
            <span className="w-1.5 h-1.5 rounded-full bg-[#3fb950] animate-pulse inline-block" />
            LIVE
          </span>
        )}
      </div>
      <div
        className="text-3xl font-bold tracking-tight"
        style={{ color: accent ?? "var(--foreground)" }}
      >
        {value}
      </div>
      {sub && (
        <div className="text-xs" style={{ color: "var(--text-muted)" }}>
          {sub}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// System Health Widget
// ---------------------------------------------------------------------------
function SystemHealthWidget() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let mounted = true;
    const fetch = () =>
      api.health
        .get()
        .then((h) => { if (mounted) setHealth(h); })
        .catch(() => { if (mounted) setError(true); });
    fetch();
    const id = setInterval(fetch, 30_000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  if (error)
    return (
      <div className="card p-5">
        <div className="text-sm font-semibold mb-3" style={{ color: "var(--foreground)" }}>System Health</div>
        <div className="flex items-center gap-2 text-sm" style={{ color: "#f85149" }}>
          <span className="w-2 h-2 rounded-full bg-[#f85149]" />
          Backend unreachable
        </div>
      </div>
    );

  if (!health)
    return (
      <div className="card p-5 animate-pulse">
        <div className="h-4 w-24 rounded mb-4" style={{ background: "var(--surface-raised)" }} />
        <div className="h-3 w-full rounded mb-2" style={{ background: "var(--surface-raised)" }} />
        <div className="h-3 w-2/3 rounded" style={{ background: "var(--surface-raised)" }} />
      </div>
    );

  const uptimeHours = (health.uptime_seconds / 3600).toFixed(1);
  const rows = [
    { label: "API Status", value: health.status.toUpperCase(), ok: health.status === "ok" },
    { label: "Database", value: health.db_status.toUpperCase(), ok: health.db_status === "ok" },
    { label: "Version", value: health.version, ok: true },
    { label: "Uptime", value: `${uptimeHours}h`, ok: true },
  ];

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>System Health</div>
        <span className="flex items-center gap-1 text-[10px] font-semibold" style={{ color: "#3fb950" }}>
          <span className="w-1.5 h-1.5 rounded-full bg-[#3fb950] animate-pulse inline-block" />
          LIVE
        </span>
      </div>
      <div className="space-y-2.5">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between text-xs">
            <span style={{ color: "var(--text-muted)" }}>{r.label}</span>
            <span className="flex items-center gap-1.5 font-mono font-semibold" style={{ color: r.ok ? "#3fb950" : "#f85149" }}>
              <span className={`w-1.5 h-1.5 rounded-full ${r.ok ? "bg-[#3fb950]" : "bg-[#f85149]"}`} />
              {r.value}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-4 text-[11px]" style={{ borderTop: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}>
        Last checked: {new Date(health.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Architecture Flow
// ---------------------------------------------------------------------------
function ArchFlow() {
  const steps = [
    { label: "GitHub", sub: "Webhook", color: "#2f81f7" },
    { label: "Analyzer", sub: "Commits", color: "#a371f7" },
    { label: "Risk Engine", sub: "Scoring", color: "#d29922" },
    { label: "ML Model", sub: "Prediction", color: "#3fb950" },
    { label: "Dashboard", sub: "Realtime", color: "#58a6ff" },
  ];

  return (
    <div className="card p-5">
      <div className="text-sm font-semibold mb-4" style={{ color: "var(--foreground)" }}>Pipeline Overview</div>
      <div className="flex items-center gap-1 overflow-x-auto pb-1">
        {steps.map((step, i) => (
          <div key={step.label} className="flex items-center gap-1 flex-shrink-0">
            <div className="flex flex-col items-center gap-1">
              <div
                className="w-16 h-12 rounded-md flex flex-col items-center justify-center text-center"
                style={{ background: `${step.color}18`, border: `1px solid ${step.color}40` }}
              >
                <div className="text-[10px] font-bold" style={{ color: step.color }}>{step.label}</div>
                <div className="text-[9px]" style={{ color: "var(--text-muted)" }}>{step.sub}</div>
              </div>
            </div>
            {i < steps.length - 1 && (
              <svg width="16" height="8" viewBox="0 0 16 8" fill="none">
                <path d="M0 4h14M10 1l4 3-4 3" stroke="var(--border)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Recent Activity (placeholder until webhooks populate real data)
// ---------------------------------------------------------------------------
const placeholderActivity = [
  { sha: "a3f2c1d", repo: "owner/api-service", risk: "HIGH", score: 82, msg: "fix: urgent hotfix for auth bypass", time: "2m ago", color: "#f85149" },
  { sha: "b7e8912", repo: "owner/frontend-app", risk: "MEDIUM", score: 45, msg: "feat: add user profile page", time: "14m ago", color: "#d29922" },
  { sha: "c1d4567", repo: "owner/data-pipeline", risk: "LOW", score: 12, msg: "chore: update dependencies", time: "1h ago", color: "#3fb950" },
  { sha: "d9a0b3e", repo: "owner/api-service", risk: "LOW", score: 8, msg: "docs: update README", time: "2h ago", color: "#3fb950" },
];

function RecentActivity({ repoCount }: { repoCount: number }) {
  if (repoCount === 0) {
    return (
      <div className="card p-5">
        <div className="text-sm font-semibold mb-4" style={{ color: "var(--foreground)" }}>Recent Activity</div>
        <div className="flex flex-col items-center justify-center py-8 gap-3">
          <svg width="32" height="32" viewBox="0 0 16 16" fill="var(--text-muted)">
            <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8Z" />
          </svg>
          <div className="text-sm text-center" style={{ color: "var(--text-muted)" }}>
            No repositories connected yet.<br />Import one to see commit activity.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>Recent Activity</div>
        <span
          className="text-[10px] font-semibold px-2 py-0.5 rounded"
          style={{ background: "var(--surface-raised)", color: "var(--text-muted)", border: "1px solid var(--border-subtle)" }}
        >
          DEMO DATA
        </span>
      </div>
      <div className="space-y-1">
        {placeholderActivity.map((a) => (
          <div
            key={a.sha}
            className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm"
            style={{ background: "var(--surface-raised)" }}
          >
            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: a.color }} />
            <code className="text-xs font-mono flex-shrink-0" style={{ color: "var(--text-muted)" }}>
              {a.sha}
            </code>
            <span className="truncate flex-1 text-xs" style={{ color: "var(--foreground)" }}>
              {a.msg}
            </span>
            <span className="badge text-[10px] border flex-shrink-0" style={{ color: a.color, borderColor: `${a.color}40`, background: `${a.color}12` }}>
              {a.risk} {a.score}%
            </span>
            <span className="text-[11px] flex-shrink-0" style={{ color: "var(--text-muted)" }}>
              {a.time}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function DashboardPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(true);

  useEffect(() => {
    api.repositories
      .list()
      .then(setRepos)
      .catch(() => {})
      .finally(() => setLoadingRepos(false));
  }, []);

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <div>
          <h1 className="text-base font-semibold" style={{ color: "var(--foreground)" }}>
            Dashboard
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            AI Deployment Risk Predictor — overview
          </p>
        </div>
        <a
          href="/repositories"
          className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-opacity hover:opacity-80"
          style={{ background: "var(--accent)", color: "white" }}
        >
          + Import Repo
        </a>
      </header>

      {/* Body */}
      <main className="flex-1 p-6 space-y-6">
        {/* Stat row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Repositories"
            value={loadingRepos ? "—" : repos.length}
            sub="connected & monitored"
            live
          />
          <StatCard
            label="Commits Analysed"
            value="—"
            sub="Requires webhook data"
          />
          <StatCard
            label="High Risk Commits"
            value="—"
            sub="Requires webhook data"
            accent="#f85149"
          />
          <StatCard
            label="Avg Risk Score"
            value="—"
            sub="Requires webhook data"
          />
        </div>

        {/* Second row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <ArchFlow />
            <RecentActivity repoCount={repos.length} />
          </div>
          <div className="space-y-4">
            <SystemHealthWidget />
            {/* Roadmap card */}
            <div className="card p-5">
              <div className="text-sm font-semibold mb-3" style={{ color: "var(--foreground)" }}>Roadmap</div>
              <div className="space-y-2">
                {[
                  { label: "Graph Neural Network", done: false },
                  { label: "Multi-repo analytics", done: false },
                  { label: "Team risk profiling", done: false },
                  { label: "Real-time anomaly detection", done: false },
                  { label: "Technical debt scoring", done: false },
                  { label: "SaaS billing", done: false },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
                    <span className="w-3 h-3 rounded-sm flex items-center justify-center flex-shrink-0" style={{ border: "1px solid var(--border)" }}>
                      {item.done && <span className="text-[#3fb950]">✓</span>}
                    </span>
                    {item.label}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
