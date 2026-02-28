"""
Training data pipeline  (AI_Model_Engineering.md §4 + §7).

Collects labeled commits from the database, extracts features, applies
preprocessing (§7), and produces train / test splits ready for model
training.

Pipeline steps:
    1. Query commits from DB  (with associated RiskAssessments & features)
    2. Label commits via the failure detector  (§3)
    3. Build feature matrix  (§5-6 — reuses ``risk_engine.extract_features``)
    4. Preprocess  (§7 — median imputation, StandardScaler, remove corrupt)
    5. Split into train / test sets
    6. Return as numpy arrays or save as CSV for inspection
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Commit, Repository, RiskAssessment
from app.services.risk_engine import CommitFeatures, extract_features

logger = logging.getLogger(__name__)

# Feature columns used by the ML model (must be numeric).
# This is the ordered list fed into the model — keep in sync with
# CommitFeatures fields.
FEATURE_COLUMNS: list[str] = [
    # Code-level
    "lines_added",
    "lines_deleted",
    "total_lines_changed",
    "files_changed",
    "file_types_count",
    "percentage_test_files",
    # Complexity
    "avg_cyclomatic_complexity",
    "max_cyclomatic_complexity",
    "avg_maintainability_index",
    "total_cc_blocks",
    "avg_halstead_volume",
    "complexity_python_files",
    # Developer-level
    "total_prior_commits",
    "previous_bug_rate",
    "commit_frequency",
    "time_since_last_commit",
    # Repository-level
    "repo_size",
    "contributor_count",
    "open_issues_count",
    "commit_velocity",
    # Temporal
    "day_of_week",
    "hour_of_day",
    "weekend_flag",  # will be cast to int (0/1)
    # Derived
    "code_churn_ratio",
    "risk_density",
    "developer_risk_score",
    # Message
    "message_length",
    "has_risky_keywords",  # will be cast to int (0/1)
    "risky_keyword_count",
]


# ---------------------------------------------------------------------------
# Step 1 — Collect raw data from DB
# ---------------------------------------------------------------------------

def collect_training_samples(db: Session) -> list[dict]:
    """
    Query every commit that has a stored ``features_json`` and
    ``risk_assessment`` and return a list of dicts ready for feature matrix
    construction.

    Each dict contains:
        - ``features``: parsed CommitFeatures dict
        - ``label``: 1 if the rule-based engine flagged HIGH, else 0
          (bootstrap labeling; will be replaced by ``labeling.py`` once
          GitHub API labels are collected)
        - ``sha``, ``repository_full_name``
    """
    samples: list[dict] = []

    assessments = (
        db.query(RiskAssessment)
        .join(Commit)
        .filter(RiskAssessment.features_json.isnot(None))
        .all()
    )

    for a in assessments:
        try:
            features_dict = json.loads(a.features_json)
        except (json.JSONDecodeError, TypeError):
            continue

        commit = a.commit
        if not commit:
            continue

        repo = commit.repository
        full_name = repo.full_name if repo else "unknown"

        samples.append({
            "sha": commit.sha,
            "repository_full_name": full_name,
            "features": features_dict,
            "label": a.label if hasattr(a, "label") and a.label is not None
                     else (1 if a.risk_level and a.risk_level.value == "HIGH" else 0),
        })

    logger.info("Collected %d training samples from database.", len(samples))
    return samples


# ---------------------------------------------------------------------------
# Step 2 — Build numpy feature matrix  +  label vector
# ---------------------------------------------------------------------------

def _try_import_numpy():
    try:
        import numpy as np
        return np
    except ImportError:
        raise ImportError(
            "numpy is required for ML training. "
            "Install with:  pip install -r requirements-ml.txt"
        )


def build_feature_matrix(
    samples: list[dict],
) -> tuple:
    """
    Convert a list of sample dicts into a NumPy feature matrix ``X`` and
    label vector ``y``.

    Returns:
        ``(X, y, shas)``  where ``X.shape = (n_samples, n_features)`` and
        ``y.shape = (n_samples,)``.  ``shas`` is a list of commit SHAs for
        traceability.
    """
    np = _try_import_numpy()

    rows: list[list[float]] = []
    labels: list[int] = []
    shas: list[str] = []

    for sample in samples:
        fd = sample["features"]
        row = []
        for col in FEATURE_COLUMNS:
            val = fd.get(col, 0)
            # Cast booleans to int
            if isinstance(val, bool):
                val = int(val)
            elif val is None:
                val = 0.0
            row.append(float(val))
        rows.append(row)
        labels.append(int(sample.get("label", 0)))
        shas.append(sample.get("sha", ""))

    X = np.array(rows, dtype=np.float64)
    y = np.array(labels, dtype=np.int32)

    logger.info(
        "Feature matrix built: X=%s  y=%s  positive_rate=%.2f%%",
        X.shape, y.shape,
        (y.sum() / len(y) * 100) if len(y) > 0 else 0,
    )
    return X, y, shas


# ---------------------------------------------------------------------------
# Step 3 — Preprocess  (AI_Model_Engineering.md §7)
# ---------------------------------------------------------------------------

def preprocess(
    X,
    y,
    *,
    fit: bool = True,
    scaler=None,
    imputer=None,
):
    """
    Apply preprocessing per §7:
        - Median imputation for missing (NaN) values
        - StandardScaler normalisation
        - Remove corrupted samples (rows with all zeros or NaN)

    Args:
        X, y:     Feature matrix and labels.
        fit:      If ``True``, fit scaler + imputer on this data.
                  If ``False``, transform only (use existing fitted objects).
        scaler:   Pre-fitted ``StandardScaler`` (required when ``fit=False``).
        imputer:  Pre-fitted ``SimpleImputer`` (required when ``fit=False``).

    Returns:
        ``(X_clean, y_clean, scaler, imputer)``
    """
    np = _try_import_numpy()
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler

    # Replace infinities with NaN so imputer can handle them
    X = np.where(np.isinf(X), np.nan, X)

    # --- Remove corrupted samples (all-zero or all-NaN rows) ---
    valid_mask = ~np.all(np.isnan(X) | (X == 0), axis=1)
    if not np.all(valid_mask):
        removed = int((~valid_mask).sum())
        logger.info("Removing %d corrupted samples.", removed)
        X = X[valid_mask]
        y = y[valid_mask]

    # --- Median imputation ---
    if fit:
        imputer = SimpleImputer(strategy="median")
        X = imputer.fit_transform(X)
    else:
        if imputer is None:
            raise ValueError("imputer must be provided when fit=False")
        X = imputer.transform(X)

    # --- StandardScaler ---
    if fit:
        scaler = StandardScaler()
        X = scaler.fit_transform(X)
    else:
        if scaler is None:
            raise ValueError("scaler must be provided when fit=False")
        X = scaler.transform(X)

    logger.info("Preprocessing complete. X=%s", X.shape)
    return X, y, scaler, imputer


# ---------------------------------------------------------------------------
# Step 4 — Train / test split
# ---------------------------------------------------------------------------

def split_data(X, y, test_size: float = 0.2, random_state: int = 42):
    """
    Stratified train / test split.

    Returns ``(X_train, X_test, y_train, y_test)``.
    """
    from sklearn.model_selection import train_test_split

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y,
    )
    logger.info(
        "Split: train=%d  test=%d  (positive_rate train=%.2f%% test=%.2f%%)",
        len(y_train), len(y_test),
        (y_train.sum() / len(y_train) * 100) if len(y_train) > 0 else 0,
        (y_test.sum() / len(y_test) * 100) if len(y_test) > 0 else 0,
    )
    return X_train, X_test, y_train, y_test


# ---------------------------------------------------------------------------
# Export to CSV  (for inspection / notebook work)
# ---------------------------------------------------------------------------

def export_to_csv(
    samples: list[dict],
    output_path: str | Path = "training_data.csv",
) -> Path:
    """
    Save the training samples as a CSV file for manual inspection or
    external training in a Jupyter notebook.
    """
    import csv

    output_path = Path(output_path)
    header = ["sha", "repository", "label"] + FEATURE_COLUMNS

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for sample in samples:
            fd = sample["features"]
            row = [
                sample["sha"],
                sample.get("repository_full_name", ""),
                sample.get("label", 0),
            ]
            for col in FEATURE_COLUMNS:
                val = fd.get(col, 0)
                if isinstance(val, bool):
                    val = int(val)
                row.append(val)
            writer.writerow(row)

    logger.info("Exported %d samples to %s", len(samples), output_path)
    return output_path
