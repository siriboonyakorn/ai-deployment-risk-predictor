"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  api,
  CommitHistoryResponse,
  GitHubCommitItem,
  Repository,
  RiskPredictionResponse,
} from "@/lib/api";
import RiskBadge from "@/components/RiskBadge";

function CommitRow({
  commit,
  repoFullName,
}: {
  commit: GitHubCommitItem;
  repoFullName: string;
}) {
  const author = commit.commit.author;
  const date = author?.date ? new Date(author.date).toLocaleString() : "—";
  const firstLine = commit.commit.message.split("\n")[0];
  const rest = commit.commit.message.split("\n").slice(1).join("\n").trim();

  const [predicting, setPredicting] = useState(false);
  const [result, setResult] = useState<RiskPredictionResponse | null>(null);
  const [predError, setPredError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setPredicting(true);
    setPredError(null);
    try {
      const res = await api.predictions.create({
        sha: commit.sha,
        repository_full_name: repoFullName,
        commit_message: commit.commit.message,
        author_email: commit.commit.author?.email ?? undefined,
      });
      setResult(res);
    } catch (err) {
      setPredError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setPredicting(false);
    }
  };

  return (
    <div
      className="rounded-md transition-all"
      style={{ background: "var(--surface)", border: "1px solid transparent" }}
    >
      <div className="flex items-start gap-3 px-4 py-3.5 text-sm">
        {/* Commit icon */}
        <div className="flex-shrink-0 mt-0.5">
          <div
            className="w-6 h-6 rounded-full flex items-center justify-center"
            style={{
              background: "var(--surface-raised)",
              border: "1px solid var(--border)",
            }}
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 16 16"
              fill="var(--text-muted)"
            >
              <path d="M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z" />
            </svg>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div
            className="font-medium truncate"
            style={{ color: "var(--foreground)" }}
          >
            {firstLine}
          </div>
          {rest && (
            <div
              className="text-xs mt-0.5 truncate"
              style={{ color: "var(--text-muted)" }}
            >
              {rest}
            </div>
          )}
          <div
            className="flex items-center gap-3 mt-1 text-xs"
            style={{ color: "var(--text-muted)" }}
          >
            {author?.name && <span>{author.name}</span>}
            <span>{date}</span>
          </div>
        </div>

        {/* SHA + actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Risk badge if analyzed */}
          {result && (
            <RiskBadge level={result.assessment.risk_level} />
          )}

          {/* Analyze button */}
          {!result && (
            <button
              onClick={handleAnalyze}
              disabled={predicting}
              className="px-2.5 py-1 rounded-md text-xs font-medium transition-all disabled:opacity-50"
              style={{
                background: predicting
                  ? "var(--surface-raised)"
                  : "color-mix(in srgb, var(--accent) 15%, transparent)",
                color: "var(--accent)",
                border: "1px solid color-mix(in srgb, var(--accent) 30%, transparent)",
              }}
            >
              {predicting ? (
                <span className="flex items-center gap-1.5">
                  <svg
                    className="animate-spin"
                    width="10"
                    height="10"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                  >
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                  </svg>
                  Analyzing…
                </span>
              ) : (
                "Analyze Risk"
              )}
            </button>
          )}

          {/* Re-analyze button if already done */}
          {result && (
            <button
              onClick={handleAnalyze}
              disabled={predicting}
              className="px-2 py-1 rounded-md text-xs opacity-50 hover:opacity-80 transition-opacity disabled:opacity-30"
              style={{
                background: "var(--surface-raised)",
                color: "var(--text-muted)",
                border: "1px solid var(--border)",
              }}
            >
              ↻
            </button>
          )}

          <a
            href={commit.html_url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-xs px-2.5 py-1 rounded-md transition-opacity hover:opacity-80"
            style={{
              background: "var(--surface-raised)",
              color: "var(--accent-hover)",
              border: "1px solid var(--border)",
            }}
            title={commit.sha}
          >
            {commit.sha.slice(0, 7)} ↗
          </a>
        </div>
      </div>

      {/* Inline result row */}
      {(result || predError) && (
        <div
          className="px-4 pb-3 pt-0 text-xs"
          style={{ borderTop: "1px solid var(--border-subtle)" }}
        >
          {predError && (
            <span style={{ color: "var(--risk-high)" }}>⚠ {predError}</span>
          )}
          {result && (
            <div className="flex items-center gap-4 flex-wrap pt-2">
              <span style={{ color: "var(--text-muted)" }}>
                Risk Score:{" "}
                <strong style={{ color: "var(--foreground)" }}>
                  {result.assessment.risk_score}
                </strong>
                /100
              </span>
              <span style={{ color: "var(--text-muted)" }}>
                Confidence:{" "}
                <strong style={{ color: "var(--foreground)" }}>
                  {result.assessment.confidence != null
                    ? `${Math.round(result.assessment.confidence * 100)}%`
                    : "—"}
                </strong>
              </span>
              <div
                className="flex-1 h-1.5 rounded-full overflow-hidden"
                style={{
                  background: "var(--border)",
                  minWidth: "80px",
                  maxWidth: "160px",
                }}
              >
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${result.assessment.risk_score}%`,
                    background:
                      result.assessment.risk_level === "HIGH"
                        ? "var(--risk-high)"
                        : result.assessment.risk_level === "MEDIUM"
                        ? "var(--risk-medium)"
                        : "var(--risk-low)",
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function CommitsPage() {
  const searchParams = useSearchParams();
  const preselectedRepoId = searchParams.get("repo");

  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedId, setSelectedId] = useState<string>(preselectedRepoId ?? "");
  const [branch, setBranch] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<CommitHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load repo list
  useEffect(() => {
    api.repositories.list().then(setRepos).catch(() => {});
  }, []);

  // Auto-load when repo is pre-selected
  useEffect(() => {
    if (preselectedRepoId) {
      setSelectedId(preselectedRepoId);
    }
  }, [preselectedRepoId]);

  const fetchCommits = async (repoId: string, pg: number) => {
    if (!repoId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.repositories.commits(
        Number(repoId),
        pg,
        30,
        branch || undefined
      );
      setData(res);
      setPage(pg);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load commits");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchCommits(selectedId, 1);
  };

  useEffect(() => {
    if (selectedId) fetchCommits(selectedId, 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

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
            Commit History
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            Browse commits and analyze deployment risk per commit
          </p>
        </div>
      </header>

      {/* Filter bar */}
      <div
        className="flex items-center gap-3 px-6 py-3 border-b flex-shrink-0"
        style={{
          borderColor: "var(--border-subtle)",
          background: "var(--surface)",
        }}
      >
        <form
          onSubmit={handleSearch}
          className="flex items-center gap-3 flex-1 flex-wrap"
        >
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="px-3 py-1.5 rounded-md text-sm outline-none"
            style={{
              background: "var(--surface-raised)",
              border: "1px solid var(--border)",
              color: selectedId ? "var(--foreground)" : "var(--text-muted)",
            }}
          >
            <option value="">Select a repository…</option>
            {repos.map((r) => (
              <option key={r.id} value={String(r.id)}>
                {r.full_name}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Branch (default)"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            className="px-3 py-1.5 rounded-md text-sm font-mono outline-none w-40"
            style={{
              background: "var(--surface-raised)",
              border: "1px solid var(--border)",
              color: "var(--foreground)",
            }}
          />
          <button
            type="submit"
            disabled={!selectedId || loading}
            className="px-3 py-1.5 rounded-md text-sm font-medium disabled:opacity-50"
            style={{ background: "var(--accent)", color: "white" }}
          >
            {loading ? "Loading…" : "Fetch"}
          </button>
        </form>

        {data && (
          <div
            className="text-xs flex-shrink-0"
            style={{ color: "var(--text-muted)" }}
          >
            {data.commits_fetched} commits · page {page}
          </div>
        )}
      </div>

      {/* Body */}
      <main className="flex-1 p-6">
        {!selectedId ? (
          <div className="flex flex-col items-center justify-center h-64 gap-3">
            <svg
              width="40"
              height="40"
              viewBox="0 0 16 16"
              fill="var(--border)"
            >
              <path d="M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z" />
            </svg>
            <div
              className="text-sm text-center"
              style={{ color: "var(--text-muted)" }}
            >
              Select a repository above to browse its commit history
            </div>
          </div>
        ) : error ? (
          <div
            className="max-w-lg mx-auto text-sm px-4 py-3 rounded-md"
            style={{
              background: "#f851491a",
              color: "#f85149",
              border: "1px solid #f8514930",
            }}
          >
            {error}
          </div>
        ) : loading ? (
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="card h-16 animate-pulse"
                style={{ background: "var(--surface)" }}
              />
            ))}
          </div>
        ) : data && data.commits.length === 0 ? (
          <div
            className="text-sm text-center py-16"
            style={{ color: "var(--text-muted)" }}
          >
            No commits found for this branch.
          </div>
        ) : data ? (
          <div className="space-y-1.5 max-w-4xl">
            {data.commits.map((c) => (
              <CommitRow
                key={c.sha}
                commit={c}
                repoFullName={data.full_name}
              />
            ))}

            {/* Pagination */}
            <div className="flex justify-center gap-3 pt-4">
              <button
                disabled={page <= 1 || loading}
                onClick={() => fetchCommits(selectedId, page - 1)}
                className="px-4 py-2 rounded-md text-sm font-medium disabled:opacity-40"
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  color: "var(--foreground)",
                }}
              >
                ← Previous
              </button>
              <button
                disabled={data.commits_fetched < 30 || loading}
                onClick={() => fetchCommits(selectedId, page + 1)}
                className="px-4 py-2 rounded-md text-sm font-medium disabled:opacity-40"
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  color: "var(--foreground)",
                }}
              >
                Next →
              </button>
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
