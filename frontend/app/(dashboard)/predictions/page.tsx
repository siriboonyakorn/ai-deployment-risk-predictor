"use client";

import { useEffect, useState } from "react";
import {
  api,
  Repository,
  GitHubCommitItem,
  RiskPredictionResponse,
  RiskPredictionRequest,
} from "@/lib/api";
import RiskBadge from "@/components/RiskBadge";

interface HistoryEntry {
  sha: string;
  repoName: string;
  message: string;
  result: RiskPredictionResponse;
  analyzedAt: string;
}

function RiskMeter({ score, level }: { score: number; level: string }) {
  const color =
    level === "HIGH"
      ? "var(--risk-high)"
      : level === "MEDIUM"
      ? "var(--risk-medium)"
      : "var(--risk-low)";

  return (
    <div className="space-y-2">
      <div className="flex items-end justify-between">
        <span className="text-4xl font-bold" style={{ color }}>
          {score}
        </span>
        <span className="text-sm mb-1" style={{ color: "var(--text-muted)" }}>
          / 100
        </span>
      </div>
      <div
        className="h-2.5 rounded-full overflow-hidden"
        style={{ background: "var(--border)" }}
      >
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${score}%`, background: color }}
        />
      </div>
      <div className="text-xs" style={{ color: "var(--text-muted)" }}>
        {score < 30
          ? "Low risk — safe to deploy"
          : score < 60
          ? "Moderate risk — review before deploying"
          : "High risk — requires thorough review"}
      </div>
    </div>
  );
}

function ResultCard({ result }: { result: RiskPredictionResponse }) {
  const { commit, assessment } = result;
  return (
    <div
      className="rounded-xl p-5 space-y-4 animate-fade-up"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div
            className="text-xs font-mono mb-1"
            style={{ color: "var(--text-muted)" }}
          >
            {commit.sha.slice(0, 7)}
          </div>
          <div
            className="text-sm font-medium truncate"
            style={{ color: "var(--foreground)" }}
          >
            {commit.message ?? "(no message)"}
          </div>
        </div>
        <RiskBadge level={assessment.risk_level} />
      </div>

      <RiskMeter score={assessment.risk_score} level={assessment.risk_level} />

      <div className="grid grid-cols-3 gap-3 pt-1">
        {[
          {
            label: "Confidence",
            value:
              assessment.confidence != null
                ? `${Math.round(assessment.confidence * 100)}%`
                : "—",
          },
          { label: "Lines +", value: commit.lines_added },
          { label: "Lines −", value: commit.lines_deleted },
        ].map(({ label, value }) => (
          <div
            key={label}
            className="rounded-lg p-3 text-center"
            style={{ background: "var(--surface-raised)" }}
          >
            <div
              className="text-xs mb-1"
              style={{ color: "var(--text-muted)" }}
            >
              {label}
            </div>
            <div
              className="text-sm font-semibold"
              style={{ color: "var(--foreground)" }}
            >
              {String(value)}
            </div>
          </div>
        ))}
      </div>

      <div
        className="text-xs pt-1"
        style={{
          color: "var(--text-muted)",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        Model: {assessment.model_version} · Analyzed{" "}
        {new Date(assessment.created_at).toLocaleString()}
      </div>
    </div>
  );
}

function HistoryRow({
  entry,
  onSelect,
}: {
  entry: HistoryEntry;
  onSelect: (entry: HistoryEntry) => void;
}) {
  const { assessment, commit } = entry.result;
  const color =
    assessment.risk_level === "HIGH"
      ? "var(--risk-high)"
      : assessment.risk_level === "MEDIUM"
      ? "var(--risk-medium)"
      : "var(--risk-low)";

  return (
    <button
      onClick={() => onSelect(entry)}
      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all hover:brightness-110"
      style={{
        background: "var(--surface-raised)",
        border: "1px solid transparent",
      }}
    >
      <div
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ background: color }}
      />
      <div className="flex-1 min-w-0">
        <div
          className="text-xs font-mono truncate"
          style={{ color: "var(--text-muted)" }}
        >
          {commit.sha.slice(0, 7)}
        </div>
        <div
          className="text-xs truncate mt-0.5"
          style={{ color: "var(--foreground)" }}
        >
          {entry.message.split("\n")[0] || "(no message)"}
        </div>
      </div>
      <div className="text-right flex-shrink-0">
        <div className="text-sm font-semibold" style={{ color }}>
          {assessment.risk_score}
        </div>
        <div className="text-xs" style={{ color: "var(--text-muted)" }}>
          {assessment.risk_level}
        </div>
      </div>
    </button>
  );
}

export default function PredictionsPage() {
  // Form state
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState("");
  const [commits, setCommits] = useState<GitHubCommitItem[]>([]);
  const [commitsLoading, setCommitsLoading] = useState(false);
  const [selectedSha, setSelectedSha] = useState("");
  const [manualSha, setManualSha] = useState("");
  const [linesAdded, setLinesAdded] = useState("");
  const [linesDeleted, setLinesDeleted] = useState("");
  const [filesChanged, setFilesChanged] = useState("");

  // Result state
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<RiskPredictionResponse | null>(null);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  // History
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  // Load repos
  useEffect(() => {
    api.repositories.list().then(setRepos).catch(() => {});
  }, []);

  // Load commits when repo changes
  useEffect(() => {
    if (!selectedRepoId) {
      setCommits([]);
      return;
    }
    setCommitsLoading(true);
    api.repositories
      .commits(Number(selectedRepoId), 1, 50)
      .then((r) => setCommits(r.commits))
      .catch(() => setCommits([]))
      .finally(() => setCommitsLoading(false));
  }, [selectedRepoId]);

  const selectedRepo = repos.find((r) => String(r.id) === selectedRepoId);
  const effectiveSha = manualSha.trim() || selectedSha;
  const selectedCommit = commits.find((c) => c.sha === selectedSha);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!effectiveSha || !selectedRepo) return;

    setAnalyzing(true);
    setAnalyzeError(null);
    setResult(null);

    const payload: RiskPredictionRequest = {
      sha: effectiveSha,
      repository_full_name: selectedRepo.full_name,
      commit_message: selectedCommit?.commit.message ?? undefined,
      author_email: selectedCommit?.commit.author?.email ?? undefined,
      lines_added: linesAdded ? Number(linesAdded) : 0,
      lines_deleted: linesDeleted ? Number(linesDeleted) : 0,
      files_changed: filesChanged ? Number(filesChanged) : 0,
    };

    try {
      const res = await api.predictions.create(payload);
      setResult(res);
      const entry: HistoryEntry = {
        sha: effectiveSha,
        repoName: selectedRepo.full_name,
        message: selectedCommit?.commit.message ?? manualSha,
        result: res,
        analyzedAt: new Date().toISOString(),
      };
      setHistory((prev) => [entry, ...prev.slice(0, 19)]);
    } catch (err) {
      setAnalyzeError(
        err instanceof Error ? err.message : "Analysis failed"
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const canAnalyze = !!effectiveSha && !!selectedRepo && !analyzing;

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <div>
          <h1
            className="text-base font-semibold"
            style={{ color: "var(--foreground)" }}
          >
            Risk Analysis
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            Predict deployment risk for any commit in your connected
            repositories
          </p>
        </div>
      </header>

      <main className="flex-1 p-6">
        <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* ── Left: Form ─────────────────────────────── */}
          <div
            className="rounded-xl p-5 space-y-4"
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
            }}
          >
            <div className="flex items-center gap-2 mb-1">
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="var(--accent)"
              >
                <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm4.879-2.773 4.264 2.559a.25.25 0 0 1 0 .428l-4.264 2.559A.25.25 0 0 1 6 10.559V5.442a.25.25 0 0 1 .379-.215Z" />
              </svg>
              <h2
                className="text-sm font-semibold"
                style={{ color: "var(--foreground)" }}
              >
                Analyze a Commit
              </h2>
            </div>

            <form onSubmit={handleAnalyze} className="space-y-3">
              {/* Repository selector */}
              <div className="space-y-1">
                <label
                  className="text-xs font-medium"
                  style={{ color: "var(--text-muted)" }}
                >
                  Repository
                </label>
                <select
                  value={selectedRepoId}
                  onChange={(e) => {
                    setSelectedRepoId(e.target.value);
                    setSelectedSha("");
                    setManualSha("");
                  }}
                  className="w-full px-3 py-2 rounded-lg text-sm outline-none"
                  style={{
                    background: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                    color: selectedRepoId
                      ? "var(--foreground)"
                      : "var(--text-muted)",
                  }}
                >
                  <option value="">Select a repository…</option>
                  {repos.map((r) => (
                    <option key={r.id} value={String(r.id)}>
                      {r.full_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Commit selector */}
              <div className="space-y-1">
                <label
                  className="text-xs font-medium"
                  style={{ color: "var(--text-muted)" }}
                >
                  Commit{commitsLoading ? " (loading…)" : ""}
                </label>
                <select
                  value={selectedSha}
                  onChange={(e) => {
                    setSelectedSha(e.target.value);
                    setManualSha("");
                  }}
                  disabled={!selectedRepoId || commitsLoading}
                  className="w-full px-3 py-2 rounded-lg text-sm outline-none disabled:opacity-50"
                  style={{
                    background: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                    color: selectedSha
                      ? "var(--foreground)"
                      : "var(--text-muted)",
                  }}
                >
                  <option value="">Select a commit…</option>
                  {commits.map((c) => (
                    <option key={c.sha} value={c.sha}>
                      {c.sha.slice(0, 7)} —{" "}
                      {c.commit.message.split("\n")[0].slice(0, 55)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Divider */}
              <div className="flex items-center gap-2">
                <div
                  className="flex-1 h-px"
                  style={{ background: "var(--border-subtle)" }}
                />
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  or enter SHA manually
                </span>
                <div
                  className="flex-1 h-px"
                  style={{ background: "var(--border-subtle)" }}
                />
              </div>

              {/* Manual SHA input */}
              <input
                type="text"
                value={manualSha}
                onChange={(e) => {
                  setManualSha(e.target.value);
                  setSelectedSha("");
                }}
                placeholder="Paste commit SHA (e.g. a1b2c3d…)"
                className="w-full px-3 py-2 rounded-lg text-sm font-mono outline-none"
                style={{
                  background: "var(--surface-raised)",
                  border: "1px solid var(--border)",
                  color: "var(--foreground)",
                }}
              />

              {/* Optional diff stats */}
              <div
                className="rounded-lg p-3 space-y-2"
                style={{ background: "var(--surface-raised)" }}
              >
                <div
                  className="text-xs font-medium"
                  style={{ color: "var(--text-muted)" }}
                >
                  Diff stats{" "}
                  <span style={{ fontWeight: 400 }}>
                    (optional — improves score accuracy)
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    {
                      label: "Lines added",
                      value: linesAdded,
                      onChange: setLinesAdded,
                    },
                    {
                      label: "Lines deleted",
                      value: linesDeleted,
                      onChange: setLinesDeleted,
                    },
                    {
                      label: "Files changed",
                      value: filesChanged,
                      onChange: setFilesChanged,
                    },
                  ].map(({ label, value, onChange }) => (
                    <div key={label} className="space-y-1">
                      <label
                        className="text-xs"
                        style={{ color: "var(--text-muted)" }}
                      >
                        {label}
                      </label>
                      <input
                        type="number"
                        min="0"
                        value={value}
                        onChange={(e) => onChange(e.target.value)}
                        placeholder="0"
                        className="w-full px-2 py-1.5 rounded text-sm outline-none text-center"
                        style={{
                          background: "var(--background)",
                          border: "1px solid var(--border)",
                          color: "var(--foreground)",
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Error */}
              {analyzeError && (
                <div
                  className="text-xs px-3 py-2 rounded-lg"
                  style={{
                    background: "#f851491a",
                    color: "#f85149",
                    border: "1px solid #f8514930",
                  }}
                >
                  ⚠ {analyzeError}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={!canAnalyze}
                className="btn-primary w-full py-2.5 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {analyzing ? (
                  <>
                    <svg
                      className="animate-spin"
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3"
                    >
                      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                    </svg>
                    Analyzing…
                  </>
                ) : (
                  <>
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 16 16"
                      fill="currentColor"
                    >
                      <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm4.879-2.773 4.264 2.559a.25.25 0 0 1 0 .428l-4.264 2.559A.25.25 0 0 1 6 10.559V5.442a.25.25 0 0 1 .379-.215Z" />
                    </svg>
                    Analyze Risk
                  </>
                )}
              </button>
            </form>
          </div>

          {/* ── Right: Result + History ─────────────────── */}
          <div className="space-y-4">
            {/* Result card or placeholder */}
            {result ? (
              <ResultCard result={result} />
            ) : (
              <div
                className="rounded-xl p-8 flex flex-col items-center justify-center gap-3 text-center"
                style={{
                  background: "var(--surface)",
                  border: "1px dashed var(--border)",
                  minHeight: "220px",
                }}
              >
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center"
                  style={{ background: "var(--surface-raised)" }}
                >
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 16 16"
                    fill="var(--border)"
                  >
                    <path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Zm4.879-2.773 4.264 2.559a.25.25 0 0 1 0 .428l-4.264 2.559A.25.25 0 0 1 6 10.559V5.442a.25.25 0 0 1 .379-.215Z" />
                  </svg>
                </div>
                <div
                  className="text-sm font-medium"
                  style={{ color: "var(--text-muted)" }}
                >
                  No analysis yet
                </div>
                <div
                  className="text-xs max-w-xs"
                  style={{ color: "var(--text-muted)" }}
                >
                  Select a repository and commit on the left, then click{" "}
                  <strong style={{ color: "var(--foreground)" }}>
                    Analyze Risk
                  </strong>{" "}
                  to get an AI-powered deployment risk assessment.
                </div>
              </div>
            )}

            {/* Session history */}
            {history.length > 0 && (
              <div
                className="rounded-xl p-4 space-y-2"
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <h3
                    className="text-xs font-semibold uppercase tracking-widest"
                    style={{ color: "var(--text-muted)" }}
                  >
                    Session History
                  </h3>
                  <span className="badge text-xs">{history.length}</span>
                </div>
                <div className="space-y-1 max-h-72 overflow-y-auto">
                  {history.map((entry, idx) => (
                    <HistoryRow
                      key={`${entry.sha}-${idx}`}
                      entry={entry}
                      onSelect={(e) => setResult(e.result)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
