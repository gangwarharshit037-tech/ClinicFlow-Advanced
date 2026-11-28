import hashlib
import warnings

from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from reporting.build_analytics_db import DATABASE
from reporting.business_kpis import run_business_analysis
from reporting.advanced_sql import run_advanced_analysis


ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = ROOT / "reports" / "sql"


def safe_text(value):

    if isinstance(value, str):
        if value.lstrip().startswith(
            ("=", "+", "-", "@")
        ) or value.startswith(("\t", "\r", "\n")):
            return "'" + value

    return value


def prepare_export(df):

    result = df.copy(deep=True)

    for column in result.select_dtypes(
        include=["object", "string"]
    ).columns:

        result[column] = result[column].map(safe_text)

    return result


def export_sql_reports(
    database=DATABASE,
    output_dir=OUTPUT_DIR
):

    output_dir = Path(output_dir)

    business = run_business_analysis(database)

    advanced = run_advanced_analysis(database)

    if set(business) & set(advanced):
        raise ValueError("Duplicate report names.")

    reports = {**business, **advanced}

    if len(reports) != 16:
        raise ValueError("Expected 16 SQL reports.")

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    metadata = []

    with TemporaryDirectory(
        prefix="clinicflow_export_",
        dir=output_dir
    ) as temp_dir:

        staging = Path(temp_dir)

        for name, df in reports.items():

            filename = f"{name}.csv"

            destination = staging / filename

            prepared = prepare_export(df)

            prepared.to_csv(
                destination,
                index=False,
                encoding="utf-8-sig",
                na_rep=""
            )

            exported = pd.read_csv(
                destination,
                encoding="utf-8-sig"
            )

            if exported.shape != prepared.shape:
                raise ValueError(
                    f"Shape mismatch: {filename}"
                )

            if list(exported.columns) != list(df.columns):
                raise ValueError(
                    f"Column mismatch: {filename}"
                )

            checksum = hashlib.sha256(
                destination.read_bytes()
            ).hexdigest()

            metadata.append({
                "report_name": name,
                "category": (
                    "Business KPI"
                    if name in business
                    else "Advanced SQL"
                ),
                "filename": filename,
                "rows": len(df),
                "columns": len(df.columns),
                "size_bytes": destination.stat().st_size,
                "sha256": checksum,
                "data_source": "Synthetic 2025"
            })

        manifest = pd.DataFrame(metadata)

        manifest.to_csv(
            staging / "report_manifest.csv",
            index=False,
            encoding="utf-8-sig"
        )

        for record in metadata:

            filename = record["filename"]

            (staging / filename).replace(
                output_dir / filename
            )

        (staging / "report_manifest.csv").replace(
            output_dir / "report_manifest.csv"
        )

    return manifest


def main():

    print("=" * 70)
    print("CLINICFLOW AUTOMATED SQL REPORT EXPORT")
    print("=" * 70)

    manifest = export_sql_reports()

    print(
        manifest[
            [
                "report_name",
                "category",
                "rows",
                "columns",
                "size_bytes"
            ]
        ].to_string(index=False)
    )

    print("\nTotal SQL reports:", len(manifest))

    print(
        "Total exported records:",
        manifest["rows"].sum()
    )

    print(
        "Total report size:",
        round(
            manifest["size_bytes"].sum() / 1024,
            2
        ),
        "KB"
    )

    print("\nManifest: report_manifest.csv")

    print("Output directory:", OUTPUT_DIR)

    print("\nSUCCESS: All SQL reports exported.")


if __name__ == "__main__":
    main()
