# ADZE XML-to-JSON Converter

Welcome to the ADZE project – a flexible tool for converting XML to JSON with both Web UI and CLI support. This README explains the complete deployment strategy using GitHub Actions and OpenShift, covering project structure, CI/CD automation, environment configuration, and testing modes.

---

## 🌐 Supported Modes

- **Web Mode**: Upload `.xdp` XML files via browser UI and receive converted JSON output.
- **CLI Mode**: Use included sample files within the Docker container to convert via terminal commands.

---

## 📁 Project Structure

```
ADZE/
│── .github/
│   └── workflows/
│       ├── ci.yaml              # CI pipeline: lint, build, Helm validation
│       ├── deploy-dev.yaml      # Auto deploy to OpenShift (dev)
│       └── deploy-prod.yaml     # Manual deploy to OpenShift (prod)
│
│── helm-chart/
│   ├── Chart.yaml
│   ├── values-dev.yaml
│   ├── values-prod.yaml
│   └── templates/
│
│── src/                         # Python source code
│── data/                        # input/output/report files
│── Dockerfile                   # App container definition
│── README.md
```

---

## 🚀 Deployment Strategy

### Environments

| Environment | Namespace     | Description                       |
| ----------- | ------------- | --------------------------------- |
| Dev         | `c79ac4-dev`  | Active development, test features |
| test        | `c79ac4-test` | Integration & pre-prod testing    |
| Prod        | `c79ac4-prod` | Stable production deployments     |

---

### GitHub Actions CI/CD

#### ✅ [ci.yaml](.github/workflows/ci.yaml)

Runs on every push or PR:
- Lints Helm charts
- Builds and pushes Docker image
- Validates Helm templates using `values-dev.yaml`

Ref: [ci.yaml snippet](./.github/workflows/ci.yaml)

#### 🚀 [deploy-dev.yaml](.github/workflows/deploy-dev.yaml)

Triggered on push to `dev`:
- Logs into OpenShift (`c79ac4-dev`)
- Deploys using Helm with `values-dev.yaml`

Ref: [deploy-dev.yaml snippet](./.github/workflows/deploy-dev.yaml)

#### 🚀 [deploy-prod.yaml](.github/workflows/deploy-prod.yaml)

Triggered on push to `main`:
- Manual approval required
- Logs into OpenShift (`c79ac4-prod`)
- Deploys using Helm with `values-prod.yaml`

Ref: [deploy-prod.yaml snippet](./.github/workflows/deploy-prod.yaml)

---

## 🌱 Branching Workflow

```plaintext
feature/* ──▶ PR to dev ──▶ Merge to dev
                    ↓
        GitHub Actions deploys to c79ac4-dev
                    ↓
        Merge dev → release/*
                    ↓
        PR from release/* → main
                    ↓
        Merge to main → GitHub deploys to c79ac4-prod (manual)
```

---

## 🔑 GitHub Secrets Required

| Secret Name                | Purpose                            |
| -------------------------- | ---------------------------------- |
| `DOCKER_USERNAME`          | Docker Hub username                |
| `DOCKER_PASSWORD`          | Docker Hub password                |
| `OPENSHIFT_SERVER`         | OpenShift API URL (dev)            |
| `OPENSHIFT_TOKEN`          | Dev access token                   |
| `OPENSHIFT_NAMESPACE`      | Dev namespace (e.g., `c79ac4-dev`) |
| `OPENSHIFT_TOKEN_PROD`     | Prod access token                  |
| `OPENSHIFT_NAMESPACE_PROD` | Prod namespace (`c79ac4-prod`)     |

---

## 🧪 Local Testing Instructions

### ✅ Web Mode

1. Access:
   ```
   https://<openshift-route>/upload_form
   ```
2. Upload XML file.
3. Processed result should appear in the output and report directory.

---

### ✅ CLI Mode (inside OpenShift pod)

```bash
# Open shell
oc exec -it <pod-name> -n c79ac4-dev -- /bin/sh

# Run a single file
python src/xml_converter.py -f /app/data/input/CFL01010.xdp -o /app/data/output

# Batch convert all files
python src/xml_converter.py --input-dir /app/data/input --output-dir /app/data/output

# Check output
ls /app/data/output
cat /app/data/output/<converted-file>.json
```

---

## 🧪 CI/CD Live Demo Flow (End-to-End)

| Step | Action                               | Expected Outcome                                      |
| ---- | ------------------------------------ | ----------------------------------------------------- |
| 1    | Push `feature/*` branch              | Triggers `ci.yaml` for test, lint, Docker build       |
| 2    | Create PR → Merge to `dev`           | Triggers `deploy-dev.yaml`, deploys to `c79ac4-dev`   |
| 3    | Promote `dev` → `release/*` → `main` | Triggers `deploy-prod.yaml`, deploys to `c79ac4-prod` |
| 4    | Verify pod & logs via OpenShift      | App running, logs show successful processing          |
