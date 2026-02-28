"""
CLI entry point for ML training.

Usage:
    cd backend
    python -m app.ml.trainer [options]

Examples:
    # Train with synthetic data (for quick start)
    python -m app.ml.trainer --synthetic

    # Train logistic regression on DB data + synthetic fill
    python -m app.ml.trainer --model lr --synthetic

    # Train random forest
    python -m app.ml.trainer --model rf --synthetic

    # Train gradient boosting + export CSV
    python -m app.ml.trainer --model gb --synthetic --csv-export data.csv

    # Train with 1000 synthetic samples
    python -m app.ml.trainer --synthetic --synthetic-count 1000
"""

from app.ml.trainer import main

if __name__ == "__main__":
    main()
