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
  const token = await getToken();
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

export interface GitHubUserRepo {
  id: number;
  name: string;
  full_name: string;
  description: string | null;
  private: boolean;
  html_url: string;
  language: string | null;
  stargazers_count: number;
  forks_count: number;
  open_issues_count: number;
  default_branch: string;
  updated_at: string | null;
  created_at: string | null;
  topics: string[];
  fork: boolean;
  archived: boolean;
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

export interface RiskPredictionRequest {
  sha: string;
  repository_full_name: string;
  lines_added?: number;
  lines_deleted?: number;
  files_changed?: number;
  commit_message?: string | null;
  author_email?: string | null;
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
// Dashboard Stats
// ---------------------------------------------------------------------------

export interface DashboardStats {
  total_repositories: number;
  total_commits: number;
  total_assessments: number;
  risk_counts: { LOW: number; MEDIUM: number; HIGH: number };
  avg_risk_score: number | null;
  high_risk_count: number;
  recent_commits_24h: number;
  recent_high_risk_24h: number;
}

export interface RiskDistributionEntry {
  level: string;
  count: number;
  percentage: number;
}

export interface ScoreHistogramBucket {
  range: string;
  count: number;
}

export interface RiskDistributionResponse {
  distribution: RiskDistributionEntry[];
  total: number;
  score_histogram: ScoreHistogramBucket[];
}

export interface RecentActivityItem {
  sha: string;
  message: string;
  author_email: string | null;
  author_name: string | null;
  risk_score: number;
  risk_level: RiskLevel;
  confidence: number | null;
  model_version: string;
  repository_full_name: string | null;
  committed_at: string | null;
  analyzed_at: string | null;
}

export interface CommitWithRisk {
  id: number;
  sha: string;
  message: string;
  author_name: string | null;
  author_email: string | null;
  lines_added: number;
  lines_deleted: number;
  files_changed: number;
  avg_cyclomatic_complexity: number | null;
  complexity_rank: string | null;
  repository_id: number;
  repository_full_name: string | null;
  committed_at: string | null;
  created_at: string | null;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  confidence: number | null;
  model_version: string | null;
}

export interface CommitsWithRiskResponse {
  items: CommitWithRisk[];
  total: number;
  skip: number;
  limit: number;
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
    githubRepos: (page = 1, per_page = 100) =>
      request<GitHubUserRepo[]>(`/auth/github/repos?page=${page}&per_page=${per_page}`),
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
    create: (payload: RiskPredictionRequest) =>
      request<RiskPredictionResponse>('/predictions', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    list: (skip = 0, limit = 50) =>
      request<RiskPredictionResponse[]>(`/predictions?skip=${skip}&limit=${limit}`),
  },

  dashboard: {
    stats: () =>
      request<DashboardStats>("/dashboard/stats"),
    riskDistribution: () =>
      request<RiskDistributionResponse>("/dashboard/risk-distribution"),
    recentActivity: (limit = 10) =>
      request<{ items: RecentActivityItem[]; count: number }>(
        `/dashboard/recent-activity?limit=${limit}`
      ),
    commitsWithRisk: (params: {
      skip?: number;
      limit?: number;
      risk_level?: string;
      sort_by?: string;
      sort_order?: string;
      search?: string;
      repo_id?: number;
    } = {}) => {
      const qs = new URLSearchParams();
      if (params.skip != null) qs.set("skip", String(params.skip));
      if (params.limit != null) qs.set("limit", String(params.limit));
      if (params.risk_level) qs.set("risk_level", params.risk_level);
      if (params.sort_by) qs.set("sort_by", params.sort_by);
      if (params.sort_order) qs.set("sort_order", params.sort_order);
      if (params.search) qs.set("search", params.search);
      if (params.repo_id != null) qs.set("repo_id", String(params.repo_id));
      return request<CommitsWithRiskResponse>(
        `/dashboard/commits-with-risk?${qs}`
      );
    },
  },
};
