# 🧠 AI Model Engineering
## AI Software Failure Predictor

---

# 1. Overview

The AI Software Failure Predictor uses machine learning to estimate the probability that a commit or pull request will introduce a production failure.

The system analyzes GitHub repository activity, extracts behavioral and structural features, and generates a risk score before deployment.

---

# 2. Problem Definition

## Objective

Predict whether a commit or pull request introduces a production failure.

## Prediction Type

Binary Classification:

- 0 → Safe
- 1 → Risky

## Output

- Risk Score (0–100)
- Risk Level (Low / Medium / High)
- Confidence Score

---

# 3. Definition of Failure (Labeling Strategy)

For the MVP, a failure is defined as:

- Pull request reverted within 7 days
- Hotfix commit within 48 hours
- Issue labeled “bug” referencing the commit
- Rollback commit detected

This allows supervised learning using labeled historical data.

---

# 4. Data Collection

## Data Source

GitHub API:

- Commits
- Pull Requests
- Issues
- Labels
- Contributors

## Pipeline

1. Fetch merged PRs
2. Collect commit metadata
3. Detect failure conditions
4. Assign binary label
5. Store dataset in database

---

# 5. Feature Engineering

## Code-Level Features

- lines_added
- lines_deleted
- total_lines_changed
- files_changed
- file_types_count
- percentage_test_files_changed

## Developer-Level Features

- total_prior_commits
- previous_bug_rate
- commit_frequency
- time_since_last_commit

## Repository-Level Features

- repo_size
- contributor_count
- open_issues_count
- commit_velocity

## Temporal Features

- day_of_week
- time_of_day
- weekend_flag

---

# 6. Derived Features

- code_churn_ratio = lines_added / (lines_deleted + 1)
- risk_density = files_changed / total_lines_changed
- developer_risk_score = previous_bug_rate × total_lines_changed

These engineered features improve predictive power.

---

# 7. Data Preprocessing

- Handle missing values using median
- Normalize numeric features (StandardScaler)
- Handle class imbalance using class_weight="balanced"
- Remove corrupted samples

---

# 8. Model Training

## Baseline Model

Logistic Regression

Why:
- Fast
- Interpretable
- Lightweight
- Easy to deploy

## Evaluation Metrics

- Accuracy
- Precision
- Recall
- F1 Score
- ROC AUC

Target: ROC AUC > 0.65 (MVP)

---

# 9. Advanced Models (Future Phase)

- Random Forest
- Gradient Boosting
- XGBoost
- LightGBM

Compare based on:
- Accuracy
- Inference speed
- Model size

---

# 10. Model Versioning

Models are stored as:

- model_v1.pkl
- model_v2.pkl

Each prediction stores the model_version for traceability.

---

# 11. Production Inference Flow

1. Backend loads model at startup
2. Feature extraction runs
3. Model predicts probability
4. Probability converted to risk score
5. Prediction stored in database
6. Response returned to frontend

---

# 12. Monitoring & Future ML Ops

- Track prediction distribution
- Detect feature drift
- Log predictions for retraining
- Schedule periodic retraining

This ensures long-term model reliability.