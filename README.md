# IRS Nonprofit Organization Data Downloader

This project downloads IRS nonprofit data from multiple regions, combines them into a single dataset, filters them down to likely Scholarship Granting Organizations (SGOs), and returns a shortened list of organizations with an added SGO likelihood rating & associated confidence score.

## Files

- `main.py` - Main entry point that orchestrates the entire IRS data processing pipeline
- `irs_data_download.py` - Functions for downloading and processing IRS data files
- `irs_data_filter.py` - Functions for filtering IRS organization data
- `sgo_scorer.py` - SGO scoring engine (integrated from the sortingSGOs project) that applies a second confidence scoring pass to the filtered dataset
- `test_irs_data.py` - Unit tests for filtering functionality
- `requirements.txt` - Python dependencies

## Setup

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the main script to download all IRS regional data, apply filtering, and generate the final dataset:

```bash
python main.py
```

### What the pipeline does:

1. Downloads IRS CSV files for 4 regions:
   - Northeast (eo1.csv)
   - Mid-Atlantic and Great Lakes (eo2.csv)
   - Gulf Coast and Pacific Coast (eo3.csv)
   - All Other Areas (eo4.csv)

2. Loads each CSV into a pandas DataFrame

3. Adds a "region" column to identify the source region

4. Concatenates all DataFrames into one combined dataset

5. Applies filtering criteria (organizations must meet at least 5 of 6 criteria)

6. Sorts data by ruling date (most recent first)

7. Applies a second scoring pass (`sgo_scorer.py`) to the filtered dataset, scoring each organization by NTEE classification, name keywords, and IRS field signals

8. Combines both scores into a weighted average confidence score and sorts organizations highest to lowest

9. Saves the results to `combined_irs_data.csv` (raw) and `combined_irs_data_scored.xlsx` (formatted, with hidden raw columns, frozen header, and auto-filters)

## Column Names

The IRS data includes the following relevant columns:

- **EIN** - Employer Identification Number
- **NAME** - Organization name
- **ICO** - In Care Of
- **STREET** - Street address
- **CITY** - City
- **STATE** - State
- **ZIP** - ZIP code
- **SUBSECTION** - Subsection
- **AFFILIATION** - Affiliation code
- **CLASSIFICATION** - Organization classification
- **RULING** - Ruling date (YYYYMM format, e.g., 202601 for Jan 2026)
- **DEDUCTIBILITY** - Deductibility code
- **FOUNDATION** - Foundation type code
- **PF_FILING_REQ_CD** - Private foundation filing requirement code
- **NTEE_CD** - National Taxonomy of Exempt Entities code
- **region** - Added by script to indicate source region (Northeast, Mid-Atlantic and Great Lakes, Gulf Coast and Pacific Coast, All Other Areas)

## Output Columns

The final outputs include raw IRS fields plus derived scoring columns.

- `combined_irs_data.csv` includes all input IRS columns, plus:
  - **region** — source region label
  - **irs_filter_score** — number of IRS filter criteria passed
  - **sgo_scorer_score** — second-pass confidence score from `sgo_scorer.py`
  - **scoring_path** — scoring classification path (`NTEE`, `CERTIFIED`, `NO_NTEE`, `UNCLASSIFIED`, `DISQUALIFIED`)
  - **combined_score** — weighted average of `irs_filter_score` and `sgo_scorer_score`

- `combined_irs_data_scored.xlsx` includes a formatted worksheet with visible columns:
  - **Region**
  - **State**
  - **Organization Name**
  - **Org Classification**
  - **Business Address**
  - **Name**
  - **Email**
  - **Website**
  - **Phone Number**
  - **Ruling Date**
  - **Scoring Classification**
  - **Average Score**

The Excel file also stores hidden raw IRS columns and hidden score columns for reference.

