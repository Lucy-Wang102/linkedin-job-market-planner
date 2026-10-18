from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="LinkedIn Job Market Planner",
    page_icon="💼",
    layout="wide",
)

DATA_PATH = Path(__file__).parent / "data" / "dashboard_jobs.csv.gz"


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    """Load the compact deployment dataset produced by prepare_data.py."""
    if not path.exists():
        return pd.DataFrame()

    jobs = pd.read_csv(path, compression="gzip", parse_dates=["listed_date"])
    numeric_columns = ["annual_salary_mid", "applications", "views"]
    for column in numeric_columns:
        jobs[column] = pd.to_numeric(jobs[column], errors="coerce")
    jobs["remote_allowed"] = jobs["remote_allowed"].fillna(False).astype(bool)
    jobs["salary_available"] = jobs["annual_salary_mid"].notna()
    return jobs


def metric_text(value: float) -> str:
    if pd.isna(value):
        return "Not available"
    return f"${value:,.0f}"


jobs = load_data(DATA_PATH)

if jobs.empty:
    st.error(
        "The prepared data file is missing. Run `python prepare_data.py` after "
        "placing the Kaggle CSV in the `raw_data` folder, then commit "
        "`data/dashboard_jobs.csv.gz` to GitHub."
    )
    st.stop()

st.title("LinkedIn Job Market Planner")
st.caption(
    "A decision dashboard for university career-services teams planning employer "
    "outreach and student workshops. Data: LinkedIn Job Postings (2023–2024)."
)

with st.sidebar:
    st.header("Choose a market segment")

    experience_options = sorted(jobs["experience_level"].dropna().unique())
    selected_experience = st.multiselect(
        "Experience level",
        experience_options,
        default=experience_options,
    )

    work_type_options = sorted(jobs["work_type"].dropna().unique())
    selected_work_types = st.multiselect(
        "Work type",
        work_type_options,
        default=work_type_options,
    )

    remote_choice = st.radio(
        "Remote availability",
        ["All postings", "Remote allowed", "Not marked remote"],
    )

    location_query = st.text_input(
        "Location contains",
        placeholder="Example: New York or California",
    ).strip()

    salary_only = st.checkbox("Only postings with usable salary data")

    st.divider()
    st.subheader("Recommendation settings")
    salary_weight = st.slider(
        "Weight placed on salary",
        min_value=0,
        max_value=100,
        value=40,
        step=10,
        help=(
            "0% ranks segments only by number of openings; 100% ranks them only "
            "by median annual salary."
        ),
    ) / 100

filtered = jobs[
    jobs["experience_level"].isin(selected_experience)
    & jobs["work_type"].isin(selected_work_types)
].copy()

if remote_choice == "Remote allowed":
    filtered = filtered[filtered["remote_allowed"]]
elif remote_choice == "Not marked remote":
    filtered = filtered[~filtered["remote_allowed"]]

if location_query:
    filtered = filtered[
        filtered["location"].str.contains(location_query, case=False, na=False)
    ]

if salary_only:
    filtered = filtered[filtered["salary_available"]]

if filtered.empty:
    st.warning("No postings match these filters. Broaden the selections in the sidebar.")
    st.stop()

salary_count = int(filtered["salary_available"].sum())
salary_coverage = salary_count / len(filtered)
remote_share = filtered["remote_allowed"].mean()
median_salary = filtered["annual_salary_mid"].median()

metric_columns = st.columns(4)
metric_columns[0].metric("Matching postings", f"{len(filtered):,}")
metric_columns[1].metric("Remote allowed", f"{remote_share:.1%}")
metric_columns[2].metric("Salary disclosed", f"{salary_coverage:.1%}")
metric_columns[3].metric("Median annual salary", metric_text(median_salary))

st.caption(
    "Salary metrics use annualized USD postings with plausible values. Because many "
    "postings omit salary, compensation results describe only the disclosed subset."
)

overview_tab, salary_tab, decision_tab, notes_tab = st.tabs(
    ["Market overview", "Compensation", "Decision table", "Data notes"]
)

with overview_tab:
    left, right = st.columns(2)

    experience_counts = (
        filtered.groupby("experience_level", as_index=False)
        .agg(postings=("job_id", "nunique"))
        .sort_values("postings", ascending=False)
    )
    experience_chart = (
        alt.Chart(experience_counts)
        .mark_bar(cornerRadiusEnd=4, color="#2563EB")
        .encode(
            x=alt.X("postings:Q", title="Number of postings"),
            y=alt.Y(
                "experience_level:N",
                title="Experience level",
                sort="-x",
            ),
            tooltip=["experience_level:N", alt.Tooltip("postings:Q", format=",")],
        )
        .properties(title="Demand by experience level", height=330)
    )
    left.altair_chart(experience_chart, width="stretch")

    work_type_counts = (
        filtered.groupby("work_type", as_index=False)
        .agg(postings=("job_id", "nunique"))
        .sort_values("postings", ascending=False)
    )
    work_type_chart = (
        alt.Chart(work_type_counts)
        .mark_bar(cornerRadiusEnd=4, color="#0F766E")
        .encode(
            x=alt.X("postings:Q", title="Number of postings"),
            y=alt.Y("work_type:N", title="Work type", sort="-x"),
            tooltip=["work_type:N", alt.Tooltip("postings:Q", format=",")],
        )
        .properties(title="Demand by work type", height=330)
    )
    right.altair_chart(work_type_chart, width="stretch")

    top_locations = (
        filtered[filtered["location"] != "Not specified"]
        .groupby("location", as_index=False)
        .agg(postings=("job_id", "nunique"))
        .nlargest(15, "postings")
    )
    location_chart = (
        alt.Chart(top_locations)
        .mark_bar(cornerRadiusEnd=4, color="#7C3AED")
        .encode(
            x=alt.X("postings:Q", title="Number of postings"),
            y=alt.Y("location:N", title=None, sort="-x"),
            tooltip=["location:N", alt.Tooltip("postings:Q", format=",")],
        )
        .properties(title="Top locations in the selected market", height=420)
    )
    st.altair_chart(location_chart, width="stretch")

with salary_tab:
    salary_data = filtered.dropna(subset=["annual_salary_mid"])
    if salary_data.empty:
        st.info("No usable salary observations are available for this selection.")
    else:
        salary_by_experience = (
            salary_data.groupby("experience_level", as_index=False)
            .agg(
                median_salary=("annual_salary_mid", "median"),
                salary_postings=("job_id", "nunique"),
            )
            .sort_values("median_salary", ascending=False)
        )
        salary_chart = (
            alt.Chart(salary_by_experience)
            .mark_bar(cornerRadiusEnd=4, color="#EA580C")
            .encode(
                x=alt.X(
                    "median_salary:Q",
                    title="Median annualized salary (USD)",
                    axis=alt.Axis(format="$,.0f"),
                ),
                y=alt.Y("experience_level:N", title=None, sort="-x"),
                tooltip=[
                    "experience_level:N",
                    alt.Tooltip("median_salary:Q", format="$,.0f"),
                    alt.Tooltip("salary_postings:Q", format=","),
                ],
            )
            .properties(title="Median disclosed salary by experience level", height=360)
        )
        st.altair_chart(salary_chart, width="stretch")

        st.caption(
            f"This chart is based on {len(salary_data):,} postings with usable salary "
            f"data ({len(salary_data) / len(filtered):.1%} of the current selection)."
        )

with decision_tab:
    segment_table = (
        filtered.groupby(["experience_level", "work_type"], as_index=False)
        .agg(
            postings=("job_id", "nunique"),
            median_salary=("annual_salary_mid", "median"),
            salary_observations=("annual_salary_mid", "count"),
            remote_share=("remote_allowed", "mean"),
        )
    )
    segment_table["salary_coverage"] = (
        segment_table["salary_observations"] / segment_table["postings"]
    )

    minimum_segment_size = max(10, int(len(filtered) * 0.002))
    eligible = segment_table[
        segment_table["postings"] >= minimum_segment_size
    ].copy()

    if eligible.empty:
        st.info("The selection is too narrow to produce a stable segment recommendation.")
    else:
        volume_rank = eligible["postings"].rank(pct=True)
        salary_rank = eligible["median_salary"].rank(pct=True).fillna(0)
        eligible["priority_score"] = (
            (1 - salary_weight) * volume_rank + salary_weight * salary_rank
        ) * 100
        eligible = eligible.sort_values("priority_score", ascending=False)
        recommendation = eligible.iloc[0]

        st.success(
            "Recommended focus: "
            f"**{recommendation['experience_level']} / "
            f"{recommendation['work_type']}** — "
            f"{int(recommendation['postings']):,} postings, "
            f"{recommendation['remote_share']:.0%} remote allowed, and "
            f"{metric_text(recommendation['median_salary'])} median disclosed salary."
        )
        st.caption(
            "The recommendation combines relative posting volume and median salary "
            f"using the sidebar weights. Segments need at least {minimum_segment_size} "
            "postings to be ranked. It is a planning aid, not a causal claim."
        )

        opportunity_chart = (
            alt.Chart(eligible)
            .mark_circle(opacity=0.78, stroke="white", strokeWidth=1)
            .encode(
                x=alt.X("postings:Q", title="Number of postings"),
                y=alt.Y(
                    "median_salary:Q",
                    title="Median annualized salary (USD)",
                    axis=alt.Axis(format="$,.0f"),
                ),
                size=alt.Size(
                    "remote_share:Q",
                    title="Remote share",
                    scale=alt.Scale(range=[100, 900]),
                ),
                color=alt.Color(
                    "experience_level:N",
                    title="Experience level",
                    scale=alt.Scale(scheme="tableau10"),
                ),
                tooltip=[
                    "experience_level:N",
                    "work_type:N",
                    alt.Tooltip("postings:Q", format=","),
                    alt.Tooltip("median_salary:Q", format="$,.0f"),
                    alt.Tooltip("remote_share:Q", format=".1%"),
                    alt.Tooltip("salary_coverage:Q", format=".1%"),
                    alt.Tooltip("priority_score:Q", format=".1f"),
                ],
            )
            .properties(title="Opportunity map", height=440)
            .interactive()
        )
        st.altair_chart(opportunity_chart, width="stretch")

        display_table = eligible[
            [
                "experience_level",
                "work_type",
                "postings",
                "median_salary",
                "remote_share",
                "salary_coverage",
                "priority_score",
            ]
        ].copy()
        st.dataframe(
            display_table,
            width="stretch",
            hide_index=True,
            column_config={
                "experience_level": "Experience level",
                "work_type": "Work type",
                "postings": st.column_config.NumberColumn("Postings", format="%d"),
                "median_salary": st.column_config.NumberColumn(
                    "Median salary", format="$%.0f"
                ),
                "remote_share": st.column_config.ProgressColumn(
                    "Remote share", min_value=0, max_value=1, format="percent"
                ),
                "salary_coverage": st.column_config.ProgressColumn(
                    "Salary coverage", min_value=0, max_value=1, format="percent"
                ),
                "priority_score": st.column_config.NumberColumn(
                    "Priority score", format="%.1f"
                ),
            },
        )

with notes_tab:
    st.subheader("How to use this dashboard")
    st.markdown(
        """
        1. Use the filters to define the student population or employer market being planned for.
        2. Review posting volume to see where hiring demand is concentrated.
        3. Check salary coverage before using compensation in a decision.
        4. Adjust the salary weight to compare a demand-first and salary-first priority.
        5. Use the ranked segment as a starting point for employer outreach or a workshop topic.
        """
    )

    st.subheader("Important limitations")
    st.markdown(
        """
        - The dataset is a historical snapshot of LinkedIn postings from 2023–2024, not a live labor-market feed.
        - A job posting is not the same as a completed hire, and duplicate or expired listings may remain.
        - Salary disclosure is incomplete and may not be representative of postings without salary data.
        - `remote_allowed=False` means the posting was not marked as remote; it does not prove that remote work was impossible.
        - Results describe this dataset and should be combined with local student needs and employer knowledge.
        """
    )

    st.subheader("Source")
    st.markdown(
        "[LinkedIn Job Postings (2023–2024) by Arsh Koneru on Kaggle]"
        "(https://www.kaggle.com/datasets/arshkon/linkedin-job-postings) — "
        "licensed CC BY-SA 4.0."
    )

