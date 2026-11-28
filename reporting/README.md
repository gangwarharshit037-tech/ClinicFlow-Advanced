# ClinicFlow Advanced - Reporting Pipeline

## Version

V2.0 Phase 2 - Excel Reporting and Power BI Integration

## Overview

This reporting pipeline generates, validates and cleans
synthetic healthcare appointment data for analytical use.

## Dataset

- Total appointments: 10,000
- Total columns: 14
- Booked appointments: 8,000
- Cancelled appointments: 2,000
- Doctors: 3
- Departments: 3
- Appointment period: January to December 2025
- Random seed: 42
- Patient personal information: None

## Installation

    python -m pip install -r requirements-reporting.txt

## Generate synthetic data

    python scripts/generate_synthetic_data.py

## Validate dataset

    python -m reporting.data_validation

## Clean dataset

    python -m reporting.data_cleaning

## Run reporting tests

    python -m pytest tests/test_reporting_data_quality.py -v

## Run complete test suite

    python -m pytest -q

## Data Quality

- 24 dataset validation checks
- 20 automated reporting tests
- 132 total passing project tests
- Missing value detection
- Duplicate appointment detection
- Date and time validation
- Doctor and department consistency
- Booking lead time validation
- Calendar field consistency
- Duplicate active slot prevention

## Privacy and Limitations

All appointment records are synthetic.

The dataset does not contain patient names,
phone numbers or real medical records.

The 80 percent booked and 20 percent cancelled
distribution is an artificial design choice.

Booking dates may extend into December 2024.

Booked status does not indicate completed treatment
or confirmed patient attendance.

The reporting pipeline does not modify the
live application database.

Synthetic appointment trends must not be interpreted
as real healthcare demand.

## Upcoming Features

- Advanced SQL business analysis
- Automated Excel reports
- Excel KPI dashboards
- Admin reporting integration
- Power BI data model
- DAX measures
- Interactive business intelligence dashboards

## Reproducibility and Continuous Integration

Generated CSV datasets are excluded from version control.

To reproduce the reporting dataset from a fresh clone,
run the generation, validation and cleaning commands
before executing the automated test suite.

GitHub Actions automatically installs reporting
dependencies, generates synthetic data, validates
data quality, cleans the dataset and runs all tests.

Reporting dependencies are maintained separately
from web application runtime dependencies.

The generator uses a fixed random seed.

Exact CSV hashes may vary across operating systems
or dependency versions.

Generated datasets are overwritten when generation
or cleaning commands are executed again.

## Advanced SQL Business Analysis

The analytical pipeline uses 10,000 synthetic appointments for 2025.

### Database architecture

- SQLite star schema
- One fact table and three dimension tables
- Six custom indexes
- Six analytical views
- Automated ETL and integrity validation

### Reporting features

- 10 business KPI reports
- 6 advanced SQL reports
- Common Table Expressions (CTEs)
- SQL window functions
- Month-over-month growth
- Cumulative appointment analysis
- Rolling seven-day averages
- Department contribution and rankings
- Automated CSV exports
- SHA-256 checksums and report manifest

### Run the reporting pipeline

    python scripts/generate_synthetic_data.py
    python -m reporting.data_validation
    python -m reporting.data_cleaning
    python -m reporting.build_analytics_db
    python -m reporting.business_kpis
    python -m reporting.advanced_sql
    python -m reporting.export_sql_reports

### Verified results

| Metric | Value |
| --- | ---: |
| Total appointments | 10,000 |
| Booked appointments | 8,000 |
| Cancelled appointments | 2,000 |
| Cancellation rate | 20% |
| Average daily appointments | 27.40 |
| Average lead time | 14.96 days |
| SQL reports | 16 |
| CSV files including manifest | 17 |
| Exported analytical rows | 534 |
| SQL automated tests | 35 |
| Total automated tests passed locally | 167 |

### Automated testing

    python -m pytest tests/test_sql_reporting.py -v
    python -m pytest tests/ -q

Tests use temporary databases and export directories.
Generate and clean the synthetic CSV before running tests.

### Generated outputs

- data/analytics/clinicflow_analytics.db
- reports/sql/*.csv

Generated outputs are excluded from Git.

### Limitations

- All reporting data is synthetic.
- Booked appointments are not completed visits.
- Rankings measure appointment volume, not clinical quality.
- January growth is undefined.
- Rolling averages require seven complete days.
- Index performance has not been benchmarked.
- CSV replacements are atomic individually, not as a batch.
- Do not rebuild the database during report export.
- Excel and Power BI integration are planned next.
