import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.exceptions import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from app.models import Commit, Repository
from app.schemas import (
    CommitHistoryResponse,
    CommitResponse,
    CommitSyncResponse,
    GitHubAuthor,
    GitHubCommitDetail,
    GitHubCommitItem,
    GitHubRepoMetadata,
    MessageResponse,
    RepositoryCreate,
    RepositoryResponse,
    RepoImportRequest,
    RepoImportResponse,
)
from app.services.commit_sync import sync_commits_for_repo
from app.services.github import (
    fetch_commit_history,
    fetch_repo_metadata,
    parse_github_url,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/repositories", tags=["Repositories"])
settings = get_settings()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_commit_items(raw_commits: list[dict]) -> list[GitHubCommitItem]:
    items: list[GitHubCommitItem] = []
    for c in raw_commits:
        inner = c.get("commit", {})
        author_data = inner.get("author") or {}
        committer_data = inner.get("committer") or {}
        items.append(
            GitHubCommitItem(
                sha=c["sha"],
                html_url=c.get("html_url", ""),
                commit=GitHubCommitDetail(
                    message=inner.get("message", ""),
                    author=GitHubAuthor(
                        name=author_data.get("name"),
                        email=author_data.get("email"),
                        date=author_data.get("date"),
                    ),
                    committer=GitHubAuthor(
                        name=committer_data.get("name"),
                        email=committer_data.get("email"),
                        date=committer_data.get("date"),
                    ),
                ),
            )
        )
    return items


def _build_metadata(gh: dict) -> GitHubRepoMetadata:
    return GitHubRepoMetadata(
        github_repo_id=gh["id"],
        name=gh["name"],
        full_name=gh["full_name"],
        description=gh.get("description"),
        is_private=gh.get("private", False),
        default_branch=gh.get("default_branch", "main"),
        stars=gh.get("stargazers_count", 0),
        forks=gh.get("forks_count", 0),
        open_issues=gh.get("open_issues_count", 0),
        html_url=gh.get("html_url", ""),
        language=gh.get("language"),
        created_at=gh.get("created_at"),
        updated_at=gh.get("updated_at"),
    )


# ---------------------------------------------------------------------------
# Standard CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=list[RepositoryResponse])
def list_repositories(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """List all connected repositories."""
    return db.query(Repository).offset(skip).limit(limit).all()


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def connect_repository(payload: RepositoryCreate, db: Session = Depends(get_db)):
    """Connect a new GitHub repository for risk monitoring."""
    existing = db.query(Repository).filter(
        Repository.github_repo_id == payload.github_repo_id
    ).first()

    if existing:
        raise ConflictError(f"Repository '{payload.full_name}' is already connected.")

    repo = Repository(
        github_repo_id=payload.github_repo_id,
        name=payload.name,
        full_name=payload.full_name,
        description=payload.description,
        is_private=payload.is_private,
        owner_id=1,  # placeholder until auth is wired up
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    logger.info("Connected repository %s", repo.full_name)
    return repo


@router.get("/{repo_id}", response_model=RepositoryResponse)
def get_repository(repo_id: int, db: Session = Depends(get_db)):
    """Get a single repository by ID."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise NotFoundError("Repository", repo_id)
    return repo


@router.delete("/{repo_id}", response_model=MessageResponse)
def disconnect_repository(repo_id: int, db: Session = Depends(get_db)):
    """Disconnect and remove a repository."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise NotFoundError("Repository", repo_id)
    db.delete(repo)
    db.commit()
    logger.info("Disconnected repository %s", repo.full_name)
    return MessageResponse(message=f"Repository '{repo.full_name}' disconnected.")


# ---------------------------------------------------------------------------
# GitHub URL import
# ---------------------------------------------------------------------------

@router.post(
    "/import",
    response_model=RepoImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import a repository by GitHub URL",
)
def import_repository(
    payload: RepoImportRequest,
    db: Session = Depends(get_db),
):
    """
    Accept a GitHub repository URL, fetch its metadata and recent commit
    history from the GitHub API, persist the repository record, and return
    everything in a single response.

    - **github_url**: Full GitHub URL, e.g. `https://github.com/owner/repo`
    - **branch**: Optional branch name. Defaults to the repository's default branch.
    """
    # 1. Parse URL  (raises ValidationError on bad format)
    owner, repo_name = parse_github_url(payload.github_url)

    token = settings.github_token_or_none

    # 2. Fetch repo metadata from GitHub  (raises NotFoundError / ExternalServiceError)
    gh_repo = fetch_repo_metadata(owner, repo_name, token=token)

    # 3. Upsert repository record
    existing = db.query(Repository).filter(
        Repository.github_repo_id == gh_repo["id"]
    ).first()

    if existing:
        repo_record = existing
    else:
        repo_record = Repository(
            github_repo_id=gh_repo["id"],
            name=gh_repo["name"],
            full_name=gh_repo["full_name"],
            description=gh_repo.get("description"),
            is_private=gh_repo.get("private", False),
            owner_id=1,  # placeholder until auth is wired up
        )
        db.add(repo_record)
        db.commit()
        db.refresh(repo_record)

    # 4. Fetch commit history  (non-fatal)
    branch = payload.branch or gh_repo.get("default_branch")
    try:
        raw_commits = fetch_commit_history(owner, repo_name, token=token, branch=branch)
    except Exception as exc:
        logger.warning("Could not fetch commits during import: %s", exc)
        raw_commits = []

    commit_items = _build_commit_items(raw_commits)

    logger.info("Imported repository %s (%d commits fetched)", repo_record.full_name, len(commit_items))
    return RepoImportResponse(
        repository=repo_record,
        metadata=_build_metadata(gh_repo),
        commits=commit_items,
        commits_fetched=len(commit_items),
    )


# ---------------------------------------------------------------------------
# Commit history for a connected repository
# ---------------------------------------------------------------------------

@router.get(
    "/{repo_id}/commits",
    response_model=CommitHistoryResponse,
    summary="Fetch commit history for a connected repository",
)
def get_commit_history(
    repo_id: int,
    branch: str = Query(default=None, description="Branch name (defaults to repo default branch)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=30, ge=1, le=100, description="Commits per page"),
    db: Session = Depends(get_db),
):
    """
    Fetch recent commit history for a connected repository directly from the
    GitHub API.

    - **repo_id**: Internal repository ID (from the database).
    - **branch**: Branch to query. Omit to use the repository's default branch.
    - **page** / **per_page**: Pagination controls (max 100 per page).
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise NotFoundError("Repository", repo_id)

    parts = repo.full_name.split("/", 1)
    if len(parts) != 2:
        raise ValidationError(f"Stored full_name '{repo.full_name}' is not in 'owner/repo' format.")
    owner, repo_name = parts
    token = settings.github_token_or_none

    # fetch_commit_history raises typed exceptions (NotFoundError, etc.)
    raw_commits = fetch_commit_history(
        owner, repo_name, token=token, branch=branch, per_page=per_page, page=page,
    )

    commit_items = _build_commit_items(raw_commits)

    return CommitHistoryResponse(
        repository_id=repo.id,
        full_name=repo.full_name,
        branch=branch,
        page=page,
        per_page=per_page,
        commits=commit_items,
        commits_fetched=len(commit_items),
    )


# ---------------------------------------------------------------------------
# Commit sync — fetch last N commits, extract metrics, persist
# ---------------------------------------------------------------------------

@router.post(
    "/{repo_id}/sync-commits",
    response_model=CommitSyncResponse,
    summary="Sync commit history and metrics into the database",
)
def sync_commits(
    repo_id: int,
    branch: str = Query(default=None, description="Branch (defaults to repo default branch)"),
    limit: int = Query(default=None, ge=1, le=500, description="Max commits to sync (default from settings)"),
    fetch_metrics: bool = Query(default=True, description="Fetch per-commit stats (lines added/deleted, files changed)"),
    db: Session = Depends(get_db),
):
    """
    Fetch the last *N* commits from GitHub, extract per-commit metrics
    (lines added, lines deleted, files changed), and store everything in the
    database.

    Existing commits (matched by SHA) are skipped.  New commits are
    persisted together with their metrics.

    - **repo_id**: Internal repository ID.
    - **branch**: Branch to query (omit for default branch).
    - **limit**: Override the default fetch limit (``COMMIT_FETCH_LIMIT``).
    - **fetch_metrics**: When ``true`` (default), an extra API call per
      commit is made to retrieve stats.  Set to ``false`` for a faster sync
      without metrics.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise NotFoundError("Repository", repo_id)

    commits = sync_commits_for_repo(
        repo, db, branch=branch, limit=limit, fetch_metrics=fetch_metrics,
    )

    return CommitSyncResponse(
        repository_id=repo.id,
        full_name=repo.full_name,
        commits_synced=len(commits),
        commits=[
            CommitResponse(
                id=c.id,
                sha=c.sha,
                message=c.message,
                author_name=c.author_name,
                author_email=c.author_email,
                lines_added=c.lines_added,
                lines_deleted=c.lines_deleted,
                files_changed=c.files_changed,
                committed_at=c.committed_at,
                repository_id=c.repository_id,
                created_at=c.created_at,
            )
            for c in commits
        ],
    )


# ---------------------------------------------------------------------------
# List stored commits from DB
# ---------------------------------------------------------------------------

@router.get(
    "/{repo_id}/stored-commits",
    response_model=list[CommitResponse],
    summary="List commits stored in the database for a repository",
)
def list_stored_commits(
    repo_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Return commits that have already been synced to the database.

    Unlike ``GET /{repo_id}/commits`` (which queries GitHub live), this
    endpoint reads from the local store and includes persisted metrics.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise NotFoundError("Repository", repo_id)

    commits = (
        db.query(Commit)
        .filter(Commit.repository_id == repo.id)
        .order_by(Commit.committed_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return commits
