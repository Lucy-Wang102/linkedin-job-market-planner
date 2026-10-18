# linkedin-job-market-planner
An interactive Streamlit dashboard for exploring LinkedIn job demand, salary, remote work, and career-service priorities.
# LinkedIn Job Market Planner

**Live app:** I will add the Streamlit Community Cloud link here after deployment.

## Purpose and intended user

I built this dashboard for a manager at a university career center. The manager has to decide where to spend limited staff time: which employers to contact and which kinds of workshops to offer students. I therefore focused on a practical question: which parts of the job market have enough openings to deserve attention, and what do those openings look like in terms of salary and remote work? The filters let the manager narrow the data to a student group or location before comparing experience levels and work types.

## The decision the dashboard supports

The dashboard is meant to help the manager choose one employment segment for the next round of outreach or student programming. For example, the manager can compare entry-level full-time positions with internships, or look at one city before planning an employer event. I based the recommendation on two things: the number of postings and the median disclosed salary. Since different career centers may value these differently, the user can change the salary weight instead of relying on a ranking whose priorities are hidden.

## What I included and why

- I put four summary measures at the top: number of matching postings, remote share, salary coverage, and median disclosed annual salary. These give the user a quick sense of the selected market.
- The experience, work type, remote, and location filters make it possible to look at a specific group instead of treating the whole dataset as one market.
- The demand charts show where postings are concentrated by experience level, work type, and location.
- The compensation chart includes the number of usable salary observations because the salary field has many missing values.
- The decision table puts posting volume, salary, remote share, and salary coverage together. I also included an opportunity map so the trade-off between demand and pay is easier to see.

## What I left out

I left out full job descriptions, application links, company descriptions, and most company-level fields. They are available in the original dataset, but they do not help much with the resource decision and would make this dashboard harder to read. I also chose not to treat views or application counts as evidence of hiring success. Those fields are incomplete, and viewing or applying for a job does not mean that someone was hired. I did not rank individual employers either, because the dataset does not tell me enough about workplace quality or actual hiring outcomes to support that conclusion.

## Data preparation

The app reads a smaller file that I created from the Kaggle postings table. I removed duplicate job IDs and labeled missing categories as `Not specified`. To compare salaries reported under different pay periods, I converted them to estimated annual amounts using hourly × 2,080, weekly × 52, biweekly × 26, and monthly × 12. The salary charts use USD observations between $10,000 and $1,000,000 after conversion so that obvious unit problems do not control the results. I did not fill in missing salaries; instead, the dashboard reports salary coverage so the user can see how much data each comparison is based on.

## Refresh schedule

If a career center used this dashboard in practice, I would update it once a month. Hiring priorities can change fairly quickly, but a weekly update would probably add noise without changing program decisions. The Kaggle dataset used here is a historical snapshot from 2023–2024 rather than a live feed, so this class project can only be refreshed when the publisher releases a newer version. Even after an update, I would keep the date and source limitations visible.

## Limitations

- The dataset is a historical snapshot, so it should not be read as the current LinkedIn job market.
- The number of postings is not the same as the number of people eventually hired.
- Many postings do not disclose salary. The disclosed salaries may differ systematically from the missing ones.
- `Not marked remote` means that the posting was not tagged as remote; it does not prove that remote work was unavailable.
- The dashboard summarizes patterns in this dataset. It does not show that one job characteristic causes another.

## Data source

I used [LinkedIn Job Postings (2023–2024)](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings) by Arsh Koneru and a collaborator. According to the Kaggle description, it contains more than 124,000 LinkedIn postings and includes job, salary, location, work-type, and company information. The dataset is licensed under CC BY-SA 4.0.

## Reproduce the deployment data

1. Download and unzip the Kaggle dataset.
2. Put `postings.csv` or `job_postings.csv` anywhere inside a folder named `raw_data` in this project.
3. Install the dependencies and run the preparation script:

```bash
pip install -r requirements.txt
python prepare_data.py
```

4. Check that the script created `data/dashboard_jobs.csv.gz`.
5. Run the app locally:

```bash
streamlit run app.py
```

I excluded `raw_data` from Git because the original source file is large. The smaller `data/dashboard_jobs.csv.gz` file should be committed so the deployed app can start without Kaggle credentials. The included `runtime.txt` sets the deployment to Python 3.12, which is compatible with the package versions in `requirements.txt`.

## Deploy on Streamlit Community Cloud

1. Push the project to a repository under my own GitHub account.
2. Sign in to Streamlit Community Cloud with my own account.
3. Create an app from the repository and use `app.py` as the entrypoint.
4. After the app is online, add its public URL at the top of this README and to the first Markdown cell of `phone-trade-in.ipynb`.
