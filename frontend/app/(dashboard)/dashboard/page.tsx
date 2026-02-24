"use client";

import { useEffect, useState } from "react";
import { api, AuthUser, HealthResponse, Repository } from "@/lib/api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function formatUptime(seconds: number) {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

// ---------------------------------------------------------------------------
// Stat Card
// ---------------------------------------------------------------------------
function StatCard({
  label,
  value,
  sub,
  accentColor,
  live,
  icon,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  accentColor?: string;
  live?: boolean;
  icon?: React.ReactNode;
}) {
  return (
    <div
      className="card p-5 flex flex-col gap-3 relative overflow-hidden"
      style={{ borderTopColor: accentColor ?? "var(--border-subtle)", borderTopWidth: 2 }}
    >
      <div className="flex items-start justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
          {label}
        </span>
        <div className="flex items-center gap-1.5">
          {live && (
            <span className="flex items-center gap-1 text-[10px] font-bold" style={{ color: "#22c55e" }}>
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse inline-block" />
              LIVE
            </span>
          )}
          {icon && (
            <span style={{ color: accentColor ?? "var(--text-muted)", opacity: 0.7 }}>{icon}</span>
          )}
        </div>
      </div>
      <div className="text-3xl font-black tracking-tight" style={{ color: accentColor ?? "var(--foreground)" }}>
        {value}
      </div>
      {sub && (
        <div className="text-xs" style={{ color: "var(--text-muted)" }}>{sub}</div>
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
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetch = () =>
      api.health
        .get()
        .then((h) => { if (mounted) { setHealth(h); setLastChecked(new Date()); } })
        .catch(() => { if (mounted) setError(true); });
    fetch();
    const id = setInterval(fetch, 30_000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  if (error)
    return (
      <div className="card p-5">
        <SectionHeader title="System Health" />
        <div className="flex items-center gap-2 text-sm mt-3 px-3 py-2 rounded-lg" style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)" }}>
          <span className="w-2 h-2 rounded-full bg-red-400 flex-shrink-0" />
          Backend unreachable
        </div>
      </div>
    );

  if (!health)
    return (
      <div className="card p-5">
        <SectionHeader title="System Health" />
        <div className="space-y-3 mt-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-4 rounded skeleton" style={{ width: i % 2 === 0 ? "60%" : "80%" }} />
          ))}
        </div>
      </div>
    );

  const rows = [
    { label: "API Status", value: health.status.toUpperCase(), ok: health.status === "ok" },
    { label: "Database", value: health.db_status.toUpperCase(), ok: health.db_status === "ok" },
    { label: "Version", value: `v${health.version}`, ok: true },
    { label: "Uptime", value: formatUptime(health.uptime_seconds), ok: true },
  ];

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <SectionHeader title="System Health" />
        <span className="flex items-center gap-1 text-[10px] font-bold" style={{ color: "#22c55e" }}>
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse inline-block" />
          LIVE
        </span>
      </div>
      <div className="space-y-2">
        {rows.map((r) => (
          <div
            key={r.label}
            className="flex items-center justify-between px-3 py-2 rounded-lg text-xs"
            style={{ background: "var(--surface-raised)" }}
          >
            <span style={{ color: "var(--text-muted)" }}>{r.label}</span>
            <span
              className="flex items-center gap-1.5 font-bold font-mono"
              style={{ color: r.ok ? "#22c55e" : "#ef4444" }}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${r.ok ? "bg-green-400" : "bg-red-400"}`} />
              {r.value}
            </span>
          </div>
        ))}
      </div>
      {lastChecked && (
        <div className="mt-3 text-[10px]" style={{ color: "var(--text-dim)" }}>
          Last checked: {lastChecked.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pipeline flow
// ---------------------------------------------------------------------------
const pipelineSteps = [
  { label: "GitHub", sub: "Webhook / API", color: "#3b82f6" },
  { label: "Commit Analyzer", sub: "Diff Parser", color: "#a78bfa" },
  { label: "Risk Engine", sub: "Scorer", color: "#f59e0b" },
  { label: "ML Model", sub: "GNN / RF", color: "#22c55e" },
  { label: "Dashboard", sub: "Real-time", color: "#38bdf8" },
];

function PipelineFlow() {
  return (
    <div className="card p-5">
      <SectionHeader title="Pipeline Overview" />
      <div className="flex items-center gap-2 mt-4 overflow-x-auto pb-1">
        {pipelineSteps.map((step, i) => (
          <div key={step.label} className="flex items-center gap-2 flex-shrink-0">
            <div
              className="flex flex-col items-center justify-center w-[88px] h-14 rounded-xl text-center px-2"
              style={{
                background: `${step.color}14`,
                border: `1px solid ${step.color}35`,
              }}
            >
              <div className="text-[11px] font-bold leading-tight" style={{ color: step.color }}>
                {step.label}
              </div>
              <div className="text-[9px] mt-0.5" style={{ color: "var(--text-muted)" }}>
                {step.sub}
              </div>
            </div>
            {i < pipelineSteps.length - 1 && (
              <svg width="14" height="10" viewBox="0 0 14 10" fill="none">
                <path d="M0 5h12M8 1l4 4-4 4" stroke="var(--border)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Recent activity
// ---------------------------------------------------------------------------
const placeholderActivity = [
  { sha: "a3f2c1d", repo: "owner/api-service", risk: "HIGH", score: 82, msg: "fix: urgent hotfix for auth bypass", time: "2m ago", color: "#ef4444" },
  { sha: "b7e8912", repo: "owner/frontend-app", risk: "MED", score: 45, msg: "feat: add user profile page", time: "14m ago", color: "#f59e0b" },
  { sha: "c1d4567", repo: "owner/data-pipeline", risk: "LOW", score: 12, msg: "chore: update dependencies", time: "1h ago", color: "#22c55e" },
  { sha: "d9a0b3e", repo: "owner/api-service", risk: "LOW", score: 8, msg: "docs: update README", time: "2h ago", color: "#22c55e" },
];

function RecentActivity({ repoCount }: { repoCount: number }) {
  if (repoCount === 0) {
    return (
      <div className="card p-5">
        <SectionHeader title="Recent Activity" />
        <div className="flex flex-col items-center justify-center py-10 gap-4">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center"
            style={{ background: "var(--surface-raised)", border: "1px solid var(--border)" }}
          >
            <svg width="20" height="20" viewBox="0 0 16 16" fill="var(--text-dim)">
              <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8Z" />
            </svg>
          </div>
          <div className="text-center">
            <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
              No activity yet
            </div>
            <div className="text-xs mt-1 max-w-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
              Import a repository to start tracking commit risk.
            </div>
          </div>
          <a
            href="/repositories"
            className="btn-primary text-xs px-4 py-2"
          >
            Import Repository
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <SectionHeader title="Recent Activity" />
        <span
          className="text-[10px] font-bold px-2 py-0.5 rounded-md border"
          style={{
            background: "rgba(245,158,11,0.08)",
            color: "#f59e0b",
            borderColor: "rgba(245,158,11,0.2)",
          }}
        >
          DEMO DATA
        </span>
      </div>
      <div className="space-y-1.5">
        {placeholderActivity.map((a) => (
          <div
            key={a.sha}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors"
            style={{ background: "var(--surface-raised)" }}
          >
            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: a.color }} />
            <code className="text-[11px] font-mono flex-shrink-0" style={{ color: "var(--text-muted)" }}>
              {a.sha}
            </code>
            <span className="truncate flex-1 text-xs" style={{ color: "var(--foreground)" }}>
              {a.msg}
            </span>
            <span
              className="badge flex-shrink-0"
              style={{ color: a.color, borderColor: `${a.color}35`, background: `${a.color}10`, fontSize: "10px" }}
            >
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
// Roadmap
// ---------------------------------------------------------------------------
const roadmapItems = [
  { label: "Graph Neural Network model", done: false },
  { label: "Multi-repo risk analytics", done: false },
  { label: "Team risk profiling", done: false },
  { label: "Real-time anomaly detection", done: false },
  { label: "Technical debt scoring", done: false },
  { label: "SaaS billing & plans", done: false },
];

function Roadmap() {
  return (
    <div className="card p-5">
      <SectionHeader title="Roadmap" />
      <div className="space-y-2 mt-4">
        {roadmapItems.map((item) => (
          <div key={item.label} className="flex items-center gap-2.5 text-xs">
            <span
              className="w-3.5 h-3.5 rounded flex items-center justify-center flex-shrink-0"
              style={{
                border: `1px solid ${item.done ? "#22c55e" : "var(--border)"}`,
                background: item.done ? "rgba(34,197,94,0.1)" : "transparent",
              }}
            >
              {item.done && <span style={{ color: "#22c55e", fontSize: "9px", fontWeight: "bold" }}>✓</span>}
            </span>
            <span style={{ color: item.done ? "var(--foreground)" : "var(--text-muted)" }}>
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section header helper
// ---------------------------------------------------------------------------
function SectionHeader({ title }: { title: string }) {
  return (
    <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
      {title}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function DashboardPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loadingRepos, setLoadingRepos] = useState(true);

  useEffect(() => {
    api.repositories.list().then(setRepos).catch(() => {}).finally(() => setLoadingRepos(false));
    api.auth.me().then(setUser).catch(() => {});
  }, []);

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 h-14 border-b flex-shrink-0"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <div>
          <h1 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
            {greeting()}{user ? `, ${user.username}` : ""} 👋
          </h1>
          <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>
            Here's what's happening with your deployments today.
          </p>
        </div>
        <a
          href="/repositories"
          className="btn-primary text-xs px-3 py-1.5"
        >
          <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
            <path d="M7.75 2a.75.75 0 0 1 .75.75V7h4.25a.75.75 0 0 1 0 1.5H8.5v4.25a.75.75 0 0 1-1.5 0V8.5H2.75a.75.75 0 0 1 0-1.5H7V2.75A.75.75 0 0 1 7.75 2Z" />
          </svg>
          Import Repo
        </a>
      </header>

      {/* Body */}
      <main className="flex-1 p-6 space-y-5 overflow-auto">
        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Repositories"
            value={loadingRepos ? "—" : repos.length}
            sub="connected & monitored"
            accentColor="#3b82f6"
            live
            icon={
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8Z" />
              </svg>
            }
          />
          <StatCard
            label="Commits Analysed"
            value="—"
            sub="Requires webhook pipeline"
            accentColor="#a78bfa"
          />
          <StatCard
            label="High Risk Commits"
            value="—"
            sub="Requires webhook pipeline"
            accentColor="#ef4444"
          />
          <StatCard
            label="Avg Risk Score"
            value="—"
            sub="Requires webhook pipeline"
            accentColor="#f59e0b"
          />
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Left 2/3 */}
          <div className="lg:col-span-2 space-y-5">
            <PipelineFlow />
            <RecentActivity repoCount={repos.length} />
          </div>

          {/* Right 1/3 */}
          <div className="space-y-5">
            <SystemHealthWidget />
            <Roadmap />
          </div>
        </div>
      </main>
    </div>
  );
}
