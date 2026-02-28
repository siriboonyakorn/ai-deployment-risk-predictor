"use client";

import { useEffect, useState, useCallback } from "react";
import {
  api,
  AuthUser,
  DashboardStats,
  HealthResponse,
  RecentActivityItem,
  Repository,
  RiskDistributionResponse,
} from "@/lib/api";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import RiskBadge from "@/components/RiskBadge";

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

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const RISK_COLORS: Record<string, string> = {
  LOW: "#22c55e",
  MEDIUM: "#f59e0b",
  HIGH: "#ef4444",
};

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
  trend,
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  accentColor?: string;
  live?: boolean;
  icon?: React.ReactNode;
  trend?: string;
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
      <div className="flex items-center justify-between">
        {sub && (
          <div className="text-xs" style={{ color: "var(--text-muted)" }}>{sub}</div>
        )}
        {trend && (
          <div className="text-[10px] font-semibold" style={{ color: accentColor }}>{trend}</div>
        )}
      </div>
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
// Risk Distribution Pie Chart
// ---------------------------------------------------------------------------
function RiskDistributionChart({ data }: { data: RiskDistributionResponse | null }) {
  if (!data || data.total === 0) {
    return (
      <div className="card p-5">
        <SectionHeader title="Risk Distribution" />
        <div className="flex items-center justify-center h-48 text-xs" style={{ color: "var(--text-muted)" }}>
          No risk data yet. Analyze some commits to see the distribution.
        </div>
      </div>
    );
  }

  const pieData = data.distribution.map((d) => ({
    name: d.level,
    value: d.count,
    color: RISK_COLORS[d.level] ?? "#6b7a96",
  }));

  return (
    <div className="card p-5">
      <SectionHeader title="Risk Distribution" />
      <div className="flex items-center gap-4 mt-4">
        <div className="w-40 h-40 flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={35}
                outerRadius={65}
                paddingAngle={3}
                dataKey="value"
                stroke="none"
              >
                {pieData.map((entry, idx) => (
                  <Cell key={idx} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "var(--surface-raised)",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  fontSize: "12px",
                  color: "var(--foreground)",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex-1 space-y-2">
          {data.distribution.map((d) => (
            <div key={d.level} className="flex items-center gap-3">
              <span className="w-3 h-3 rounded-sm flex-shrink-0" style={{ background: RISK_COLORS[d.level] }} />
              <span className="text-xs flex-1" style={{ color: "var(--foreground)" }}>{d.level}</span>
              <span className="text-xs font-mono font-bold" style={{ color: "var(--foreground)" }}>{d.count}</span>
              <span className="text-xs font-mono w-12 text-right" style={{ color: "var(--text-muted)" }}>{d.percentage}%</span>
            </div>
          ))}
          <div className="border-t pt-2 mt-2 flex items-center justify-between text-xs" style={{ borderColor: "var(--border-subtle)" }}>
            <span style={{ color: "var(--text-muted)" }}>Total</span>
            <span className="font-mono font-bold" style={{ color: "var(--foreground)" }}>{data.total}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Score Histogram Bar Chart
// ---------------------------------------------------------------------------
function ScoreHistogramChart({ data }: { data: RiskDistributionResponse | null }) {
  if (!data || data.total === 0) return null;

  const barData = data.score_histogram.map((b) => ({
    range: b.range,
    count: b.count,
    fill: parseInt(b.range) < 30 ? RISK_COLORS.LOW : parseInt(b.range) < 60 ? RISK_COLORS.MEDIUM : RISK_COLORS.HIGH,
  }));

  return (
    <div className="card p-5">
      <SectionHeader title="Score Distribution" />
      <div className="mt-4 h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={barData} barCategoryGap="15%">
            <XAxis dataKey="range" tick={{ fontSize: 10, fill: "var(--text-muted)" }} axisLine={{ stroke: "var(--border)" }} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: "var(--text-muted)" }} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip
              contentStyle={{
                background: "var(--surface-raised)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                fontSize: "12px",
                color: "var(--foreground)",
              }}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {barData.map((entry, idx) => (
                <Cell key={idx} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
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
// Recent Activity (live data)
// ---------------------------------------------------------------------------
function RecentActivity({ items, loading }: { items: RecentActivityItem[]; loading: boolean }) {
  if (loading) {
    return (
      <div className="card p-5">
        <SectionHeader title="Recent Activity" />
        <div className="space-y-2 mt-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-12 rounded skeleton" />
          ))}
        </div>
      </div>
    );
  }

  if (items.length === 0) {
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
            <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>No activity yet</div>
            <div className="text-xs mt-1 max-w-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
              Import a repository and analyze commits to start tracking risk.
            </div>
          </div>
          <a href="/repositories" className="btn-primary text-xs px-4 py-2">Import Repository</a>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <SectionHeader title="Recent Activity" />
        <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>{items.length} commits</span>
      </div>
      <div className="space-y-1.5">
        {items.map((a) => {
          const color = RISK_COLORS[a.risk_level] ?? "#6b7a96";
          return (
            <div
              key={a.sha}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors"
              style={{ background: "var(--surface-raised)" }}
            >
              <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
              <code className="text-[11px] font-mono flex-shrink-0" style={{ color: "var(--text-muted)" }}>
                {a.sha.slice(0, 7)}
              </code>
              <span className="truncate flex-1 text-xs" style={{ color: "var(--foreground)" }}>
                {a.message.split("\n")[0] || "(no message)"}
              </span>
              <RiskBadge level={a.risk_level} score={a.risk_score} />
              <span className="text-[11px] flex-shrink-0" style={{ color: "var(--text-muted)" }}>
                {timeAgo(a.analyzed_at)}
              </span>
            </div>
          );
        })}
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
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [distro, setDistro] = useState<RiskDistributionResponse | null>(null);
  const [activity, setActivity] = useState<RecentActivityItem[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(true);
  const [loadingActivity, setLoadingActivity] = useState(true);

  const fetchData = useCallback(() => {
    api.repositories.list().then(setRepos).catch(() => {}).finally(() => setLoadingRepos(false));
    api.auth.me().then(setUser).catch(() => {});
    api.dashboard.stats().then(setStats).catch(() => {});
    api.dashboard.riskDistribution().then(setDistro).catch(() => {});
    api.dashboard.recentActivity(10).then((r) => setActivity(r.items)).catch(() => {}).finally(() => setLoadingActivity(false));
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 30_000);
    return () => clearInterval(id);
  }, [fetchData]);

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
        <a href="/repositories" className="btn-primary text-xs px-3 py-1.5">
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
            value={stats?.total_assessments ?? "—"}
            sub={stats?.recent_commits_24h ? `${stats.recent_commits_24h} in last 24h` : "total assessments"}
            accentColor="#a78bfa"
            trend={stats && stats.total_commits > 0 ? `${stats.total_commits} total commits` : undefined}
          />
          <StatCard
            label="High Risk Commits"
            value={stats?.high_risk_count ?? "—"}
            sub={stats?.recent_high_risk_24h ? `${stats.recent_high_risk_24h} in last 24h` : "identified as HIGH"}
            accentColor="#ef4444"
            icon={
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8.22 1.754a.25.25 0 0 0-.44 0L1.698 13.132a.25.25 0 0 0 .22.368h12.164a.25.25 0 0 0 .22-.368Zm-1.763-.707c.659-1.234 2.427-1.234 3.086 0l6.082 11.378A1.75 1.75 0 0 1 14.082 15H1.918a1.75 1.75 0 0 1-1.543-2.575ZM9 11a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm-.25-5.25a.75.75 0 0 0-1.5 0v2.5a.75.75 0 0 0 1.5 0v-2.5Z" />
              </svg>
            }
          />
          <StatCard
            label="Avg Risk Score"
            value={stats?.avg_risk_score != null ? stats.avg_risk_score.toFixed(1) : "—"}
            sub={
              stats?.avg_risk_score != null
                ? stats.avg_risk_score < 30 ? "Overall: Low risk" : stats.avg_risk_score < 60 ? "Overall: Moderate risk" : "Overall: High risk"
                : "no assessments yet"
            }
            accentColor={
              stats?.avg_risk_score != null
                ? stats.avg_risk_score < 30 ? "#22c55e" : stats.avg_risk_score < 60 ? "#f59e0b" : "#ef4444"
                : "#f59e0b"
            }
          />
        </div>

        {/* Risk level category summary */}
        {stats && stats.total_assessments > 0 && (
          <div className="grid grid-cols-3 gap-4">
            {(["LOW", "MEDIUM", "HIGH"] as const).map((level) => {
              const count = stats.risk_counts[level];
              const pct = stats.total_assessments ? ((count / stats.total_assessments) * 100).toFixed(1) : "0";
              return (
                <div key={level} className="card p-4 flex items-center gap-4" style={{ borderLeftWidth: 3, borderLeftColor: RISK_COLORS[level] }}>
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold"
                    style={{ background: `${RISK_COLORS[level]}15`, color: RISK_COLORS[level] }}
                  >
                    {count}
                  </div>
                  <div>
                    <div className="text-xs font-semibold" style={{ color: RISK_COLORS[level] }}>{level} RISK</div>
                    <div className="text-[11px]" style={{ color: "var(--text-muted)" }}>{pct}% of total</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Left 2/3 */}
          <div className="lg:col-span-2 space-y-5">
            <PipelineFlow />
            <RecentActivity items={activity} loading={loadingActivity} />
          </div>

          {/* Right 1/3 */}
          <div className="space-y-5">
            <RiskDistributionChart data={distro} />
            <ScoreHistogramChart data={distro} />
            <SystemHealthWidget />
          </div>
        </div>
      </main>
    </div>
  );
}
