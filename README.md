# Pediatric BMI Z-Score WHO Calculator

### [Open the Live Application →](https://abusuraihsakhri.github.io/bmi-zscore-who-calculator/)

[![CI](https://github.com/abusuraihsakhri/bmi-zscore-who-calculator/actions/workflows/ci.yml/badge.svg)](https://github.com/abusuraihsakhri/bmi-zscore-who-calculator/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A dependency-free BMI calculator for WHO pediatric BMI-for-age z-scores and
adult BMI categories. Pediatric calculations use the WHO Child Growth
Standards 2006 reference below 60 months and the WHO Growth Reference 2007
from 60 to less than 229 months.

The repository provides a Python CLI/API, CSV batch processing, a small FHIR
R4 integration helper, and a static browser calculator suitable for GitHub
Pages.

## What it calculates

For pediatric BMI-for-age, the project uses the LMS/Box-Cox transformation:

z = ((BMI / M)^L - 1) / (L × S)

When the unadjusted score is above +3 SD or below -3 SD, the implementation
uses the WHO adjusted extrapolation based on the distance between the 2-SD and
3-SD curves.

Reference resolution:

- **Birth to <60 months:** day-level WHO Child Growth Standards 2006 data.
  If only age in months is supplied, the nearest day is derived using
  365.25/12 days per month. Exact age in days is preferred.
- **60 to <229 months:** monthly WHO Growth Reference 2007 data, with linear
  interpolation for fractional months as used by WHO AnthroPlus.
- **Post-reference/adult inputs:** BMI is classified by adult BMI thresholds;
  no fabricated adult z-score or percentile is produced.

Pediatric category labels follow age-specific WHO z-score cut-offs. The
under-5 low-BMI labels in this project are deliberately descriptive
("Low BMI-for-age" and "Very low BMI-for-age") rather than treating BMI alone
as a diagnosis of wasting.

## Browser application

The static application is in the web directory. It runs entirely in the
browser, loads the same WHO reference tables used by Python, and requires no
server-side Python or external API.

Features:

- Light theme by default with a dark-theme toggle.
- Compact responsive layout with a visible **Analyze** action.
- BMI, z-score, percentile, category, LMS parameters, reference age, and
  reference standard in one result view.
- No patient inputs are transmitted. Only the theme preference is stored in
  browser local storage.
- No external fonts, scripts, analytics, or third-party network calls.

GitHub Pages deployment is handled by .github/workflows/pages.yml from the
master branch.

## CLI

Single calculation:

~~~bash
python cli.py single \
  --weight 32.23 \
  --height 1.40 \
  --age-months 120 \
  --sex M
~~~

For a child under 5, exact age in days can be supplied:

~~~bash
python cli.py single \
  --weight 9.6 \
  --height 0.76 \
  --age-months 12 \
  --age-days 365 \
  --sex M
~~~

Batch CSV processing:

~~~bash
python cli.py batch -i sample.csv -o results.csv
~~~

Accepted height columns include height_m, height_cm, length_cm, and height.
Accepted age columns include age_months and age_days.

## Python API

~~~python
import bmi_zscore as bmi

result = bmi.calculate_patient(
    patient_id="example",
    weight_kg=32.23,
    height_m=1.40,
    age_months=120,
    sex="M",
)

print(result.bmi)
print(result.z_score)
print(result.percentile)
print(result.child_category)
print(result.reference_standard)
~~~

## FHIR helper

fhir_bmi_integration.py can extract height and weight from FHIR R4
Observations using LOINC 8302-2 and 29463-7, calculate BMI-for-age, and produce
a derived BMI Observation. Patient.birthDate and a supported Patient.gender
value are required.

When Observation resources contain effectiveDateTime, the latest supplied
observation date is used as the age reference date. This keeps calculations
reproducible instead of silently using the current date.

## Local development

Runtime code uses only the Python standard library. Tests require pytest.

~~~bash
python -m pip install pytest
python -m pytest -p no:zarr -v
python cli.py batch -i sample.csv -o out_smoke.csv
python simulator.py 100 --seed 7
~~~

Build and serve the browser application:

~~~bash
python scripts/build_site.py
python -m http.server 8000 --directory _site
~~~

Then open http://localhost:8000/.

The web application targets current versions of Chrome, Edge, Firefox, and
Safari and uses standard HTML, CSS, and JavaScript without a framework.

## Validation and limitations

The automated tests check exact anchors from the WHO source tables,
fractional-month interpolation, adjusted LMS behavior, age boundaries, CSV and
CLI workflows, FHIR behavior, auxiliary helper regressions, and the static
site build.

Important limitations:

- BMI-for-age is a reference calculation and not a diagnosis or treatment
  recommendation.
- For children under 5, exact age in days is more precise than a month-only
  approximation.
- The calculator does not infer or correct recumbent-length versus standing-
  height measurement technique. Supply anthropometry collected according to
  the relevant WHO procedure.
- Oedema handling from WHO Anthro/AnthroPlus is not implemented in the simple
  calculator interface; weight-related z-scores should not be interpreted as
  equivalent to a full WHO Anthro assessment when oedema is present.
- The experimental workflow helpers in alert_escalation.py,
  longitudinal_growth.py, and patient_stratification.py are explicitly
  heuristic and are not validated clinical risk models.

## Reference data

The bundled WHO data are sourced from the WHO-maintained repositories:

- https://github.com/WorldHealthOrganization/anthro
- https://github.com/WorldHealthOrganization/anthroplus

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for data provenance and
third-party rights information.

## License

Project code is licensed under the MIT License; see [LICENSE](LICENSE).
Third-party WHO reference material is identified separately in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
