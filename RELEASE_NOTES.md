# v2026.09.21

This release completes the repository audit and browser deployment.

## Changes

- Replaced sparse approximate pediatric BMI anchors with bundled WHO Child Growth Standards 2006 and WHO Growth Reference 2007 source tables.
- Implemented WHO adjusted LMS extrapolation beyond ±3 SD and corrected pediatric age-boundary handling.
- Removed fabricated adult z-scores and percentiles.
- Fixed FHIR sex/date handling, the WHO helper runtime error, longitudinal ordering, stratification regression, and the broken simulator.
- Removed automatic clinical-order behavior from example alert rules and labeled heuristic workflow modules explicitly.
- Added a compact responsive browser calculator with light/dark themes and a visible Analyze action.
- Added reproducible static-site build and GitHub Pages deployment.
- Expanded regression coverage to 49 tests across Python 3.10, 3.11, and 3.12.
- Added static-site, JavaScript syntax, CLI, simulator, and credential-pattern checks.
- Pinned GitHub Actions to reviewed release commits.

## Live application

https://abusuraihsakhri.github.io/bmi-zscore-who-calculator/

## Notes

The browser calculator runs locally in the user's browser. Patient inputs are not transmitted. WHO reference data provenance is documented in THIRD_PARTY_NOTICES.md.
