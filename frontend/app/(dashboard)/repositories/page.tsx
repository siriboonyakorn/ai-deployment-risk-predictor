"use client";

import { useEffect, useRef, useState } from "react";
import { api, Repository, RepoImportResponse } from "@/lib/api";

// ---------------------------------------------------------------------------
// Import Modal
// ---------------------------------------------------------------------------
function ImportModal({
  onClose,
  onImported,
}: {
  onClose: () => void;
  onImported: (r: Repository) => void;
}) {
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RepoImportResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.repositories.import(url.trim(), branch.trim() || undefined);
      setResult(res);
      onImported(res.repository);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.6)" }}
      onClick={(e) => e.target === e.currentTarget && !result && onClose()}
    >
      <div className="card w-full max-w-lg" style={{ background: "var(--surface)" }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: "var(--border-subtle)" }}>
          <div>
            <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
              Import GitHub Repository
            </div>
            <div className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
              Paste any public GitHub repo URL
            </div>
          </div>
          <button onClick={onClose} className="text-lg leading-none hover:opacity-70" style={{ color: "var(--text-muted)" }}>
            ×
          </button>
        </div>

        {/* Body */}
        <div className="p-5">
          {result ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm" style={{ color: "#3fb950" }}>
                <span className="w-4 h-4 rounded-full flex items-center justify-center text-xs" style={{ background: "#3fb95020", border: "1px solid #3fb95040" }}>✓</span>
                Repository imported successfully
              </div>
              <div className="card p-4 space-y-2 text-sm" style={{ background: "var(--surface-raised)" }}>
                <div className="font-semibold" style={{ color: "var(--foreground)" }}>{result.metadata.full_name}</div>
                {result.metadata.description && (
                  <div className="text-xs" style={{ color: "var(--text-muted)" }}>{result.metadata.description}</div>
                )}
                <div className="flex gap-4 text-xs pt-1" style={{ color: "var(--text-muted)" }}>
                  <span>⭐ {result.metadata.stars.toLocaleString()}</span>
                  <span>🔀 {result.metadata.forks.toLocaleString()}</span>
                  {result.metadata.language && <span>💻 {result.metadata.language}</span>}
                  <span>🌿 {result.metadata.default_branch}</span>
                </div>
                <div className="text-xs pt-1" style={{ color: "var(--text-muted)" }}>
                  Fetched <strong style={{ color: "var(--foreground)" }}>{result.commits_fetched}</strong> recent commits
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={onClose}
                  className="flex-1 py-2 rounded-md text-sm font-medium"
                  style={{ background: "var(--accent)", color: "white" }}
                >
                  Done
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>
                  GitHub Repository URL *
                </label>
                <input
                  ref={inputRef}
                  type="url"
                  placeholder="https://github.com/owner/repo"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-md text-sm font-mono outline-none"
                  style={{
                    background: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                    color: "var(--foreground)",
                  }}
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>
                  Branch (optional)
                </label>
                <input
                  type="text"
                  placeholder="main"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  className="w-full px-3 py-2 rounded-md text-sm font-mono outline-none"
                  style={{
                    background: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                    color: "var(--foreground)",
                  }}
                />
              </div>
              {error && (
                <div className="text-xs px-3 py-2 rounded-md" style={{ background: "#f8514918", color: "#f85149", border: "1px solid #f8514930" }}>
                  {error}
                </div>
              )}
              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 py-2 rounded-md text-sm font-medium"
                  style={{ background: "var(--surface-raised)", color: "var(--text-muted)", border: "1px solid var(--border)" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !url.trim()}
                  className="flex-1 py-2 rounded-md text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: "var(--accent)", color: "white" }}
                >
                  {loading ? "Importing…" : "Import Repository"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Repo Row
// ---------------------------------------------------------------------------
function RepoRow({
  repo,
  onDelete,
}: {
  repo: Repository;
  onDelete: (id: number) => void;
}) {
  const [deleting, setDeleting] = useState(false);
  const [confirm, setConfirm] = useState(false);

  const handleDelete = async () => {
    if (!confirm) { setConfirm(true); return; }
    setDeleting(true);
    try {
      await api.repositories.delete(repo.id);
      onDelete(repo.id);
    } catch {
      setDeleting(false);
      setConfirm(false);
    }
  };

  return (
    <div
      className="flex items-center gap-4 px-4 py-3.5 rounded-md text-sm"
      style={{ background: "var(--surface)" }}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium" style={{ color: "var(--foreground)" }}>
            {repo.full_name}
          </span>
          {repo.is_private && (
            <span className="badge" style={{ color: "var(--text-muted)", borderColor: "var(--border)", background: "var(--surface-raised)", fontSize: "9px" }}>
              Private
            </span>
          )}
          <span
            className="flex items-center gap-1 text-[10px]"
            style={{ color: repo.webhook_active ? "#3fb950" : "var(--text-muted)" }}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${repo.webhook_active ? "bg-[#3fb950]" : "bg-gray-600"}`} />
            {repo.webhook_active ? "Webhook active" : "Webhook inactive"}
          </span>
        </div>
        <div className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
          Added {new Date(repo.created_at).toLocaleDateString()}
        </div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <a
          href={`/commits?repo=${repo.id}`}
          className="px-3 py-1.5 rounded-md text-xs font-medium transition-opacity hover:opacity-80"
          style={{ background: "var(--surface-raised)", color: "var(--text-muted)", border: "1px solid var(--border)" }}
        >
          View Commits
        </a>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="px-3 py-1.5 rounded-md text-xs font-medium transition-opacity hover:opacity-80 disabled:opacity-40"
          style={
            confirm
              ? { background: "#f851491a", color: "#f85149", border: "1px solid #f8514940" }
              : { background: "var(--surface-raised)", color: "var(--text-muted)", border: "1px solid var(--border)" }
          }
        >
          {deleting ? "Removing…" : confirm ? "Confirm?" : "Remove"}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function RepositoriesPage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    api.repositories
      .list()
      .then(setRepos)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleImported = (repo: Repository) => {
    setRepos((prev) => {
      if (prev.find((r) => r.id === repo.id)) return prev;
      return [repo, ...prev];
    });
  };

  const handleDelete = (id: number) =>
    setRepos((prev) => prev.filter((r) => r.id !== id));

  return (
    <>
      {showModal && (
        <ImportModal
          onClose={() => setShowModal(false)}
          onImported={(r) => { handleImported(r); }}
        />
      )}

      <div className="flex flex-col min-h-screen">
        {/* Header */}
        <header
          className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <div>
            <h1 className="text-base font-semibold" style={{ color: "var(--foreground)" }}>
              Repositories
            </h1>
            <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
              {repos.length} connected — import a GitHub repo to start analysing risk
            </p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-opacity hover:opacity-80"
            style={{ background: "var(--accent)", color: "white" }}
          >
            + Import Repository
          </button>
        </header>

        {/* Body */}
        <main className="flex-1 p-6">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="card h-16 animate-pulse" style={{ background: "var(--surface)" }} />
              ))}
            </div>
          ) : repos.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 gap-4">
              <svg width="48" height="48" viewBox="0 0 16 16" fill="var(--border)">
                <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8Z" />
              </svg>
              <div className="text-center">
                <div className="text-sm font-medium mb-1" style={{ color: "var(--foreground)" }}>No repositories yet</div>
                <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                  Import a GitHub repository to start tracking deployment risk
                </div>
              </div>
              <button
                onClick={() => setShowModal(true)}
                className="px-4 py-2 rounded-md text-sm font-medium"
                style={{ background: "var(--accent)", color: "white" }}
              >
                Import your first repository
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {repos.map((repo) => (
                <RepoRow key={repo.id} repo={repo} onDelete={handleDelete} />
              ))}
            </div>
          )}
        </main>
      </div>
    </>
  );
}
