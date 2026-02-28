"""
Production model predictor  (AI_Model_Engineering.md §11).

Loads a trained model at startup and provides a ``predict()`` function that
the predictions router can call.  Falls back to the rule-based engine when
no trained model is available.

Production inference flow (§11):
    1.  Backend loads model at startup
    2.  Feature extraction runs  (``risk_engine.extract_features``)
    3.  Model predicts probability
    4.  Probability converted to risk score  (0–100)
    5.  Prediction stored in database
    6.  Response returned to frontend
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from app.ml.data_pipeline import FEATURE_COLUMNS
from app.ml.trainer import MODELS_DIR, load_model
from app.models import RiskLevel
from app.services.risk_engine import CommitFeatures, RiskResult, calculate_risk

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Singleton model holder — loaded once at import / startup
# ---------------------------------------------------------------------------

class ModelPredictor:
    """
    Holds a loaded ML model and provides prediction methods.

    Designed to be instantiated once and reused across requests.
    """

    def __init__(self):
        self._bundle: Optional[dict] = None
        self._model = None
        self._scaler = None
        self._imputer = None
        self._feature_columns: list[str] = FEATURE_COLUMNS
        self._version: str = "rule-v1"
        self._model_name: str = "rule_based"
        self._available: bool = False

    @property
    def is_ml_available(self) -> bool:
        """``True`` when a trained ML model is loaded."""
        return self._available

    @property
    def version(self) -> str:
        return self._version

    @property
    def model_name(self) -> str:
        return self._model_name

    def load(self, path: Optional[str | Path] = None) -> bool:
        """
        Attempt to load a trained model from disk.

        Args:
            path: Explicit path to a ``.pkl`` bundle.
                  Defaults to ``models/latest.pkl``.

        Returns:
            ``True`` if a model was loaded successfully.
        """
        try:
            bundle = load_model(path)
            self._bundle = bundle
            self._model = bundle["model"]
            self._scaler = bundle.get("scaler")
            self._imputer = bundle.get("imputer")
            self._feature_columns = bundle.get("feature_columns", FEATURE_COLUMNS)
            self._version = bundle.get("version", "ml-v1")
            self._model_name = bundle.get("model_name", "unknown")
            self._available = True

            metrics = bundle.get("metrics", {})
            logger.info(
                "ML model loaded: %s (%s)  ROC-AUC=%.4f",
                self._model_name,
                self._version,
                metrics.get("roc_auc", 0),
            )
            return True
        except FileNotFoundError:
            logger.info(
                "No trained model found at %s — using rule-based engine.",
                path or MODELS_DIR / "latest.pkl",
            )
            self._available = False
            return False
        except Exception as exc:
            logger.error("Failed to load model: %s", exc)
            self._available = False
            return False

    def predict(self, features: CommitFeatures) -> RiskResult:
        """
        Predict risk for a commit.

        - If an ML model is loaded → use it  (§11 flow).
        - Otherwise → fall back to the rule-based engine.

        Returns:
            A :class:`RiskResult` with risk_score, risk_level, confidence,
            features, and score_breakdown.
        """
        if not self._available:
            return calculate_risk(features)

        return self._predict_ml(features)

    def _predict_ml(self, features: CommitFeatures) -> RiskResult:
        """Run inference with the ML model."""
        # 1. Build feature vector in the correct column order
        fd = features.to_dict()
        row = []
        for col in self._feature_columns:
            val = fd.get(col, 0)
            if isinstance(val, bool):
                val = int(val)
            elif val is None:
                val = 0.0
            row.append(float(val))

        X = np.array([row], dtype=np.float64)

        # 2. Preprocess  (impute + scale) using the fitted objects
        if self._imputer is not None:
            X = self._imputer.transform(X)
        if self._scaler is not None:
            X = self._scaler.transform(X)

        # 3. Predict probability
        try:
            proba = self._model.predict_proba(X)[0]
            # proba = [P(safe), P(risky)]
            risk_probability = float(proba[1]) if len(proba) > 1 else float(proba[0])
        except Exception:
            # Some models may not have predict_proba
            pred = self._model.predict(X)[0]
            risk_probability = float(pred)

        # 4. Convert probability to risk score (0–100)
        risk_score = round(risk_probability * 100, 2)

        # 5. Determine risk level
        if risk_score >= 60:
            level = RiskLevel.HIGH
        elif risk_score >= 30:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        # 6. Confidence from the model's certainty
        confidence = round(max(risk_probability, 1 - risk_probability), 4)

        # Also run the rule-based engine to get the interpretable breakdown
        rule_result = calculate_risk(features)

        logger.info(
            "ML prediction: score=%.1f (%s) confidence=%.2f  [%s %s]",
            risk_score, level.value, confidence, self._model_name, self._version,
        )

        return RiskResult(
            risk_score=risk_score,
            risk_level=level,
            confidence=confidence,
            features=features,
            score_breakdown=rule_result.score_breakdown,  # keep interpretable breakdown
        )

    def get_info(self) -> dict:
        """Return model metadata for the API."""
        if not self._available:
            return {
                "engine": "rule_based",
                "version": "rule-v1",
                "ml_available": False,
            }
        metrics = self._bundle.get("metrics", {}) if self._bundle else {}
        return {
            "engine": "ml",
            "model_name": self._model_name,
            "version": self._version,
            "ml_available": True,
            "roc_auc": metrics.get("roc_auc", 0),
            "accuracy": metrics.get("accuracy", 0),
            "f1_score": metrics.get("f1_score", 0),
            "trained_at": self._bundle.get("trained_at", "") if self._bundle else "",
        }


# ---------------------------------------------------------------------------
# Global singleton  — loaded at startup in main.py
# ---------------------------------------------------------------------------

predictor = ModelPredictor()


def init_predictor(model_path: Optional[str | Path] = None) -> ModelPredictor:
    """
    Initialise the global predictor.  Called from the FastAPI lifespan
    handler in ``main.py``.
    """
    predictor.load(model_path)
    return predictor
