"""
Code complexity analysis using radon.

Computes cyclomatic complexity (CC) for Python source code obtained from
GitHub commits.  Non-Python files receive a neutral complexity score.

The metrics produced here become features for the ML risk-prediction model
described in AI_Model_Engineering.md §5-6.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy radon import — keeps the module importable even if radon is not yet
# ---------------------------------------------------------------------------
_radon_available: bool = False
try:
    from radon.complexity import cc_visit, cc_rank          # type: ignore[import-untyped]
    from radon.metrics import mi_visit, h_visit             # type: ignore[import-untyped]
    from radon.raw import analyze as raw_analyze            # type: ignore[import-untyped]
    _radon_available = True
except ImportError:
    logger.warning(
        "radon is not installed — code-complexity features will be unavailable. "
        "Install with:  pip install radon"
    )


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class FileComplexity:
    """Complexity results for a single source file."""
    filename: str
    language: str                        # e.g. "python", "javascript", "other"
    cyclomatic_complexity: float = 0.0   # average CC across all blocks
    max_complexity: float = 0.0          # highest CC in one block
    num_blocks: int = 0                  # functions / methods analysed
    cc_rank: str = "A"                   # radon A-F rank (average)
    maintainability_index: float = 100.0 # radon MI (0-100, higher = better)
    loc: int = 0                         # lines of code (logical)
    lloc: int = 0                        # logical lines of code
    sloc: int = 0                        # source lines of code
    comments: int = 0                    # comment lines
    blank: int = 0                       # blank lines
    halstead_volume: float = 0.0         # Halstead volume


@dataclass
class CommitComplexityReport:
    """Aggregated complexity for all files in a commit."""
    sha: str
    total_files_analysed: int = 0
    python_files_analysed: int = 0
    avg_cyclomatic_complexity: float = 0.0
    max_cyclomatic_complexity: float = 0.0
    total_cc_blocks: int = 0
    avg_maintainability_index: float = 100.0
    overall_cc_rank: str = "A"
    total_loc: int = 0
    total_sloc: int = 0
    total_comments: int = 0
    avg_halstead_volume: float = 0.0
    files: list[FileComplexity] = field(default_factory=list)

    def to_features_dict(self) -> dict:
        """Return a flat dict of ML-ready features."""
        return {
            "complexity_avg_cc": self.avg_cyclomatic_complexity,
            "complexity_max_cc": self.max_cyclomatic_complexity,
            "complexity_total_blocks": self.total_cc_blocks,
            "complexity_avg_mi": self.avg_maintainability_index,
            "complexity_cc_rank": self.overall_cc_rank,
            "complexity_total_loc": self.total_loc,
            "complexity_total_sloc": self.total_sloc,
            "complexity_total_comments": self.total_comments,
            "complexity_avg_halstead": self.avg_halstead_volume,
            "complexity_python_files": self.python_files_analysed,
            "complexity_total_files": self.total_files_analysed,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_PYTHON_EXTENSIONS = {".py", ".pyw"}


def _is_python_file(filename: str) -> bool:
    """Check whether a filename looks like a Python module."""
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in _PYTHON_EXTENSIONS)


def _analyse_python_source(source: str, filename: str) -> FileComplexity:
    """
    Run radon analysis on a single Python source string.

    Returns a :class:`FileComplexity` with all available metrics.
    """
    result = FileComplexity(filename=filename, language="python")

    if not _radon_available:
        logger.debug("Skipping complexity for %s — radon not installed", filename)
        return result

    # --- Cyclomatic Complexity ---
    try:
        blocks = cc_visit(source)
        if blocks:
            complexities = [b.complexity for b in blocks]
            result.num_blocks = len(blocks)
            result.cyclomatic_complexity = round(statistics.mean(complexities), 2)
            result.max_complexity = max(complexities)
            # Average rank
            avg_cc = result.cyclomatic_complexity
            result.cc_rank = cc_rank(avg_cc)
    except Exception as exc:
        logger.warning("CC analysis failed for %s: %s", filename, exc)

    # --- Raw metrics (LOC, SLOC, comments, blanks) ---
    try:
        raw = raw_analyze(source)
        result.loc = raw.loc
        result.lloc = raw.lloc
        result.sloc = raw.sloc
        result.comments = raw.comments
        result.blank = raw.blank
    except Exception as exc:
        logger.warning("Raw analysis failed for %s: %s", filename, exc)

    # --- Maintainability Index ---
    try:
        mi = mi_visit(source, multi=True)
        result.maintainability_index = round(mi, 2)
    except Exception as exc:
        logger.warning("MI analysis failed for %s: %s", filename, exc)

    # --- Halstead Volume ---
    try:
        h = h_visit(source)
        # h_visit returns a list of HalsteadReport or a single object
        # depending on the radon version.  Handle both cases.
        if h is not None:
            items = h if isinstance(h, list) else [h]
            volumes = []
            for v in items:
                vol = getattr(v, "volume", None)
                if vol is not None:
                    volumes.append(vol)
            if volumes:
                result.halstead_volume = round(statistics.mean(volumes), 2)
    except Exception as exc:
        logger.debug("Halstead analysis skipped for %s: %s", filename, exc)

    return result


def _analyse_non_python_file(filename: str, content: str) -> FileComplexity:
    """
    For non-Python files we can only count lines.  Cyclomatic complexity
    is left at the neutral default (0).
    """
    lines = content.splitlines() if content else []
    return FileComplexity(
        filename=filename,
        language="other",
        loc=len(lines),
        sloc=sum(1 for ln in lines if ln.strip()),
        blank=sum(1 for ln in lines if not ln.strip()),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyse_file(filename: str, content: str) -> FileComplexity:
    """
    Analyse a single file's complexity.

    Args:
        filename: The file path / name (used to detect language).
        content:  The full source code of the file.

    Returns:
        A :class:`FileComplexity` dataclass.
    """
    if _is_python_file(filename):
        return _analyse_python_source(content, filename)
    return _analyse_non_python_file(filename, content)


def analyse_commit_files(
    sha: str,
    files: list[tuple[str, str]],
) -> CommitComplexityReport:
    """
    Analyse complexity for all files touched by a commit.

    Args:
        sha:   The commit SHA (for identification).
        files: List of ``(filename, source_content)`` tuples.

    Returns:
        A :class:`CommitComplexityReport` with per-file and aggregated
        metrics.
    """
    report = CommitComplexityReport(sha=sha)
    file_results: list[FileComplexity] = []

    for filename, content in files:
        fc = analyse_file(filename, content)
        file_results.append(fc)

    report.files = file_results
    report.total_files_analysed = len(file_results)
    report.python_files_analysed = sum(1 for f in file_results if f.language == "python")

    if file_results:
        cc_values = [f.cyclomatic_complexity for f in file_results if f.num_blocks > 0]
        max_values = [f.max_complexity for f in file_results if f.num_blocks > 0]
        mi_values = [f.maintainability_index for f in file_results if f.language == "python"]
        halstead_values = [f.halstead_volume for f in file_results if f.halstead_volume > 0]

        report.avg_cyclomatic_complexity = (
            round(statistics.mean(cc_values), 2) if cc_values else 0.0
        )
        report.max_cyclomatic_complexity = max(max_values) if max_values else 0.0
        report.total_cc_blocks = sum(f.num_blocks for f in file_results)
        report.avg_maintainability_index = (
            round(statistics.mean(mi_values), 2) if mi_values else 100.0
        )
        report.total_loc = sum(f.loc for f in file_results)
        report.total_sloc = sum(f.sloc for f in file_results)
        report.total_comments = sum(f.comments for f in file_results)
        report.avg_halstead_volume = (
            round(statistics.mean(halstead_values), 2) if halstead_values else 0.0
        )
        report.overall_cc_rank = (
            cc_rank(report.avg_cyclomatic_complexity)
            if _radon_available and cc_values
            else "A"
        )

    logger.info(
        "Complexity analysis for %s: %d files, avg_cc=%.2f, max_cc=%.1f, MI=%.1f",
        sha[:7],
        report.total_files_analysed,
        report.avg_cyclomatic_complexity,
        report.max_cyclomatic_complexity,
        report.avg_maintainability_index,
    )
    return report


def is_radon_available() -> bool:
    """Check if radon is installed and importable."""
    return _radon_available
