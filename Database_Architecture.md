# 🗄 Database Architecture
## AI Software Failure Predictor

---

# 1. Overview

The system uses PostgreSQL as the primary relational database.

The database stores:

- User accounts
- Connected repositories
- Commit metadata
- Pull requests
- ML predictions
- Labeled training data

The schema is designed for scalability and ML experimentation.

---

# 2. Core Entities

## Users

Stores authenticated GitHub users.

Fields:
- id (UUID)
- github_id (unique)
- email
- username
- created_at

---

## Repositories

Stores GitHub repositories connected by users.

Fields:
- id (UUID)
- user_id (Foreign Key → users)
- github_repo_id (unique)
- name
- owner
- repo_size
- contributor_count
- created_at

Relationship:
One user can have multiple repositories.

---

## Commits

Stores commit-level metadata.

Fields:
- id (UUID)
- repository_id (Foreign Key → repositories)
- github_commit_sha (unique)
- lines_added
- lines_deleted
- files_changed
- developer_username
- commit_timestamp
- created_at

Relationship:
One repository has many commits.

---

## Pull Requests

Stores PR-level metadata.

Fields:
- id (UUID)
- repository_id (Foreign Key → repositories)
- github_pr_id (unique)
- title
- merged (boolean)
- lines_added
- lines_deleted
- files_changed
- created_at

---

## Predictions

Stores ML prediction results.

Fields:
- id (UUID)
- commit_id (Foreign Key → commits)
- model_version
- probability
- risk_level
- created_at

Purpose:
Track model outputs and enable monitoring.

---

## Training Data

Stores labeled dataset for ML training.

Fields:
- id (UUID)
- commit_id (Foreign Key → commits)
- feature_vector (JSONB)
- label (0 or 1)
- created_at

Purpose:
Enable retraining and model improvements.

---

# 3. Relationships Overview

User
→ Repositories
→ Commits
→ Predictions

Repositories
→ Pull Requests

Commits
→ Training Data

---

# 4. Indexing Strategy

Indexes should exist on:

- repository_id
- commit_id
- label
- github_commit_sha

Purpose:
- Fast dashboard queries
- Efficient training dataset retrieval
- Improved inference logging

---

# 5. Data Flow

1. User connects repository
2. Repository stored
3. Commits ingested
4. Features extracted
5. Label assigned
6. Prediction stored
7. Dashboard reads predictions

---

# 6. Scalability Plan (Future)

- Add Redis caching
- Introduce background workers
- Add read replicas
- Introduce analytics warehouse
- Implement partitioning for large commit datasets

---

# 7. Design Principles

- Strong relational integrity
- Separation of raw data and ML features
- Version-controlled predictions
- Auditability of training data
- Scalable architecture for future SaaS growth