import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    clerk_user_id = Column(String(128), unique=True, nullable=True, index=True)
    github_id = Column(Integer, unique=True, nullable=True, index=True)
    google_id = Column(String(50), unique=True, nullable=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    access_token = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    repositories = relationship("Repository", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    github_repo_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    full_name = Column(String(500), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_private = Column(Boolean, default=False)
    webhook_active = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="repositories")
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Repository id={self.id} full_name={self.full_name}>"


class Commit(Base):
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, index=True)
    sha = Column(String(40), nullable=False, index=True)
    message = Column(Text, nullable=True)
    author_name = Column(String(255), nullable=True)
    author_email = Column(String(255), nullable=True)
    lines_added = Column(Integer, default=0)
    lines_deleted = Column(Integer, default=0)
    files_changed = Column(Integer, default=0)
    # Complexity metrics (populated by radon analysis)
    avg_cyclomatic_complexity = Column(Float, nullable=True)
    max_cyclomatic_complexity = Column(Float, nullable=True)
    avg_maintainability_index = Column(Float, nullable=True)
    complexity_rank = Column(String(2), nullable=True)  # A-F
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    committed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="commits")
    risk_assessment = relationship("RiskAssessment", back_populates="commit", uselist=False)

    def __repr__(self):
        return f"<Commit sha={self.sha[:7]} repo_id={self.repository_id}>"


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    commit_id = Column(Integer, ForeignKey("commits.id"), nullable=False, unique=True)
    risk_score = Column(Float, nullable=False)  # 0.0 – 100.0
    risk_level = Column(Enum(RiskLevel), nullable=False)
    confidence = Column(Float, nullable=True)  # 0.0 – 1.0
    features_json = Column(Text, nullable=True)  # raw ML features (JSON string)
    score_breakdown_json = Column(Text, nullable=True)  # per-category score breakdown
    model_version = Column(String(50), default="rule-v1")
    created_at = Column(DateTime, default=datetime.utcnow)

    commit = relationship("Commit", back_populates="risk_assessment")

    def __repr__(self):
        return f"<RiskAssessment commit_id={self.commit_id} score={self.risk_score} level={self.risk_level}>"
