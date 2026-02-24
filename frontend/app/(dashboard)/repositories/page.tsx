"use client";

import { useEffect, useRef, useState } from "react";
import { api, GitHubUserRepo, Repository, RepoImportResponse } from "@/lib/api";

// ---------------------------------------------------------------------------
// Language colors (subset of GitHub language colors)
// ---------------------------------------------------------------------------
const LANG_COLORS: Record<string, string> = {
  TypeScript: "#3178c6", JavaScript: "#f1e05a", Python: "#3572A5",
  Go: "#00ADD8", Rust: "#dea584", Java: "#b07219", "C++": "#f34b7d",
  C: "#555555", "C#": "#178600", Ruby: "#701516", PHP: "#4F5D95",
  Swift: "#ffac45", Kotlin: "#A97BFF", Dart: "#00B4AB", Shell: "#89e051",
  HTML: "#e34c26", CSS: "#563d7c", Vue: "#41b883", Svelte: "#ff3e00",
  Elixir: "#6e4a7e", Haskell: "#5e5086",
};

function LangDot({ lang }: { lang: string | null }) {
  if (!lang) return null;
  const color = LANG_COLORS[lang] ?? "#8b949e";
  return (
    <span className="flex items-center gap-1.5 text-xs" style={{ color: "var(--text-muted)" }}>
      <span className="lang-dot" style={{ background: color }} />
      {lang}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Tabbed Import Modal
// ---------------------------------------------------------------------------
type ModalTab = "browse" | "url";

function ImportModal({
  onClose,
  onImported,
}: {
  onClose: () => void;
  onImported: (r: Repository) => void;
}) {
  const [tab, setTab] = useState<ModalTab>("browse");
  const [result, setResult] = useState<RepoImportResponse | null>(null);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }}
      onClick={(e) => e.target === e.currentTarget && !result && onClose()}
    >
      <div
        className="w-full max-w-2xl flex flex-col rounded-2xl overflow-hidden animate-fade-up"
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          maxHeight: "85vh",
          boxShadow: "0 24px 80px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.03) inset",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <div>
            <div className="text-sm font-bold" style={{ color: "var(--foreground)" }}>
              Add Repository
            </div>
            <div className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
              Browse your GitHub repos or import by URL
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg transition-colors"
            style={{ color: "var(--text-muted)", background: "var(--surface-raised)" }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.color = "var(--foreground)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.color = "var(--text-muted)";
            }}
          >
            <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
              <path d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.75.75 0 1 1 1.06 1.06L9.06 8l3.22 3.22a.75.75 0 1 1-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06Z" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        {!result && (
          <div
            className="flex gap-1 px-4 pt-3 pb-2 flex-shrink-0 border-b"
            style={{ borderColor: "var(--border-subtle)" }}
          >
            {([
              { id: "browse" as ModalTab, label: "Browse my repos" },
              { id: "url" as ModalTab, label: "Import by URL" },
            ] as { id: ModalTab; label: string }[]).map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className="px-3 py-1.5 rounded-md text-xs font-semibold transition-colors cursor-pointer"
                style={{
                  background: tab === t.id ? "var(--surface-raised)" : "transparent",
                  color: tab === t.id ? "var(--foreground)" : "var(--text-muted)",
                  border: tab === t.id ? "1px solid var(--border)" : "1px solid transparent",
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-hidden">
          {result ? (
            <SuccessView result={result} onClose={onClose} />
          ) : tab === "browse" ? (
            <BrowseTab onImported={(r, resp) => { onImported(r); setResult(resp); }} />
          ) : (
            <UrlTab onImported={(r, resp) => { onImported(r); setResult(resp); }} />
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Success view
// ---------------------------------------------------------------------------
function SuccessView({
  result,
  onClose,
}: {
  result: RepoImportResponse;
  onClose: () => void;
}) {
  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: "#22c55e" }}>
        <span
          className="w-5 h-5 rounded-full flex items-center justify-center text-[11px]"
          style={{ background: "rgba(34,197,94,0.15)", border: "1px solid rgba(34,197,94,0.3)" }}
        >
          ✓
        </span>
        Repository added successfully
      </div>
      <div
        className="card-elevated p-4 space-y-3"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="font-bold text-sm" style={{ color: "var(--foreground)" }}>
              {result.metadata.full_name}
            </div>
            {result.metadata.description && (
              <div className="text-xs mt-1 leading-relaxed" style={{ color: "var(--text-muted)" }}>
                {result.metadata.description}
              </div>
            )}
          </div>
          {result.metadata.is_private && (
            <span className="badge flex-shrink-0" style={{ color: "var(--text-muted)", borderColor: "var(--border)", background: "var(--surface-raised)" }}>
              Private
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
          <span className="flex items-center gap-1">⭐ {result.metadata.stars.toLocaleString()}</span>
          <span className="flex items-center gap-1">🔀 {result.metadata.forks.toLocaleString()}</span>
          {result.metadata.language && (
            <LangDot lang={result.metadata.language} />
          )}
          <span className="flex items-center gap-1">🌿 {result.metadata.default_branch}</span>
        </div>
        <div className="text-xs pt-1 border-t" style={{ borderColor: "var(--border-subtle)", color: "var(--text-muted)" }}>
          Fetched <strong style={{ color: "var(--foreground)" }}>{result.commits_fetched}</strong> recent commits
        </div>
      </div>
      <div className="flex gap-2 pt-1">
        <button onClick={onClose} className="btn-primary flex-1 justify-center py-2.5 text-sm">
          Done
        </button>
        <a
          href={`/commits?repo=${result.repository.id}`}
          className="btn-ghost flex-1 text-center py-2.5 text-sm"
        >
          View Commits
        </a>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Browse Tab — fetch user's GitHub repos
// ---------------------------------------------------------------------------
function BrowseTab({
  onImported,
}: {
  onImported: (r: Repository, resp: RepoImportResponse) => void;
}) {
  const [repos, setRepos] = useState<GitHubUserRepo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [importing, setImporting] = useState<number | null>(null);
  const [importErr, setImportErr] = useState<string | null>(null);

  useEffect(() => {
    api.auth
      .githubRepos()
      .then(setRepos)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load repositories"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = repos.filter(
    (r) =>
      r.full_name.toLowerCase().includes(search.toLowerCase()) ||
      (r.description ?? "").toLowerCase().includes(search.toLowerCase())
  );

  const handleTrack = async (repo: GitHubUserRepo) => {
    setImporting(repo.id);
    setImportErr(null);
    try {
      const resp = await api.repositories.import(repo.html_url);
      onImported(resp.repository, resp);
    } catch (e) {
      setImportErr(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImporting(null);
    }
  };

  if (loading)
    return (
      <div className="p-6 space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-14 rounded-lg skeleton" />
        ))}
      </div>
    );

  if (error)
    return (
      <div className="p-6">
        <div className="px-4 py-3 rounded-lg text-sm" style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)" }}>
          {error}
        </div>
        <p className="text-xs mt-3" style={{ color: "var(--text-muted)" }}>
          Make sure the backend is running and you are authenticated.
        </p>
      </div>
    );

  return (
    <div className="flex flex-col h-full" style={{ maxHeight: "calc(85vh - 140px)" }}>
      {/* Search */}
      <div className="px-4 py-3 border-b flex-shrink-0" style={{ borderColor: "var(--border-subtle)" }}>
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2"
            width="13" height="13" viewBox="0 0 16 16" fill="var(--text-muted)"
          >
            <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.499 4.499 0 1 0-8.997 0A4.499 4.499 0 0 0 11.5 7Z" />
          </svg>
          <input
            type="text"
            placeholder={`Search ${repos.length} repositories…`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-8 text-xs"
          />
        </div>
      </div>

      {/* Error */}
      {importErr && (
        <div
          className="mx-4 mt-3 px-3 py-2 rounded-lg text-xs flex-shrink-0"
          style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)" }}
        >
          {importErr}
        </div>
      )}

      {/* List */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
        {filtered.length === 0 ? (
          <div className="text-center py-12 text-sm" style={{ color: "var(--text-muted)" }}>
            No repositories match &ldquo;{search}&rdquo;
          </div>
        ) : (
          filtered.map((repo) => (
            <div
              key={repo.id}
              className="flex items-center gap-3 px-3 py-3 rounded-xl transition-colors"
              style={{ background: "var(--surface-raised)" }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLDivElement).style.background = "var(--surface-overlay)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLDivElement).style.background = "var(--surface-raised)";
              }}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-sm font-semibold truncate" style={{ color: "var(--foreground)" }}>
                    {repo.full_name}
                  </span>
                  {repo.private && (
                    <span className="badge text-[9px]" style={{ color: "var(--text-muted)", borderColor: "var(--border)", background: "var(--surface)" }}>
                      Private
                    </span>
                  )}
                  {repo.fork && (
                    <span className="badge text-[9px]" style={{ color: "var(--text-muted)", borderColor: "var(--border)", background: "var(--surface)" }}>
                      Fork
                    </span>
                  )}
                  {repo.archived && (
                    <span className="badge text-[9px]" style={{ color: "#f59e0b", borderColor: "rgba(245,158,11,0.3)", background: "rgba(245,158,11,0.08)" }}>
                      Archived
                    </span>
                  )}
                </div>
                {repo.description && (
                  <div className="text-xs mt-0.5 truncate" style={{ color: "var(--text-muted)" }}>
                    {repo.description}
                  </div>
                )}
                <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                  <LangDot lang={repo.language} />
                  {repo.stargazers_count > 0 && (
                    <span className="flex items-center gap-1 text-[11px]" style={{ color: "var(--text-muted)" }}>
                      ⭐ {repo.stargazers_count.toLocaleString()}
                    </span>
                  )}
                  {repo.updated_at && (
                    <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                      Updated {new Date(repo.updated_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => handleTrack(repo)}
                disabled={importing !== null}
                className="btn-primary flex-shrink-0 text-xs py-1.5 px-3"
                style={{ opacity: importing === null ? 1 : importing === repo.id ? 1 : 0.5 }}
              >
                {importing === repo.id ? (
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 border border-white/40 border-t-white rounded-full animate-spin inline-block" />
                    Adding…
                  </span>
                ) : (
                  "Track"
                )}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// URL Tab
// ---------------------------------------------------------------------------
function UrlTab({
  onImported,
}: {
  onImported: (r: Repository, resp: RepoImportResponse) => void;
}) {
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await api.repositories.import(url.trim(), branch.trim() || undefined);
      onImported(res.repository, res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-6 space-y-4">
      <div>
        <label className="block text-xs font-semibold mb-2" style={{ color: "var(--text-muted)" }}>
          GitHub Repository URL *
        </label>
        <input
          ref={inputRef}
          type="url"
          placeholder="https://github.com/owner/repo"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
          className="input font-mono text-xs"
        />
      </div>
      <div>
        <label className="block text-xs font-semibold mb-2" style={{ color: "var(--text-muted)" }}>
          Branch <span style={{ color: "var(--text-dim)" }}>(optional)</span>
        </label>
        <input
          type="text"
          placeholder="main"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          className="input font-mono text-xs"
        />
      </div>
      {error && (
        <div className="px-3 py-2 rounded-lg text-xs" style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)" }}>
          {error}
        </div>
      )}
      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="btn-primary flex-1 justify-center py-2.5 text-sm"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 border border-white/40 border-t-white rounded-full animate-spin inline-block" />
              Importing…
            </span>
          ) : (
            "Import Repository"
          )}
        </button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Repo Card
// ---------------------------------------------------------------------------
function RepoCard({
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

  // Timeout confirm state
  useEffect(() => {
    if (!confirm) return;
    const t = setTimeout(() => setConfirm(false), 3000);
    return () => clearTimeout(t);
  }, [confirm]);

  return (
    <div
      className="card-elevated flex items-center gap-4 px-4 py-3.5 transition-colors"
      style={{ borderRadius: "10px" }}
    >
      {/* Icon */}
      <div
        className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
        style={{ background: "var(--surface-overlay)", border: "1px solid var(--border)" }}
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="var(--text-muted)">
          <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8Z" />
        </svg>
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
            {repo.full_name}
          </span>
          {repo.is_private && (
            <span className="badge text-[9px]" style={{ color: "var(--text-muted)", borderColor: "var(--border)", background: "var(--surface)" }}>
              Private
            </span>
          )}
          <span
            className="flex items-center gap-1 text-[10px] font-medium"
            style={{ color: repo.webhook_active ? "#22c55e" : "var(--text-dim)" }}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${repo.webhook_active ? "bg-green-400" : ""}`}
              style={{ background: repo.webhook_active ? "#22c55e" : "var(--border)" }}
            />
            {repo.webhook_active ? "Webhook active" : "Webhook inactive"}
          </span>
        </div>
        <div className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
          Added {new Date(repo.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <a
          href={`/commits?repo=${repo.id}`}
          className="btn-ghost text-xs py-1.5 px-3"
        >
          View Commits
        </a>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="text-xs py-1.5 px-3 rounded-lg font-medium transition-all disabled:opacity-40 cursor-pointer"
          style={
            confirm
              ? { background: "rgba(239,68,68,0.1)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.3)" }
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
  const [search, setSearch] = useState("");

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

  const filtered = repos.filter(
    (r) =>
      r.full_name.toLowerCase().includes(search.toLowerCase()) ||
      (r.description ?? "").toLowerCase().includes(search.toLowerCase())
  );

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
          className="flex items-center justify-between px-6 h-14 border-b flex-shrink-0"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <div>
            <h1 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
              Repositories
            </h1>
            <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>
              {repos.length === 0
                ? "Import a GitHub repository to start analysing risk"
                : `${repos.length} connected repositor${repos.length === 1 ? "y" : "ies"}`}
            </p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="btn-primary text-xs px-3 py-1.5"
          >
            <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
              <path d="M7.75 2a.75.75 0 0 1 .75.75V7h4.25a.75.75 0 0 1 0 1.5H8.5v4.25a.75.75 0 0 1-1.5 0V8.5H2.75a.75.75 0 0 1 0-1.5H7V2.75A.75.75 0 0 1 7.75 2Z" />
            </svg>
            Add Repository
          </button>
        </header>

        {/* Search bar (only when repos exist) */}
        {repos.length > 0 && (
          <div
            className="px-6 py-3 border-b flex-shrink-0"
            style={{ borderColor: "var(--border-subtle)" }}
          >
            <div className="relative max-w-sm">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2"
                width="13" height="13" viewBox="0 0 16 16" fill="var(--text-muted)"
              >
                <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.499 4.499 0 1 0-8.997 0A4.499 4.499 0 0 0 11.5 7Z" />
              </svg>
              <input
                type="text"
                placeholder="Filter repositories…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input pl-8 text-xs py-1.5"
              />
            </div>
          </div>
        )}

        {/* Body */}
        <main className="flex-1 p-6">
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 rounded-xl skeleton" />
              ))}
            </div>
          ) : repos.length === 0 ? (
            // Empty state
            <div className="flex flex-col items-center justify-center h-72 gap-5">
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center"
                style={{ background: "var(--surface-raised)", border: "1px solid var(--border)" }}
              >
                <svg width="28" height="28" viewBox="0 0 16 16" fill="var(--text-dim)">
                  <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8Z" />
                </svg>
              </div>
              <div className="text-center">
                <div className="text-base font-bold mb-1" style={{ color: "var(--foreground)" }}>
                  No repositories yet
                </div>
                <div className="text-sm max-w-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  Connect a GitHub repository to start tracking commit risk and deployment health.
                </div>
              </div>
              <button
                onClick={() => setShowModal(true)}
                className="btn-primary px-5 py-2.5 text-sm"
              >
                Add your first repository
              </button>
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16 text-sm" style={{ color: "var(--text-muted)" }}>
              No repositories match &ldquo;{search}&rdquo;
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((repo) => (
                <RepoCard key={repo.id} repo={repo} onDelete={handleDelete} />
              ))}
            </div>
          )}
        </main>
      </div>
    </>
  );
}
