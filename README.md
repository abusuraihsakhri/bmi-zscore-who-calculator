# Pediatric BMI Z-Score WHO Calculator

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![Build Status](https://img.shields.io/badge/CI-Passing-brightgreen.svg)
![Standards](https://img.shields.io/badge/WHO-Child%20Growth%20Standards%202006%20%2F%202007-blue.svg)

A clinical and epidemiological toolkit for calculating Body Mass Index (BMI), sex- and age-specific BMI-for-age Z-scores, percentiles, and nutritional classifications based on the **World Health Organization (WHO) Child Growth Standards (0–5 years / 0–60 months)** and **WHO Growth Reference (5–19 years / 61–228 months)**.

---

## 📐 Pediatric Anthropometric Formulations (LMS Method)

The calculation of BMI-for-age Z-scores employs the **Cole & Green (1992)** LMS technique adopted by the World Health Organization (WHO Child Growth Standards 2006 & WHO Reference 2007).

### 1. BMI Formulation

$$\text{BMI} = \frac{\text{weight (kg)}}{(\text{height or length in meters})^2}$$

### 2. LMS Transformation

The LMS methodology summarizes growth references into three age- and sex-dependent smoothed parameters:
- **$L$ (Lambda)**: Box-Cox power transformation parameter accounting for skewness in the distribution.
- **$M$ (Mu)**: Median BMI value at the reference age and sex.
- **$S$ (Sigma)**: Generalized coefficient of variation indicating dispersion.

The BMI-for-age Z-score ($Z$) is computed using:

$$Z = \frac{(\text{BMI} / M)^L - 1}{L \cdot S} \quad \text{when } L \neq 0$$

$$Z = \frac{\ln(\text{BMI} / M)}{S} \quad \text{when } L = 0$$

### 3. Percentile Calculation

Percentiles are derived from the standard normal cumulative distribution function $\Phi(Z)$:

$$\text{Percentile} = \Phi(Z) \times 100 = \frac{1}{2} \left[1 + \text{erf}\left(\frac{Z}{\sqrt{2}}\right)\right] \times 100$$

---

## 📊 WHO Cutoffs & Nutritional Classifications

Nutritional status interpretation differs across developmental age groups in accordance with WHO clinical guidelines:

### Children 0–5 Years (0–60 Months) — WHO Child Growth Standards (2006)

| Z-Score Range | Nutritional Classification | Clinical Interpretation |
| :--- | :--- | :--- |
| $Z < -3\,\text{SD}$ | **Severe wasting** | Severe acute malnutrition; requires immediate clinical care |
| $-3\,\text{SD} \le Z < -2\,\text{SD}$ | **Wasted** | Moderate acute malnutrition |
| $-2\,\text{SD} \le Z \le +1\,\text{SD}$ | **Normal** | Adequate nutritional status |
| $+1\,\text{SD} < Z \le +2\,\text{SD}$ | **Risk of overweight** | Potential for pediatric excess adiposity |
| $+2\,\text{SD} < Z \le +3\,\text{SD}$ | **Overweight** | Elevated risk of childhood obesity |
| $Z > +3\,\text{SD}$ | **Obese** | Extreme excess adiposity |

### Children 5–19 Years (61–228 Months) — WHO Growth Reference (2007)

| Z-Score Range | Classification | Clinical Interpretation |
| :--- | :--- | :--- |
| $Z < -3\,\text{SD}$ | **Severe thinness** | Severe undernutrition |
| $-3\,\text{SD} \le Z < -2\,\text{SD}$ | **Thinness** | Moderate undernutrition |
| $-2\,\text{SD} \le Z \le +1\,\text{SD}$ | **Normal** | Healthy weight range |
| $+1\,\text{SD} < Z \le +2\,\text{SD}$ | **Overweight** | Equivalent to adult BMI $\ge 25\,\text{kg/m}^2$ at 19 years |
| $Z > +2\,\text{SD}$ | **Obese** | Equivalent to adult BMI $\ge 30\,\text{kg/m}^2$ at 19 years |

---

## 💻 CLI Quickstart & Usage

The application provides a zero-dependency CLI (`cli.py` / `bmi_zscore.py`) using Python standard library:

### 1. Single Patient Assessment

```bash
# Evaluate a 5-year-old boy (60 months)
python cli.py single --id PAT-001 --weight 18.5 --height 1.10 --age-months 60 --sex M

# Output:
# Patient: PAT-001
#   Weight: 18.5 kg  Height: 1.10 m
#   Age: 60 months (5.0 years)
#   Sex: M
#   BMI: 15.29 kg/m²
#   Z-score: -0.01
#   Percentile: 49.6%
#   WHO Category: Normal
```

### 2. Batch CSV Processing

Process multi-patient cohorts with automatic column harmonization (supporting `height_m`, `height_cm`, `weight_kg`, `age_months`, and `age_days`):

```bash
python cli.py batch -i sample.csv -o results.csv
```

Example input (`sample.csv`):
```csv
patient_id,age_months,age_days,sex,height_cm,weight_kg,bmi,l_param,m_param,s_param,z_score,percentile,nutritional_classification
P001,36,1095,male,96.0,9.8,10.63,-1.10,15.40,0.0780,-5.87,0.0,severe wasting (<-3SD)
P002,24,730,female,86.0,9.7,13.12,-0.90,15.40,0.0810,-2.13,1.7,wasted (<-2SD)
P003,12,365,male,76.0,9.6,16.62,-0.80,16.40,0.0820,0.16,56.4,normal (-2SD to +1SD)
P006,60,1826,female,110.0,23.0,19.01,-1.20,15.20,0.0830,2.36,99.1,overweight (>+2SD)
P007,48,1461,male,103.0,23.0,21.68,-1.20,15.30,0.0790,3.61,100.0,obese (>+3SD)
```

---

## 🐍 Python Quickstart

Use `bmi_zscore` programmatically in Python applications or data science pipelines:

```python
import bmi_zscore as bmi

# 1. Calculate BMI
weight_kg = 16.5
height_m = 0.96
bmi_val = bmi.calculate_bmi(weight_kg, height_m)
print(f"BMI: {bmi_val:.2f} kg/m²")  # 17.90 kg/m²

# 2. Compute WHO LMS Z-score for a 36-month-old boy
z = bmi.bmi_zscore_child(bmi=bmi_val, age_months=36.0, sex="M")
percentile = bmi.zscore_to_percentile(z)
category = bmi.classify_child_zscore(z)

print(f"Z-Score: {z:+.2f}")        # +1.78
print(f"Percentile: {percentile:.1f}%") # 96.2%
print(f"Category: {category}")    # Overweight risk

# 3. Patient Level Evaluation
result = bmi.calculate_patient(
    patient_id="PAT-PEDIATRIC-1",
    weight_kg=23.0,
    height_m=1.10,
    age_months=60.0,
    sex="F"
)
print(f"Z: {result.z_score}, Category: {result.child_category}")
```

---

## 🧪 Testing & Verification

Run the comprehensive test suite with pytest:

```bash
python -m pytest -p no:zarr -v
```

Execute CLI batch smoke verification:

```bash
python cli.py batch -i sample.csv -o out_smoke.csv
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
