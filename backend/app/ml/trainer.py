"""
Model trainer  (AI_Model_Engineering.md §8–9).

Trains an ML model on labeled commit data, evaluates it, and saves a
versioned pickle file to disk.

Baseline:  Logistic Regression  (§8)
Future:    Random Forest, Gradient Boosting, XGBoost, LightGBM  (§9)

Usage (from the backend directory)::

    python -m app.ml.trainer                # default: logistic regression
    python -m app.ml.trainer --model rf     # random forest
    python -m app.ml.trainer --model gb     # gradient boosting
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Directory where trained models are stored
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"


# ---------------------------------------------------------------------------
# Evaluation result
# ---------------------------------------------------------------------------

@dataclass
class TrainingResult:
    """Stores training metrics and metadata."""
    model_name: str              # e.g. "logistic_regression"
    model_version: str           # e.g. "ml-v1"
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    roc_auc: float = 0.0
    train_samples: int = 0
    test_samples: int = 0
    positive_rate: float = 0.0   # % of risky commits in dataset
    training_time_seconds: float = 0.0
    feature_columns: list[str] = field(default_factory=list)
    model_path: str = ""
    trained_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        return (
            f"\n{'='*60}\n"
            f"  Model Training Results\n"
            f"{'='*60}\n"
            f"  Model:          {self.model_name}\n"
            f"  Version:        {self.model_version}\n"
            f"  Train samples:  {self.train_samples}\n"
            f"  Test samples:   {self.test_samples}\n"
            f"  Positive rate:  {self.positive_rate:.2f}%\n"
            f"  ────────────────────────────\n"
            f"  Accuracy:       {self.accuracy:.4f}\n"
            f"  Precision:      {self.precision:.4f}\n"
            f"  Recall:         {self.recall:.4f}\n"
            f"  F1 Score:       {self.f1_score:.4f}\n"
            f"  ROC AUC:        {self.roc_auc:.4f}\n"
            f"  ────────────────────────────\n"
            f"  Training time:  {self.training_time_seconds:.2f}s\n"
            f"  Model saved to: {self.model_path}\n"
            f"  Trained at:     {self.trained_at}\n"
            f"{'='*60}\n"
        )


# ---------------------------------------------------------------------------
# Model builders
# ---------------------------------------------------------------------------

def _build_logistic_regression():
    """Logistic Regression — baseline model (§8)."""
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(
        class_weight="balanced",   # handles class imbalance (§7)
        max_iter=1000,
        random_state=42,
        solver="lbfgs",
    )


def _build_random_forest():
    """Random Forest (§9)."""
    from sklearn.ensemble import RandomForestClassifier
    return RandomForestClassifier(
        n_estimators=100,
        class_weight="balanced",
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )


def _build_gradient_boosting():
    """Gradient Boosting (§9)."""
    from sklearn.ensemble import GradientBoostingClassifier
    return GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
    )


MODEL_BUILDERS = {
    "logistic_regression": _build_logistic_regression,
    "lr": _build_logistic_regression,
    "random_forest": _build_random_forest,
    "rf": _build_random_forest,
    "gradient_boosting": _build_gradient_boosting,
    "gb": _build_gradient_boosting,
}


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------

def evaluate_model(model, X_test, y_test) -> dict:
    """
    Run all evaluation metrics from §8:
    Accuracy, Precision, Recall, F1, ROC AUC.
    """
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    y_pred = model.predict(X_test)

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1_score": f1_score(y_test, y_pred, zero_division=0),
    }

    # ROC AUC requires probability scores
    try:
        y_proba = model.predict_proba(X_test)[:, 1]
        metrics["roc_auc"] = roc_auc_score(y_test, y_proba)
    except Exception:
        metrics["roc_auc"] = 0.0

    return metrics


# ---------------------------------------------------------------------------
# Save / Load model artifacts
# ---------------------------------------------------------------------------

def _next_version(model_name: str) -> str:
    """Determine the next version number (ml-v1, ml-v2, …)."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(MODELS_DIR.glob(f"{model_name}_v*.pkl"))
    if not existing:
        return "ml-v1"
    versions = []
    for p in existing:
        # Extract version number from filename like "logistic_regression_v3.pkl"
        stem = p.stem  # e.g. "logistic_regression_v3"
        parts = stem.rsplit("_v", 1)
        if len(parts) == 2 and parts[1].isdigit():
            versions.append(int(parts[1]))
    next_v = max(versions, default=0) + 1
    return f"ml-v{next_v}"


def save_model(
    model,
    scaler,
    imputer,
    model_name: str,
    version: str,
    feature_columns: list[str],
    training_result: TrainingResult,
) -> Path:
    """
    Save the trained model + preprocessing artifacts as a single pickle
    bundle.  This is what the production predictor loads at startup (§11).

    Stored structure::

        {
            "model": <fitted sklearn estimator>,
            "scaler": <fitted StandardScaler>,
            "imputer": <fitted SimpleImputer>,
            "feature_columns": [...],
            "model_name": "logistic_regression",
            "version": "ml-v1",
            "metrics": { ... },
            "trained_at": "2026-02-28T...",
        }
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{model_name}_v{version.split('-v')[-1]}.pkl"
    path = MODELS_DIR / filename

    bundle = {
        "model": model,
        "scaler": scaler,
        "imputer": imputer,
        "feature_columns": feature_columns,
        "model_name": model_name,
        "version": version,
        "metrics": training_result.to_dict(),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(path, "wb") as f:
        pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)

    # Also save a "latest" symlink / copy
    latest_path = MODELS_DIR / "latest.pkl"
    with open(latest_path, "wb") as f:
        pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)

    logger.info("Model saved: %s  (%s)", path, version)
    return path


def load_model(path: Optional[str | Path] = None) -> dict:
    """
    Load a trained model bundle from disk.

    If *path* is ``None``, loads ``models/latest.pkl``.

    Returns the bundle dict (see :func:`save_model`).
    """
    if path is None:
        path = MODELS_DIR / "latest.pkl"
    else:
        path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"No model found at {path}")

    with open(path, "rb") as f:
        bundle = pickle.load(f)

    logger.info(
        "Loaded model: %s (version=%s)",
        bundle.get("model_name", "?"),
        bundle.get("version", "?"),
    )
    return bundle


# ---------------------------------------------------------------------------
# Main training function
# ---------------------------------------------------------------------------

def train(
    X_train,
    y_train,
    X_test,
    y_test,
    model_type: str = "logistic_regression",
    feature_columns: Optional[list[str]] = None,
    scaler=None,
    imputer=None,
) -> TrainingResult:
    """
    Train a model, evaluate it, save it, and return the results.

    This is the primary entry point for the training pipeline.

    Args:
        X_train, y_train:  Training split (preprocessed).
        X_test, y_test:    Test split (preprocessed).
        model_type:        One of ``MODEL_BUILDERS`` keys.
        feature_columns:   Ordered list of feature names.
        scaler / imputer:  Fitted preprocessing objects to bundle with model.

    Returns:
        :class:`TrainingResult` with all evaluation metrics.
    """
    import numpy as np

    if model_type not in MODEL_BUILDERS:
        raise ValueError(
            f"Unknown model type '{model_type}'. "
            f"Available: {list(MODEL_BUILDERS.keys())}"
        )

    builder = MODEL_BUILDERS[model_type]
    # Normalise the display name
    canonical_name = {
        "lr": "logistic_regression",
        "rf": "random_forest",
        "gb": "gradient_boosting",
    }.get(model_type, model_type)

    logger.info("Training %s on %d samples …", canonical_name, len(y_train))

    # --- Build & fit ---
    model = builder()
    start = time.time()
    model.fit(X_train, y_train)
    elapsed = time.time() - start

    # --- Evaluate ---
    metrics = evaluate_model(model, X_test, y_test)
    version = _next_version(canonical_name)

    result = TrainingResult(
        model_name=canonical_name,
        model_version=version,
        accuracy=round(metrics["accuracy"], 4),
        precision=round(metrics["precision"], 4),
        recall=round(metrics["recall"], 4),
        f1_score=round(metrics["f1_score"], 4),
        roc_auc=round(metrics["roc_auc"], 4),
        train_samples=len(y_train),
        test_samples=len(y_test),
        positive_rate=round(float(np.concatenate([y_train, y_test]).mean()) * 100, 2),
        training_time_seconds=round(elapsed, 2),
        feature_columns=feature_columns or [],
        trained_at=datetime.now(timezone.utc).isoformat(),
    )

    # --- Save ---
    from app.ml.data_pipeline import FEATURE_COLUMNS
    cols = feature_columns or FEATURE_COLUMNS

    model_path = save_model(
        model, scaler, imputer, canonical_name, version, cols, result,
    )
    result.model_path = str(model_path)

    logger.info(result.summary())

    # --- Check MVP target ---
    target_auc = 0.65
    if result.roc_auc >= target_auc:
        logger.info("✔ ROC AUC %.4f meets MVP target (>= %.2f)", result.roc_auc, target_auc)
    else:
        logger.warning(
            "✘ ROC AUC %.4f below MVP target (>= %.2f). "
            "Consider collecting more data or trying advanced models.",
            result.roc_auc, target_auc,
        )

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """
    Full training pipeline:  DB → features → preprocess → train → save.

    Can also train on synthetic data when the DB has insufficient samples.
    """
    import argparse
    import sys

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Train the AI risk prediction model",
    )
    parser.add_argument(
        "--model", "-m",
        default="logistic_regression",
        choices=list(MODEL_BUILDERS.keys()),
        help="Model type to train (default: logistic_regression)",
    )
    parser.add_argument(
        "--synthetic", "-s",
        action="store_true",
        help="Use synthetic data if DB has < 50 samples",
    )
    parser.add_argument(
        "--synthetic-count",
        type=int,
        default=500,
        help="Number of synthetic samples to generate (default: 500)",
    )
    parser.add_argument(
        "--csv-export",
        type=str,
        default=None,
        help="Export training data to CSV before training",
    )
    args = parser.parse_args()

    # Try loading from database first
    samples = []
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        from app.ml.data_pipeline import collect_training_samples
        samples = collect_training_samples(db)
        db.close()
    except Exception as exc:
        logger.warning("Could not load from database: %s", exc)

    # If not enough data, use synthetic
    if len(samples) < 50:
        if args.synthetic or len(samples) == 0:
            logger.info(
                "Only %d DB samples. Generating %d synthetic samples for training.",
                len(samples), args.synthetic_count,
            )
            from app.ml.synthetic_data import generate_synthetic_samples
            synthetic = generate_synthetic_samples(args.synthetic_count)
            samples.extend(synthetic)
        else:
            logger.error(
                "Only %d samples in DB — need at least 50 for training. "
                "Use --synthetic flag to generate synthetic data, or sync "
                "more repositories first.",
                len(samples),
            )
            sys.exit(1)

    # Export CSV if requested
    if args.csv_export:
        from app.ml.data_pipeline import export_to_csv
        export_to_csv(samples, args.csv_export)

    # Build feature matrix
    from app.ml.data_pipeline import (
        FEATURE_COLUMNS,
        build_feature_matrix,
        preprocess,
        split_data,
    )

    X, y, shas = build_feature_matrix(samples)

    if len(X) < 20:
        logger.error("Need at least 20 samples, got %d.", len(X))
        sys.exit(1)

    # Preprocess
    X, y, scaler, imputer = preprocess(X, y, fit=True)

    # Split
    X_train, X_test, y_train, y_test = split_data(X, y)

    # Train
    result = train(
        X_train, y_train,
        X_test, y_test,
        model_type=args.model,
        feature_columns=FEATURE_COLUMNS,
        scaler=scaler,
        imputer=imputer,
    )

    print(result.summary())


if __name__ == "__main__":
    main()
