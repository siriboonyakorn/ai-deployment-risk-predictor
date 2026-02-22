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
