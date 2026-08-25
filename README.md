# BMI Calculator with WHO Classification and Z-Scores

Calculates BMI with WHO adult classification and child BMI-for-age Z-scores using the LMS method.

## Formulas Implemented

### BMI
```
BMI = weight_kg / (height_m)²
```

### WHO Adult BMI Classification
| BMI Range | Category |
|:---|:---|
| < 16.0 | Severe Thinness |
| 16.0 – 16.9 | Moderate Thinness |
| 17.0 – 18.4 | Mild Thinness |
| 18.5 – 24.9 | Normal |
| 25.0 – 29.9 | Overweight |
| 30.0 – 34.9 | Obese Class I |
| 35.0 – 39.9 | Obese Class II |
| ≥ 40.0 | Obese Class III |

### WHO Child BMI-for-age Z-scores (LMS Method)
```
Z = ((BMI/M)^L - 1) / (L × S)    when L ≠ 0
Z = log(BMI/M) / S                when L = 0
```
Uses WHO 2007 growth reference LMS tables for ages 0-19 years.

### Z-score to Percentile
Uses the standard normal CDF: `percentile = 0.5 × (1 + erf(Z/√2)) × 100`

## Usage

```bash
# Adult BMI
python bmi_zscore.py single --weight 70 --height 1.75

# Child BMI with Z-score
python bmi_zscore.py single --weight 20 --height 1.10 --age-months 60 --sex M

# Batch CSV processing
python bmi_zscore.py batch --input patients.csv --output results.csv
```

## CSV Input Format

Required: `patient_id`, `weight_kg`, `height_m`
Optional: `age_months`, `sex` (M/F — required for child Z-scores)

## Requirements

Python 3.9+ (stdlib only)

## Disclaimer

For educational and clinical decision support only. WHO child growth standards are simplified reference tables; for clinical decisions use the complete WHO Anthro or WHO AnthroPlus software.
