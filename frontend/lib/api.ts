/**
 * Typed API client for the AI Deployment Risk Predictor backend.
 * Uses Next.js rewrites so every path goes through /api/v1/* → backend.
 */

import { getToken } from "@/lib/auth";

const API_BASE = "/api/v1";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      (body as { detail?: string }).detail ?? `API error ${res.status}`
    );
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export interface AuthUser {
  id: number;
  username: string;
  email: string | null;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  uptime_seconds: number;
  db_status: string;
}

export interface Repository {
  id: number;
  name: string;
  full_name: string;
  description: string | null;
  is_private: boolean;
  webhook_active: boolean;
  owner_id: number;
  created_at: string;
}

export interface GitHubAuthor {
  name: string | null;
  email: string | null;
  date: string | null;
}

export interface GitHubCommitItem {
  sha: string;
  html_url: string;
  commit: {
    message: string;
    author: GitHubAuthor | null;
    committer: GitHubAuthor | null;
  };
}

export interface GitHubRepoMetadata {
  github_repo_id: number;
  name: string;
  full_name: string;
  description: string | null;
  is_private: boolean;
  default_branch: string;
  stars: number;
  forks: number;
  open_issues: number;
  html_url: string;
  language: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface RepoImportResponse {
  repository: Repository;
  metadata: GitHubRepoMetadata;
  commits: GitHubCommitItem[];
  commits_fetched: number;
}

export interface CommitHistoryResponse {
  repository_id: number;
  full_name: string;
  branch: string | null;
  page: number;
  per_page: number;
  commits: GitHubCommitItem[];
  commits_fetched: number;
}

export interface RiskAssessment {
  id: number;
  commit_id: number;
  risk_score: number;
  risk_level: RiskLevel;
  confidence: number | null;
  model_version: string;
  created_at: string;
}

export interface RiskPredictionResponse {
  commit: {
    id: number;
    sha: string;
    message: string | null;
    author_email: string | null;
    lines_added: number;
    lines_deleted: number;
    files_changed: number;
    repository_id: number;
    created_at: string;
  };
  assessment: RiskAssessment;
}

// ---------------------------------------------------------------------------
// API methods
// ---------------------------------------------------------------------------

export const api = {
  health: {
    get: () => request<HealthResponse>("/health"),
  },

  auth: {
    me: () =>
      request<AuthUser>("/auth/me"),
    logout: () =>
      request<{ message: string }>("/auth/logout", { method: "POST" }),
  },

  repositories: {
    list: () => request<Repository[]>("/repositories"),
    get: (id: number) => request<Repository>(`/repositories/${id}`),
    import: (github_url: string, branch?: string) =>
      request<RepoImportResponse>("/repositories/import", {
        method: "POST",
        body: JSON.stringify({ github_url, branch }),
      }),
    delete: (id: number) =>
      request<{ message: string }>(`/repositories/${id}`, {
        method: "DELETE",
      }),
    commits: (id: number, page = 1, per_page = 30, branch?: string) => {
      const params = new URLSearchParams({
        page: String(page),
        per_page: String(per_page),
      });
      if (branch) params.set("branch", branch);
      return request<CommitHistoryResponse>(
        `/repositories/${id}/commits?${params}`
      );
    },
  },

  predictions: {
    get: (sha: string) =>
      request<RiskPredictionResponse>(`/predictions/${sha}`),
  },
};
