# ADZE XML-to-JSON Converter – Deployment Guide

This document explains the complete deployment lifecycle of the ADZE XML-to-JSON Converter project, which offers both web-based and CLI-driven XML-to-JSON conversion. The deployment uses GitHub Actions, Helm, Docker Hub, and OpenShift, with a strong focus on modular CI/CD, environment isolation, and future extensibility (Sysdig + Tekton).

---

## 🌐 Supported Modes

- **Web Mode**: Upload XML files via a web form to convert to JSON.
- **CLI Mode**: Convert XML files within the pod using the terminal.

---

## 📁 Project Structure

```
XML-JSON-Converter/
├── .github/workflows/
│   ├── ci.yaml               # Lint + test (no build)
│   ├── deploy-dev.yaml       # Build + deploy to c79ac4-dev
│   ├── deploy-test.yaml      # Deploy + test in c79ac4-test
│   └── deploy-prod.yaml      # Manual deploy to c79ac4-prod
├── helm-chart/
│   ├── Chart.yaml
│   ├── values-dev.yaml
│   ├── values-test.yaml
│   └── values-prod.yaml
├── sysdig/ (future use)
│   └── sysdig-team.yaml
├── tekton/ (future use)
│   └── task-sysdig-inline-scan.yaml
│   └── pipeline-adze-integration.yaml
├── src/, Dockerfile, README.md, etc.
```

---

## 🗂️ Environments Overview

| Environment | Namespace      | Purpose                                         |
| ----------- | -------------- | ----------------------------------------------- |
| Dev         | `c79ac4-dev`   | Feature integration + image build via Helm      |
| Test        | `c79ac4-test`  | Integration tests + image verification          |
| Prod        | `c79ac4-prod`  | Production deployment (manual promotion)        |
| Tools       | `c79ac4-tools` | Manages Sysdig team config and Tekton pipelines |

---

## 🔁 Branching Strategy

```plaintext
feature/* ──▶ PR → dev
                 ↓
       GitHub deploys to dev (c79ac4-dev)

dev ──▶ PR → release/test
                 ↓
       GitHub deploys to test (c79ac4-test)

release/test ──▶ PR → main
                 ↓
       GitHub deploys to prod (c79ac4-prod)
```

| Branch      | Purpose                              | Deploys to    | Triggers Workflow           |
| ----------- | ------------------------------------ | ------------- | --------------------------- |
| `feature/*` | Unit test, lint, preview builds      | —             | `ci.yaml` (unit tests)      |
| `dev`       | Dev integration, image build/publish | `c79ac4-dev`  | `deploy-dev.yaml`           |
| `release/*` | Integration tests, validate image    | `c79ac4-test` | `deploy-test.yaml`          |
| `main`      | Manual production release            | `c79ac4-prod` | `deploy-prod.yaml` (manual) |

---

## ⚙️ GitHub Workflow Overview

```plaintext
    ┌────────────────────┐
    │ BRANCH: feature/*  │
    └─────────┬──────────┘
              │
              ▼
     GitHub Actions: ci.yaml
     - Helm lint
     - Unit tests (CLI test suite)
              │
              ▼
     Pull Request → dev
              │
              ▼
 ┌────────────────────────┐
 │ ENV: c79ac4-dev (DEV)  │
 │ BRANCH: dev            │
 └─────────┬──────────────┘
           ▼
 GitHub Actions: deploy-dev.yaml
 - Docker build + push
 - Deploy via Helm with values-dev.yaml
 - Run CLI tests inside pod
 - Manual/exploratory testing (via Web UI)
           │
           ▼
 Merge to release/test
           │
           ▼
 ┌───────────────────────────┐
 │ ENV: c79ac4-test (TEST)   │
 │ BRANCH: release/*         │
 └──────────┬────────────────┘
            ▼
GitHub Actions: deploy-test.yaml
- Deploy via Helm with values-test.yaml
- 🔁 Run integration tests:
     - Upload XDP via UI
     - Validate JSON output
     - CLI batch test inside pod
     - Optional Tekton Pipeline:
       - Run Sysdig image scan
       - Runtime policy checks
            │
            ▼
      Manual PR → main
            │
            ▼
 ┌──────────────────────────┐
 │ ENV: c79ac4-prod (PROD)  │
 │ BRANCH: main             │
 └─────────┬────────────────┘
           ▼
GitHub Actions: deploy-prod.yaml
- Requires manual approval
- Deploy via Helm with values-prod.yaml
```

---

| Workflow              | File Name                   | Trigger                       | Target Namespace | Purpose                                 |
| --------------------- | --------------------------- | ----------------------------- | ---------------- | --------------------------------------- |
| **CI (Build & Test)** | `.github/workflows/ci.yaml` | Any push or PR                | none             | Lint, build Docker image, validate Helm |
| **Dev Deploy**        | `deploy-dev.yaml`           | Push to `dev`                 | `c79ac4-dev`     | Deploy to development environment       |
| **Test Deploy**       | `deploy-test.yaml`          | Push to `release/test`        | `c79ac4-test`    | Deploy to test environment              |
| **Prod Deploy**       | `deploy-prod.yaml`          | Manual trigger after PR merge | `c79ac4-prod`    | Manual production release               |

### ✅ [`ci.yaml`](.github/workflows/ci.yaml)
Triggered on all branches:
- Runs unit tests and Helm lint
- Does **not** build/push Docker images

### 🚀 [`deploy-dev.yaml`](.github/workflows/deploy-dev.yaml)
Triggered on push to `dev`:
- Builds image with `git short SHA` as tag
- Pushes both `:latest` and `:abc1234` to Docker Hub
- Deploys to OpenShift (`c79ac4-dev`) via Helm using that tag

### 🚀 [`deploy-test.yaml`](.github/workflows/deploy-test.yaml)
Triggered on push to `release/*`:
- Reuses image built in `dev`
- Deploys to `c79ac4-test` with `image.tag=${{ env.SHORT_SHA }}`
- Runs CLI test inside pod
- Safely cleans up test output files

### 🔒 [`deploy-prod.yaml`](.github/workflows/deploy-prod.yaml)
Triggered on push to `main`:
- Deploys same tagged image to `c79ac4-prod` (manual promotion)

---

## 🧪 What Tests Are Run at Each Stage?

| Stage    | Namespace     | Branch         | CI/CD Workflow     | Tests Performed                                                                                   |
| -------- | ------------- | -------------- | ------------------ | ------------------------------------------------------------------------------------------------- |
| **CI**   | —             | `feature/*`    | `ci.yaml`          | ✅ Unit tests (Python `unittest`)<br>✅ Helm lint<br>                                               |
| **Dev**  | `c79ac4-dev`  | `dev`          | `deploy-dev.yaml`  | ✅ Manual testing via UI<br> ✅ Docker build validation<br> ✅ Optional CLI tests<br>🚧 (Exploration) |
| **Test** | `c79ac4-test` | `release/test` | `deploy-test.yaml` | ✅ Automated integration tests<br>✅ CLI tests<br>🛡️ (Optional: Tekton + Sysdig)                     |
| **Prod** | `c79ac4-prod` | `main`         | `deploy-prod.yaml` | ✅ Manual approval                                                                                 |


---

### 📦 GitHub Actions Secrets

Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions** → Add these secrets:

| Secret Name                | Description                                                    |
| -------------------------- | -------------------------------------------------------------- |
| `DOCKER_USERNAME`          | Your Docker Hub username                                       |
| `DOCKER_PASSWORD`          | Your Docker Hub token or password                              |
| `OPENSHIFT_SERVER`         | Your OpenShift API endpoint (e.g., `https://api.openshift...`) |
| `OPENSHIFT_TOKEN`          | Token for dev namespace access                                 |
| `OPENSHIFT_NAMESPACE_DEV`  | (optional) e.g., `c79ac4-dev`                                  |
| `OPENSHIFT_NAMESPACE_TEST` | (optional) e.g., `c79ac4-test`                                 |
| `OPENSHIFT_NAMESPACE_PROD` | (optional) e.g., `c79ac4-prod`                                 |

---

## 🧪 CLI Testing Inside Pod

```bash
# Open a shell
oc exec -it <pod> -n c79ac4-test -- /bin/sh

# Convert single file
python src/xml_converter.py -f /app/data/input/CFL01010.xdp -o /app/data/output

# Batch convert
python src/xml_converter.py --input-dir /app/data/input --output-dir /app/data/output

# List results
ls /app/data/output/
```

---

## 🧪 Test Output Cleanup

The CLI test auto-cleans specific output patterns **only for test**:
```bash
rm -f /app/data/output/CFL01010_xdp_output_*.json
rm -f /app/data/report/CFL01010_xdp_report_*.json
```
> It **does not** touch other user-generated files.

---

## 🔬 Tekton + Sysdig (Future Integration)

Tekton-based scanning is designed but not fully deployed:
- ✅ Task and Pipeline defined
- ✅ GitHub Actions step exists to trigger `tkn pipeline start`
- 🔒 Image pull access error pending fix (switching to Quay recommended)
- 👀 `tekton/` folder contains ready-to-apply YAMLs

---

## ✅ Live Flow Summary

| Step | Trigger                        | Outcome                               |
| ---- | ------------------------------ | ------------------------------------- |
| 1    | Push `feature/*`               | Runs CI checks (no image build)       |
| 2    | Merge PR to `dev`              | Builds image, deploys to dev          |
| 3    | Promote to `release/*`         | Deploys + tests with reused image     |
| 4    | Promote to `main`              | Deploys same image to prod            |
| 5    | Optional Tekton Trigger (test) | Scans image in `c79ac4-test` (future) |

---
