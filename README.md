# Bmi Zscore WHO Calculator

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Alert Escalation for BMI Z-Score WHO Calculator.
Manages escalation workflows for critical BMI z-score findings
with configurable severity thresholds and notification routing.

BMI Calculator with WHO Classification and Z-Scores
=====================================================

Implements:
  - BMI = weight_kg / (height_m)^2
  - WHO Adult classification (Underweight through Obese III)
  - WHO Child BMI-for-age Z-scores using LMS method with reference tables
  - Percentile calculation from Z-score

Stdlib only. Usage: python bmi_zscore.py --help

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`EscalationRule`**: Defines when and how to escalate.
- **`AlertEscalationAgent`**: Sub-agent for alert escalation management.
- **`BMIResult`** — dedicated module for b m i result evaluation and state verification.
- **`VitalExtraction`** — dedicated module for vital extraction evaluation and state verification.
- **`GrowthMeasurement`**: Single growth measurement point.
- **`LongitudinalGrowthAgent`**: Sub-agent for longitudinal growth velocity tracking.

---

## 📐 Mathematical Formulation & Logic

```text
  """Calculate BMI = weight / height²."""
  return (L, M, S)
  """Calculate BMI-for-age Z-score using WHO LMS method.
  """Calculate BMI with WHO classification for one patient."""
  result.bmi = round(calculate_bmi(weight_kg, height_m), 2)
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --input data.csv
```

### Parameter Reference
- `--interactive`: Launch guided terminal interactive wizard.
- `--input <path>`: Evaluate input from JSON or CSV specification.
- `--json`: Output deterministic structured results in JSON format.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `patient_id` | Parameter / observation metric | Required |
| `weight_kg` | Parameter / observation metric | Required |
| `height_cm` | Parameter / observation metric | Required |
| `age_months` | Parameter / observation metric | Required |
| `sex` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t bmi-zscore-who-calculator .
docker run -p 8000:8000 bmi-zscore-who-calculator
```
