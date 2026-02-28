"""Quick API smoke test for the risk prediction endpoints."""
import httpx
import json

BASE = "http://localhost:8000/api/v1"


def main():
    # Test 1: High-risk commit (hotfix, many changes)
    print("=== TEST 1: High-Risk Commit (hotfix) ===")
    r = httpx.post(f"{BASE}/predictions", json={
        "sha": "test_high_risk_001",
        "repository_full_name": "testowner/testrepo",
        "lines_added": 500,
        "lines_deleted": 200,
        "files_changed": 25,
        "commit_message": "hotfix: urgent production fix for memory leak",
        "author_email": "dev@example.com",
        "analyze_complexity": False,
    })
    data = r.json()
    print(f"  Status: {r.status_code}")
    a = data["assessment"]
    print(f"  Risk Score: {a['risk_score']}")
    print(f"  Risk Level: {a['risk_level']}")
    print(f"  Confidence: {a['confidence']}")
    print(f"  Model:      {a['model_version']}")
    print()

    # Test 2: Low-risk commit (small clean change)
    print("=== TEST 2: Low-Risk Commit (docs) ===")
    r = httpx.post(f"{BASE}/predictions", json={
        "sha": "test_low_risk_001",
        "repository_full_name": "testowner/testrepo",
        "lines_added": 5,
        "lines_deleted": 2,
        "files_changed": 1,
        "commit_message": "docs: update README with installation instructions",
        "author_email": "dev@example.com",
        "analyze_complexity": False,
    })
    data = r.json()
    print(f"  Status: {r.status_code}")
    a = data["assessment"]
    print(f"  Risk Score: {a['risk_score']}")
    print(f"  Risk Level: {a['risk_level']}")
    print(f"  Confidence: {a['confidence']}")
    print(f"  Model:      {a['model_version']}")
    print()

    # Test 3: Medium-risk commit
    print("=== TEST 3: Medium-Risk Commit (refactor) ===")
    r = httpx.post(f"{BASE}/predictions", json={
        "sha": "test_medium_risk_001",
        "repository_full_name": "testowner/testrepo",
        "lines_added": 120,
        "lines_deleted": 50,
        "files_changed": 8,
        "commit_message": "refactor: restructure authentication module",
        "author_email": "dev@example.com",
        "analyze_complexity": False,
    })
    data = r.json()
    print(f"  Status: {r.status_code}")
    a = data["assessment"]
    print(f"  Risk Score: {a['risk_score']}")
    print(f"  Risk Level: {a['risk_level']}")
    print(f"  Confidence: {a['confidence']}")
    print(f"  Model:      {a['model_version']}")
    print()

    # Test 4: Model info
    print("=== MODEL INFO ===")
    r = httpx.get(f"{BASE}/predictions/model-info")
    print(json.dumps(r.json(), indent=2))
    print()

    # Test 5: List all predictions
    print("=== ALL PREDICTIONS ===")
    r = httpx.get(f"{BASE}/predictions")
    for p in r.json():
        a = p["assessment"]
        c = p["commit"]
        sha = c["sha"][:12]
        print(f"  {sha:14s}  score={a['risk_score']:5.1f}  level={a['risk_level']:6s}  conf={a['confidence']:.2f}")


if __name__ == "__main__":
    main()
