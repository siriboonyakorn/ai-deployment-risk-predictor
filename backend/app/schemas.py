from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models import RiskLevel


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    uptime_seconds: float
    db_status: str  # "ok" | "unreachable"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    github_id: int
    access_token: str


class UserResponse(UserBase):
    id: int
    github_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class RepositoryBase(BaseModel):
    name: str
    full_name: str
    description: Optional[str] = None
    is_private: bool = False


class RepositoryCreate(RepositoryBase):
    github_repo_id: int


class RepositoryResponse(RepositoryBase):
    id: int
    github_repo_id: int
    webhook_active: bool
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------

class CommitBase(BaseModel):
    sha: str
    message: Optional[str] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    lines_added: int = 0
    lines_deleted: int = 0
    files_changed: int = 0
    committed_at: Optional[datetime] = None


class CommitCreate(CommitBase):
    repository_id: int


class CommitResponse(CommitBase):
    id: int
    repository_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Risk Assessment
# ---------------------------------------------------------------------------

class RiskPredictionRequest(BaseModel):
    sha: str
    repository_full_name: str
    lines_added: int = 0
    lines_deleted: int = 0
    files_changed: int = 0
    commit_message: Optional[str] = None
    author_email: Optional[str] = None


class RiskAssessmentResponse(BaseModel):
    id: int
    commit_id: int
    risk_score: float  # 0.0 – 100.0
    risk_level: RiskLevel
    confidence: Optional[float] = None
    model_version: str
    created_at: datetime

    class Config:
        from_attributes = True


class RiskPredictionResponse(BaseModel):
    commit: CommitResponse
    assessment: RiskAssessmentResponse


# ---------------------------------------------------------------------------
# GitHub URL import
# ---------------------------------------------------------------------------

class RepoImportRequest(BaseModel):
    """Payload for POST /repositories/import."""
    github_url: str
    # Optional branch to pull commit history from (defaults to default branch)
    branch: Optional[str] = None


class GitHubAuthor(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    date: Optional[datetime] = None


class GitHubCommitDetail(BaseModel):
    message: str
    author: Optional[GitHubAuthor] = None
    committer: Optional[GitHubAuthor] = None


class GitHubCommitItem(BaseModel):
    """A single commit entry as returned by GET /repos/{owner}/{repo}/commits."""
    sha: str
    html_url: str
    commit: GitHubCommitDetail


class GitHubRepoMetadata(BaseModel):
    """Subset of GitHub repo fields surfaced on the import response."""
    github_repo_id: int
    name: str
    full_name: str
    description: Optional[str] = None
    is_private: bool
    default_branch: str
    stars: int
    forks: int
    open_issues: int
    html_url: str
    language: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RepoImportResponse(BaseModel):
    """Response for POST /repositories/import."""
    repository: RepositoryResponse
    metadata: GitHubRepoMetadata
    commits: list[GitHubCommitItem]
    commits_fetched: int


class CommitHistoryResponse(BaseModel):
    """Response for GET /repositories/{repo_id}/commits."""
    repository_id: int
    full_name: str
    branch: Optional[str] = None
    page: int
    per_page: int
    commits: list[GitHubCommitItem]
    commits_fetched: int


# ---------------------------------------------------------------------------
# GitHub Webhook
# ---------------------------------------------------------------------------

class WebhookPushPayload(BaseModel):
    ref: str
    repository: dict
    commits: list[dict]
    sender: dict


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    """Returned after a successful GitHub OAuth login."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "UserResponse"


class GitHubLoginURL(BaseModel):
    """Returned by GET /auth/github/login so clients can redirect themselves."""
    url: str


# ---------------------------------------------------------------------------
# GitHub User Repos listing
# ---------------------------------------------------------------------------

class GitHubUserRepoItem(BaseModel):
    """A single repository from GET /user/repos."""
    id: int
    name: str
    full_name: str
    description: Optional[str] = None
    private: bool
    html_url: str
    language: Optional[str] = None
    stargazers_count: int = 0
    forks_count: int = 0
    open_issues_count: int = 0
    default_branch: str = "main"
    updated_at: Optional[str] = None
    created_at: Optional[str] = None
    topics: list[str] = []
    fork: bool = False
    archived: bool = False
