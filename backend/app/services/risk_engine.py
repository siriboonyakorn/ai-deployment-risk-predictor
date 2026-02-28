"""
Rule-based risk scoring engine  (MVP / v1).

Implements the feature engineering and risk-score formula described in
*AI_Model_Engineering.md* §5–6.  Every feature computed here is stored
alongside the prediction so the same data can later train the ML model
(logistic regression → gradient boosting → etc.).

When the ML model is ready, this module will be replaced by a call to
``model.predict_proba(features)`` but the **feature extraction** functions
remain shared.
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.models import RiskLevel
from app.services.code_analysis import CommitComplexityReport

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Feature dataclass — aligned with AI_Model_Engineering.md §5-6
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CommitFeatures:
    """
    All features extracted for a single commit.

    Sections match AI_Model_Engineering.md §5 (Code-Level, Developer-Level,
    Repository-Level, Temporal) and §6 (Derived Features).
    """

    # ── Code-Level Features ────────────────────────────────────────────
    lines_added: int = 0
    lines_deleted: int = 0
    total_lines_changed: int = 0
    files_changed: int = 0
    file_types_count: int = 0        # distinct extensions in changed files
    percentage_test_files: float = 0.0  # 0–1

    # ── Complexity Features (from radon) ───────────────────────────────
    avg_cyclomatic_complexity: float = 0.0
    max_cyclomatic_complexity: float = 0.0
    avg_maintainability_index: float = 100.0
    total_cc_blocks: int = 0
    cc_rank: str = "A"
    avg_halstead_volume: float = 0.0
    complexity_python_files: int = 0

    # ── Developer-Level Features ───────────────────────────────────────
    total_prior_commits: int = 0
    previous_bug_rate: float = 0.0   # 0–1
    commit_frequency: float = 0.0    # commits/day (last 30 days)
    time_since_last_commit: float = 0.0  # hours

    # ── Repository-Level Features ──────────────────────────────────────
    repo_size: int = 0               # KB
    contributor_count: int = 0
    open_issues_count: int = 0
    commit_velocity: float = 0.0     # commits/week (repo-wide)

    # ── Temporal Features ──────────────────────────────────────────────
    day_of_week: int = 0             # 0=Mon … 6=Sun
    hour_of_day: int = 0             # 0-23
    weekend_flag: bool = False

    # ── Derived Features (AI_Model_Engineering.md §6) ──────────────────
    code_churn_ratio: float = 0.0    # lines_added / (lines_deleted + 1)
    risk_density: float = 0.0        # files_changed / (total_lines + 1)
    developer_risk_score: float = 0.0  # previous_bug_rate × total_lines

    # ── Commit-message Features ────────────────────────────────────────
    message_length: int = 0
    has_risky_keywords: bool = False
    risky_keyword_count: int = 0

    def to_dict(self) -> dict:
        """Serialise to a JSON-safe dict for storage in ``features_json``."""
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# ═══════════════════════════════════════════════════════════════════════════
# Feature extraction
# ═══════════════════════════════════════════════════════════════════════════

_RISKY_KEYWORDS = [
    "fix", "hotfix", "urgent", "hack", "workaround", "temp", "wip",
    "revert", "rollback", "patch", "broken", "bug", "crash", "critical",
    "emergency", "quick fix", "dirty", "todo", "fixme",
]

_TEST_PATTERNS = re.compile(
    r"(test_|_test\.py|tests/|spec/|__tests__|\.test\.|\.spec\.)",
    re.IGNORECASE,
)


def extract_features(
    *,
    lines_added: int = 0,
    lines_deleted: int = 0,
    files_changed: int = 0,
    commit_message: Optional[str] = None,
    committed_at: Optional[datetime] = None,
    author_email: Optional[str] = None,
    # Per-file info  (filename, content)  — used for complexity + file-type analysis
    changed_files: Optional[list[tuple[str, str]]] = None,
    # Developer history  (provided by caller from DB queries)
    total_prior_commits: int = 0,
    previous_bug_rate: float = 0.0,
    commit_frequency: float = 0.0,
    time_since_last_commit: float = 0.0,
    # Repository-level  (provided by caller)
    repo_size: int = 0,
    contributor_count: int = 0,
    open_issues_count: int = 0,
    commit_velocity: float = 0.0,
    # Optional pre-computed complexity report
    complexity_report: Optional[CommitComplexityReport] = None,
) -> CommitFeatures:
    """
    Build a :class:`CommitFeatures` from raw commit data.

    This is the single entry-point for feature engineering.  All downstream
    consumers (rule-based scorer *and* future ML model) use this function.
    """
    f = CommitFeatures()

    # ── Code-level ─────────────────────────────────────────────────────
    f.lines_added = lines_added
    f.lines_deleted = lines_deleted
    f.total_lines_changed = lines_added + lines_deleted
    f.files_changed = files_changed

    if changed_files:
        extensions = set()
        test_count = 0
        for fname, _ in changed_files:
            ext = _file_ext(fname)
            if ext:
                extensions.add(ext)
            if _TEST_PATTERNS.search(fname):
                test_count += 1
        f.file_types_count = len(extensions)
        f.percentage_test_files = (
            round(test_count / len(changed_files), 4) if changed_files else 0.0
        )

    # ── Complexity (radon) ─────────────────────────────────────────────
    if complexity_report:
        f.avg_cyclomatic_complexity = complexity_report.avg_cyclomatic_complexity
        f.max_cyclomatic_complexity = complexity_report.max_cyclomatic_complexity
        f.avg_maintainability_index = complexity_report.avg_maintainability_index
        f.total_cc_blocks = complexity_report.total_cc_blocks
        f.cc_rank = complexity_report.overall_cc_rank
        f.avg_halstead_volume = complexity_report.avg_halstead_volume
        f.complexity_python_files = complexity_report.python_files_analysed

    # ── Developer-level ────────────────────────────────────────────────
    f.total_prior_commits = total_prior_commits
    f.previous_bug_rate = previous_bug_rate
    f.commit_frequency = commit_frequency
    f.time_since_last_commit = time_since_last_commit

    # ── Repository-level ───────────────────────────────────────────────
    f.repo_size = repo_size
    f.contributor_count = contributor_count
    f.open_issues_count = open_issues_count
    f.commit_velocity = commit_velocity

    # ── Temporal ───────────────────────────────────────────────────────
    if committed_at:
        f.day_of_week = committed_at.weekday()
        f.hour_of_day = committed_at.hour
        f.weekend_flag = committed_at.weekday() >= 5

    # ── Commit-message ─────────────────────────────────────────────────
    if commit_message:
        f.message_length = len(commit_message)
        msg_lower = commit_message.lower()
        matches = [kw for kw in _RISKY_KEYWORDS if kw in msg_lower]
        f.has_risky_keywords = len(matches) > 0
        f.risky_keyword_count = len(matches)

    # ── Derived features (AI_Model_Engineering.md §6) ──────────────────
    f.code_churn_ratio = round(lines_added / (lines_deleted + 1), 4)
    f.risk_density = round(
        files_changed / (f.total_lines_changed + 1), 6
    )
    f.developer_risk_score = round(
        previous_bug_rate * f.total_lines_changed, 4
    )

    return f


# ═══════════════════════════════════════════════════════════════════════════
# Rule-based risk scoring  (replaces the old _calculate_risk)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class RiskResult:
    """Output of the rule-based scorer."""
    risk_score: float          # 0–100
    risk_level: RiskLevel
    confidence: float          # 0–1
    features: CommitFeatures
    score_breakdown: dict = field(default_factory=dict)  # per-category scores

    def to_dict(self) -> dict:
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "confidence": self.confidence,
            "score_breakdown": self.score_breakdown,
            "features": self.features.to_dict(),
        }


def calculate_risk(features: CommitFeatures) -> RiskResult:
    """
    Compute a risk score (0–100) from extracted features using a weighted
    rule-based formula.

    The score is decomposed into sub-categories so it's interpretable and
    can be used for debugging / UI display.

    **Weight distribution** (sums to 100):
        - Code-volume       : 25 points
        - Code-complexity   : 20 points
        - Commit-message    : 10 points
        - Developer history : 15 points
        - Temporal risk     : 10 points
        - File-spread       : 10 points
        - Derived / churn   : 10 points

    When the ML model is trained, it will replace this function entirely,
    but the *feature extraction* (above) is shared.
    """
    breakdown: dict[str, float] = {}

    # ─── 1. Code Volume  (max 25) ─────────────────────────────────────
    total = features.total_lines_changed
    if total > 1000:
        vol = 25.0
    elif total > 500:
        vol = 20.0
    elif total > 200:
        vol = 14.0
    elif total > 100:
        vol = 9.0
    elif total > 50:
        vol = 5.0
    else:
        vol = max(0.0, total * 0.05)
    breakdown["code_volume"] = round(vol, 2)

    # ─── 2. Code Complexity — radon  (max 20) ─────────────────────────
    cc = features.avg_cyclomatic_complexity
    mi = features.avg_maintainability_index
    comp_score = 0.0

    # CC contribution (0-12)
    if cc > 25:
        comp_score += 12.0
    elif cc > 15:
        comp_score += 9.0
    elif cc > 10:
        comp_score += 6.0
    elif cc > 5:
        comp_score += 3.0
    else:
        comp_score += max(0.0, cc * 0.4)

    # MI contribution (0-8) — lower MI = higher risk
    if mi < 20:
        comp_score += 8.0
    elif mi < 40:
        comp_score += 6.0
    elif mi < 60:
        comp_score += 4.0
    elif mi < 80:
        comp_score += 2.0
    else:
        comp_score += 0.0

    breakdown["code_complexity"] = round(min(comp_score, 20.0), 2)

    # ─── 3. Commit Message  (max 10) ──────────────────────────────────
    msg_score = 0.0
    if features.has_risky_keywords:
        msg_score += min(features.risky_keyword_count * 3.0, 8.0)
    if features.message_length < 10:
        msg_score += 2.0  # very short / vague message
    breakdown["commit_message"] = round(min(msg_score, 10.0), 2)

    # ─── 4. Developer History  (max 15) ────────────────────────────────
    dev_score = 0.0

    # High bug rate
    if features.previous_bug_rate > 0.3:
        dev_score += 8.0
    elif features.previous_bug_rate > 0.15:
        dev_score += 5.0
    elif features.previous_bug_rate > 0.05:
        dev_score += 2.0

    # Low experience (few prior commits)
    if features.total_prior_commits < 5:
        dev_score += 5.0
    elif features.total_prior_commits < 20:
        dev_score += 2.0

    # Commit frequency spike / anomaly (very high = potential code dump)
    if features.commit_frequency > 20:
        dev_score += 2.0

    breakdown["developer_history"] = round(min(dev_score, 15.0), 2)

    # ─── 5. Temporal Risk  (max 10) ────────────────────────────────────
    time_score = 0.0
    if features.weekend_flag:
        time_score += 4.0
    # Late-night commits (22:00 – 05:00)
    if features.hour_of_day >= 22 or features.hour_of_day < 5:
        time_score += 4.0
    # Friday afternoon deployments
    if features.day_of_week == 4 and features.hour_of_day >= 14:
        time_score += 3.0
    breakdown["temporal_risk"] = round(min(time_score, 10.0), 2)

    # ─── 6. File Spread  (max 10) ──────────────────────────────────────
    fc = features.files_changed
    if fc > 30:
        spread = 10.0
    elif fc > 20:
        spread = 7.0
    elif fc > 10:
        spread = 5.0
    elif fc > 5:
        spread = 3.0
    else:
        spread = max(0.0, fc * 0.4)

    # Bonus: many file types = cross-cutting change
    if features.file_types_count > 5:
        spread += 2.0

    # Penalty reduction: lots of test files is **good**
    if features.percentage_test_files > 0.3:
        spread = max(0.0, spread - 3.0)

    breakdown["file_spread"] = round(min(spread, 10.0), 2)

    # ─── 7. Derived / Churn  (max 10) ──────────────────────────────────
    churn_score = 0.0

    # High churn ratio = lots of new code with little deletion
    if features.code_churn_ratio > 10:
        churn_score += 5.0
    elif features.code_churn_ratio > 5:
        churn_score += 3.0

    # High risk density
    if features.risk_density > 0.5:
        churn_score += 3.0

    # Developer risk score (combined metric)
    if features.developer_risk_score > 100:
        churn_score += 3.0
    elif features.developer_risk_score > 30:
        churn_score += 1.5

    breakdown["derived_churn"] = round(min(churn_score, 10.0), 2)

    # ═══════════════════════════════════════════════════════════════════
    # Aggregate
    # ═══════════════════════════════════════════════════════════════════
    raw_score = sum(breakdown.values())
    risk_score = round(min(raw_score, 100.0), 2)

    # Determine level
    if risk_score >= 60:
        level = RiskLevel.HIGH
    elif risk_score >= 30:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    # Confidence heuristic — higher when we have more data
    data_completeness = _data_completeness(features)
    confidence = round(0.60 + 0.35 * data_completeness, 2)  # 0.60–0.95

    logger.info(
        "Risk score: %.1f (%s) confidence=%.2f  breakdown=%s",
        risk_score, level.value, confidence, breakdown,
    )

    return RiskResult(
        risk_score=risk_score,
        risk_level=level,
        confidence=confidence,
        features=features,
        score_breakdown=breakdown,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _file_ext(filename: str) -> str:
    """Return the lowered file extension (e.g. '.py') or empty string."""
    idx = filename.rfind(".")
    return filename[idx:].lower() if idx >= 0 else ""


def _data_completeness(f: CommitFeatures) -> float:
    """
    Estimate how many feature categories are populated (0–1).

    More data → higher confidence in the rule-based score.
    """
    checks = [
        f.total_lines_changed > 0,         # code-level present
        f.avg_cyclomatic_complexity > 0,    # complexity present
        f.total_prior_commits > 0,          # developer history
        f.contributor_count > 0,            # repo-level
        f.message_length > 0,              # commit message
        f.day_of_week > 0 or f.hour_of_day > 0,  # temporal
    ]
    return sum(checks) / len(checks)
