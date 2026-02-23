import RiskBadge from "@/components/RiskBadge";
import type { RiskLevel } from "@/lib/api";

// ---------------------------------------------------------------------------
// Static placeholder data — will be replaced by live API calls once
// the ML pipeline and webhook data population are complete.
// ---------------------------------------------------------------------------
const placeholderAssessments = [
  {
    id: 1,
    sha: "a3f2c1d",
    repo: "owner/api-service",
    message: "fix: urgent hotfix for auth bypass",
    risk_level: "HIGH" as RiskLevel,
    risk_score: 82,
    confidence: 0.91,
    model_version: "rule-v1",
    lines_changed: 847,
    files_changed: 14,
    created_at: "2026-02-23T10:15:00Z",
  },
  {
    id: 2,
    sha: "b7e8912",
    repo: "owner/frontend-app",
    message: "feat: add user profile dashboard",
    risk_level: "MEDIUM" as RiskLevel,
    risk_score: 45,
    confidence: 0.78,
    model_version: "rule-v1",
    lines_changed: 312,
    files_changed: 8,
    created_at: "2026-02-23T09:40:00Z",
  },
  {
    id: 3,
    sha: "c1d4567",
    repo: "owner/data-pipeline",
    message: "chore: update dependencies",
    risk_level: "LOW" as RiskLevel,
    risk_score: 12,
    confidence: 0.95,
    model_version: "rule-v1",
    lines_changed: 28,
    files_changed: 2,
    created_at: "2026-02-23T08:55:00Z",
  },
  {
    id: 4,
    sha: "d9a0b3e",
    repo: "owner/api-service",
    message: "docs: update README and contributing guide",
    risk_level: "LOW" as RiskLevel,
    risk_score: 5,
    confidence: 0.97,
    model_version: "rule-v1",
    lines_changed: 60,
    files_changed: 3,
    created_at: "2026-02-23T07:30:00Z",
  },
];

// ---------------------------------------------------------------------------
// Risk distribution metrics
// ---------------------------------------------------------------------------
function RiskMeter({ score }: { score: number }) {
  const color = score >= 60 ? "#f85149" : score >= 30 ? "#d29922" : "#3fb950";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--border)" }}>
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="text-xs font-mono font-semibold w-8 text-right" style={{ color }}>
        {score}%
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ML Model Status Card
// ---------------------------------------------------------------------------
function ModelStatusCard() {
  const features = [
    { name: "Lines changed", ready: true },
    { name: "Files modified", ready: true },
    { name: "Commit message analysis", ready: true },
    { name: "Code complexity (AST)", ready: false },
    { name: "Historical bug correlation", ready: false },
    { name: "PR review patterns", ready: false },
    { name: "Developer burnout signals", ready: false },
  ];

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>ML Model Status</div>
        <span
          className="badge"
          style={{ background: "#d2992218", color: "#d29922", borderColor: "#d2992240" }}
        >
          Rule-based MVP
        </span>
      </div>
      <div className="space-y-2 mb-4">
        {features.map((f) => (
          <div key={f.name} className="flex items-center gap-2 text-xs">
            <span style={{ color: f.ready ? "#3fb950" : "var(--border)" }}>{f.ready ? "✓" : "○"}</span>
            <span style={{ color: f.ready ? "var(--foreground)" : "var(--text-muted)" }}>{f.name}</span>
            {!f.ready && (
              <span
                className="ml-auto text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded"
                style={{ background: "var(--surface-raised)", color: "var(--text-muted)", border: "1px solid var(--border-subtle)" }}
              >
                Roadmap
              </span>
            )}
          </div>
        ))}
      </div>
      <div
        className="text-[11px] pt-3"
        style={{ borderTop: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}
      >
        scikit-learn Logistic Regression model planned for milestone 2.
        Current scoring uses rule-based heuristics with 75% fixed confidence.
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function PredictionsPage() {
  const high = placeholderAssessments.filter((a) => a.risk_level === "HIGH").length;
  const medium = placeholderAssessments.filter((a) => a.risk_level === "MEDIUM").length;
  const low = placeholderAssessments.filter((a) => a.risk_level === "LOW").length;
  const avg =
    Math.round(
      placeholderAssessments.reduce((s, a) => s + a.risk_score, 0) /
        placeholderAssessments.length
    );

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <div>
          <h1 className="text-base font-semibold" style={{ color: "var(--foreground)" }}>
            Risk Predictions
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            Deployment risk scoring per commit — rule-based MVP, ML model coming next
          </p>
        </div>
        <span
          className="badge"
          style={{ background: "#d2992218", color: "#d29922", borderColor: "#d2992240" }}
        >
          Demo Data
        </span>
      </header>

      <main className="flex-1 p-6 space-y-6">
        {/* Summary row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "High Risk", value: high, color: "#f85149" },
            { label: "Medium Risk", value: medium, color: "#d29922" },
            { label: "Low Risk", value: low, color: "#3fb950" },
            { label: "Avg Score", value: `${avg}%`, color: "var(--foreground)" },
          ].map((s) => (
            <div key={s.label} className="card p-4">
              <div className="text-xs uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>
                {s.label}
              </div>
              <div className="text-3xl font-bold" style={{ color: s.color }}>
                {s.value}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Assessments table */}
          <div className="lg:col-span-2">
            <div className="card overflow-hidden">
              <div
                className="flex items-center justify-between px-4 py-3 border-b"
                style={{ borderColor: "var(--border-subtle)" }}
              >
                <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
                  Recent Risk Assessments
                </div>
              </div>
              <div className="divide-y" style={{ borderColor: "var(--border-subtle)" }}>
                {placeholderAssessments.map((a) => (
                  <div key={a.id} className="px-4 py-3.5 text-sm">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <code
                            className="font-mono text-xs px-1.5 py-0.5 rounded"
                            style={{ background: "var(--surface-raised)", color: "var(--accent-hover)" }}
                          >
                            {a.sha}
                          </code>
                          <span className="text-xs" style={{ color: "var(--text-muted)" }}>{a.repo}</span>
                        </div>
                        <div className="truncate text-xs" style={{ color: "var(--foreground)" }}>
                          {a.message}
                        </div>
                        <div className="flex gap-3 mt-1.5 text-xs" style={{ color: "var(--text-muted)" }}>
                          <span>±{a.lines_changed} lines</span>
                          <span>{a.files_changed} files</span>
                          <span>conf. {(a.confidence * 100).toFixed(0)}%</span>
                          <span>{new Date(a.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                      <div className="flex-shrink-0 w-32">
                        <RiskBadge level={a.risk_level} score={a.risk_score} />
                        <div className="mt-2">
                          <RiskMeter score={a.risk_score} />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            <ModelStatusCard />
            <div className="card p-5">
              <div className="text-sm font-semibold mb-3" style={{ color: "var(--foreground)" }}>
                How Scoring Works
              </div>
              <div className="space-y-2.5 text-xs" style={{ color: "var(--text-muted)" }}>
                <div className="flex justify-between">
                  <span>Lines changed &gt; 500</span>
                  <span className="font-mono" style={{ color: "var(--foreground)" }}>+40 pts</span>
                </div>
                <div className="flex justify-between">
                  <span>Lines changed &gt; 200</span>
                  <span className="font-mono" style={{ color: "var(--foreground)" }}>+25 pts</span>
                </div>
                <div className="flex justify-between">
                  <span>Files &gt; 20</span>
                  <span className="font-mono" style={{ color: "var(--foreground)" }}>+30 pts</span>
                </div>
                <div className="flex justify-between">
                  <span>Risky keywords</span>
                  <span className="font-mono" style={{ color: "var(--foreground)" }}>+15 pts</span>
                </div>
                <div
                  className="pt-2 border-t"
                  style={{ borderColor: "var(--border-subtle)" }}
                >
                  <div className="flex justify-between mb-1">
                    <span style={{ color: "#3fb950" }}>LOW</span>
                    <span className="font-mono">0 – 29</span>
                  </div>
                  <div className="flex justify-between mb-1">
                    <span style={{ color: "#d29922" }}>MEDIUM</span>
                    <span className="font-mono">30 – 59</span>
                  </div>
                  <div className="flex justify-between">
                    <span style={{ color: "#f85149" }}>HIGH</span>
                    <span className="font-mono">60 – 100</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
