"""
Synthetic training data generator.

Produces realistic-looking commit feature data with labels so the ML model
can be trained and validated even before enough real GitHub data has been
collected.

The distributions are designed to mimic real-world patterns:
    - Most commits are safe  (label=0, ~70%)
    - Risky commits tend to be larger, touch more files, and happen at odd hours
"""

from __future__ import annotations

import logging
import random
from typing import Optional

from app.ml.data_pipeline import FEATURE_COLUMNS

logger = logging.getLogger(__name__)


def generate_synthetic_samples(
    count: int = 500,
    positive_rate: float = 0.3,
    seed: int = 42,
) -> list[dict]:
    """
    Generate *count* synthetic training samples.

    Args:
        count:          Total number of samples.
        positive_rate:  Fraction of risky (label=1) samples.
        seed:           Random seed for reproducibility.

    Returns:
        List of sample dicts compatible with ``build_feature_matrix()``.
    """
    rng = random.Random(seed)
    samples: list[dict] = []
    n_risky = int(count * positive_rate)

    for i in range(count):
        is_risky = i < n_risky
        features = _generate_features(rng, is_risky)

        samples.append({
            "sha": f"synthetic_{i:06d}",
            "repository_full_name": "synthetic/repo",
            "features": features,
            "label": 1 if is_risky else 0,
        })

    rng.shuffle(samples)

    logger.info(
        "Generated %d synthetic samples (%.0f%% risky).",
        count, positive_rate * 100,
    )
    return samples


def _generate_features(rng: random.Random, is_risky: bool) -> dict:
    """Generate a single feature dict with realistic distributions."""

    if is_risky:
        # Risky commits: large, complex, odd hours, inexperienced dev
        lines_added = rng.randint(100, 1500)
        lines_deleted = rng.randint(20, 500)
        files_changed = rng.randint(5, 50)
        avg_cc = rng.uniform(5, 30)
        max_cc = avg_cc + rng.uniform(0, 15)
        mi = rng.uniform(10, 60)
        total_prior = rng.randint(0, 30)
        bug_rate = rng.uniform(0.1, 0.6)
        hour = rng.choice([0, 1, 2, 3, 22, 23, 14, 15, 16])
        day = rng.choice([4, 5, 6, 0, 1, 2, 3])  # bias toward Fri/weekend
        risky_kw = rng.randint(1, 5)
        msg_len = rng.randint(5, 40)
        test_pct = rng.uniform(0, 0.15)
    else:
        # Safe commits: small, clean, business hours, experienced dev
        lines_added = rng.randint(1, 200)
        lines_deleted = rng.randint(0, 80)
        files_changed = rng.randint(1, 10)
        avg_cc = rng.uniform(1, 8)
        max_cc = avg_cc + rng.uniform(0, 5)
        mi = rng.uniform(60, 100)
        total_prior = rng.randint(20, 500)
        bug_rate = rng.uniform(0, 0.1)
        hour = rng.randint(8, 18)
        day = rng.randint(0, 4)  # weekday
        risky_kw = 0 if rng.random() > 0.15 else rng.randint(1, 2)
        msg_len = rng.randint(20, 120)
        test_pct = rng.uniform(0.1, 0.6)

    total_lines = lines_added + lines_deleted
    weekend = day >= 5
    commit_freq = rng.uniform(0.5, 15.0)
    time_since = rng.uniform(0.5, 200.0)
    contributor_count = rng.randint(1, 20)
    open_issues = rng.randint(0, 100)
    commit_velocity = rng.uniform(1, 50)
    file_types = rng.randint(1, min(files_changed, 8))
    cc_blocks = rng.randint(1, files_changed * 3)
    halstead = avg_cc * rng.uniform(10, 50)
    python_files = rng.randint(0, files_changed)

    # Add some noise so the boundary isn't perfect
    if rng.random() < 0.1:
        # 10% noise: flip some features
        lines_added = rng.randint(1, 1500)
        hour = rng.randint(0, 23)

    features = {
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "total_lines_changed": total_lines,
        "files_changed": files_changed,
        "file_types_count": file_types,
        "percentage_test_files": round(test_pct, 4),
        "avg_cyclomatic_complexity": round(avg_cc, 2),
        "max_cyclomatic_complexity": round(max_cc, 2),
        "avg_maintainability_index": round(mi, 2),
        "total_cc_blocks": cc_blocks,
        "avg_halstead_volume": round(halstead, 2),
        "complexity_python_files": python_files,
        "total_prior_commits": total_prior,
        "previous_bug_rate": round(bug_rate, 4),
        "commit_frequency": round(commit_freq, 4),
        "time_since_last_commit": round(time_since, 2),
        "repo_size": rng.randint(100, 50000),
        "contributor_count": contributor_count,
        "open_issues_count": open_issues,
        "commit_velocity": round(commit_velocity, 2),
        "day_of_week": day,
        "hour_of_day": hour,
        "weekend_flag": weekend,
        "code_churn_ratio": round(lines_added / (lines_deleted + 1), 4),
        "risk_density": round(files_changed / (total_lines + 1), 6),
        "developer_risk_score": round(bug_rate * total_lines, 4),
        "message_length": msg_len,
        "has_risky_keywords": risky_kw > 0,
        "risky_keyword_count": risky_kw,
    }

    return features
