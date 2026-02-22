from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Repository
from app.schemas import MessageResponse, RepositoryCreate, RepositoryResponse

router = APIRouter(prefix="/repositories", tags=["Repositories"])


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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository '{payload.full_name}' is already connected.",
        )

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
    return repo


@router.get("/{repo_id}", response_model=RepositoryResponse)
def get_repository(repo_id: int, db: Session = Depends(get_db)):
    """Get a single repository by ID."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with id={repo_id} not found.",
        )
    return repo


@router.delete("/{repo_id}", response_model=MessageResponse)
def disconnect_repository(repo_id: int, db: Session = Depends(get_db)):
    """Disconnect and remove a repository."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with id={repo_id} not found.",
        )
    db.delete(repo)
    db.commit()
    return MessageResponse(message=f"Repository '{repo.full_name}' disconnected.")
