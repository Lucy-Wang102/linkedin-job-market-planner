"""Create a compact deployment file from the downloaded Kaggle dataset.

Place postings.csv or job_postings.csv anywhere under raw_data/, then run:
    python prepare_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
RAW_DIR = PROJECT_DIR / "raw_data"
OUTPUT_PATH = PROJECT_DIR / "data" / "dashboard_jobs.csv.gz"


def find_postings_file() -> Path:
    candidates = []
    for name in ("postings.csv", "job_postings.csv"):
        candidates.extend(RAW_DIR.rglob(name))
    if not candidates:
        raise FileNotFoundError(
            "Could not find postings.csv or job_postings.csv under raw_data/. "
            "Download and unzip the Kaggle dataset there first."
        )
    return max(candidates, key=lambda path: path.stat().st_size)


def first_existing(frame: pd.DataFrame, names: list[str], default=np.nan) -> pd.Series:
    for name in names:
        if name in frame.columns:
            return frame[name]
    return pd.Series(default, index=frame.index)


def parse_timestamp(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().mean() > 0.8:
        typical = numeric.dropna().median()
        unit = "ms" if typical > 10_000_000_000 else "s"
        return pd.to_datetime(numeric, unit=unit, errors="coerce", utc=True).dt.tz_localize(None)
    return pd.to_datetime(series, errors="coerce", utc=True).dt.tz_localize(None)


def annualize_salary(frame: pd.DataFrame) -> pd.Series:
    minimum = pd.to_numeric(first_existing(frame, ["min_salary"]), errors="coerce")
    maximum = pd.to_numeric(first_existing(frame, ["max_salary"]), errors="coerce")
    median = pd.to_numeric(first_existing(frame, ["med_salary", "median_salary"]), errors="coerce")

    midpoint = pd.concat([minimum, maximum], axis=1).mean(axis=1, skipna=True)
    salary = median.fillna(midpoint)

    pay_period = first_existing(frame, ["pay_period"], default="YEARLY").astype(str).str.upper()
    multipliers = pay_period.map(
        {
            "HOURLY": 2080,
            "WEEKLY": 52,
            "BIWEEKLY": 26,
            "MONTHLY": 12,
            "YEARLY": 1,
            "ANNUAL": 1,
        }
    )
    annual = salary * multipliers

    currency = first_existing(frame, ["currency"], default="USD").astype(str).str.upper()
    annual = annual.where(currency.isin(["USD", "NAN", "NONE", ""]))
    return annual.where(annual.between(10_000, 1_000_000))


def clean_text(series: pd.Series, fallback: str = "Not specified") -> pd.Series:
    cleaned = series.astype("string").str.strip()
    return cleaned.mask(cleaned.isna() | cleaned.eq(""), fallback)


def main() -> None:
    source_path = find_postings_file()
    print(f"Reading {source_path}")
    raw = pd.read_csv(source_path, low_memory=False)

    remote_raw = first_existing(raw, ["remote_allowed"], default=False)
    remote_allowed = (
        remote_raw.astype(str).str.strip().str.lower().isin(["1", "1.0", "true", "yes", "y"])
    )

    listed_raw = first_existing(raw, ["listed_time", "original_listed_time"])

    prepared = pd.DataFrame(
        {
            "job_id": clean_text(first_existing(raw, ["job_id"]), "Unknown"),
            "title": clean_text(first_existing(raw, ["title", "job_title"])),
            "company_name": clean_text(
                first_existing(raw, ["company_name", "company", "name"])
            ),
            "location": clean_text(first_existing(raw, ["location", "job_location"])),
            "experience_level": clean_text(
                first_existing(raw, ["formatted_experience_level", "experience_level"])
            ),
            "work_type": clean_text(
                first_existing(raw, ["formatted_work_type", "work_type"])
            ),
            "remote_allowed": remote_allowed,
            "annual_salary_mid": annualize_salary(raw).round(2),
            "applications": pd.to_numeric(
                first_existing(raw, ["applies", "applications"]), errors="coerce"
            ),
            "views": pd.to_numeric(first_existing(raw, ["views"]), errors="coerce"),
            "listed_date": parse_timestamp(listed_raw),
        }
    )

    prepared = prepared.drop_duplicates(subset="job_id", keep="first")
    prepared["salary_available"] = prepared["annual_salary_mid"].notna()
    prepared = prepared.sort_values("listed_date", na_position="last")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prepared.to_csv(OUTPUT_PATH, index=False, compression="gzip")

    print(f"Wrote {len(prepared):,} rows to {OUTPUT_PATH}")
    print(f"Output size: {OUTPUT_PATH.stat().st_size / 1_000_000:.1f} MB")
    print(f"Salary coverage: {prepared['salary_available'].mean():.1%}")


if __name__ == "__main__":
    main()

