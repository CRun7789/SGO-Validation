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

7. Displays dataset information

8. Saves the combined data to `combined_irs_data.csv`

## SGO Scoring Engine

After the initial IRS filtering step narrows the dataset down to ~36,000 likely SGO candidates, a second scoring pass is applied using a purpose-built SGO scoring engine (`sgo_scorer.py`) derived from the sortingSGOs project. Every organization that passes the IRS filter is scored individually, and the two scores are then combined into a single confidence value used to rank results.

### How the scorer works

Each organization is routed through one of three scoring paths based on its IRS classification data:

- **NTEE path** — the organization has an NTEE code beginning with `B` (Education). Scored using NTEE-specific weights for code precision, affiliation, group, foundation type, and classification.
- **No-NTEE path** — no NTEE code is present but the activity code matches `31150120` (scholarship/tuition). Scored using affiliation, group, foundation type, and classification signals.
- **Unclassified path** — everything else. Scored conservatively with a negative baseline and small positive adjustments for valid IRS fields.

All paths also incorporate:
- **Name scoring** — keywords strongly associated with SGOs (e.g. `SCHOLARSHIP`, `TUITION`, `GRANTING`) add points; disqualifying terms subtract points.
- **Revenue signals** — organizations with both revenue and income reported receive a small bonus.
- **Certified SGO list** — a curated list of known SGOs by state. Any organization whose name matches this list is automatically assigned a score of 100 regardless of IRS fields.
- **Hard disqualifiers** — organizations that fail basic IRS checks (deductibility ≠ 1, wrong subsection, or private foundation filing requirement) receive a score of 0.

### Combined score weighting

The two scores are merged into a single `Average Score` using path-dependent weighting:

| Scoring Path | IRS Filter Score Weight | SGO Scorer Weight |
|---|---|---|
| NTEE or Certified | 50% | 50% |
| No-NTEE, Unclassified, or Disqualified | 65% | 35% |

This gives greater weight to the IRS structural score when the SGO scorer had less classification signal to work with.

### Output files

Running `python main.py` produces two files in the project folder:

**`combined_irs_data.csv`** — full raw dataset with all IRS columns plus the three scoring columns (`irs_filter_score`, `sgo_scorer_score`, `combined_score`) and `scoring_path`. Useful as a data source for further analysis.

**`combined_irs_data_scored.xlsx`** — formatted Excel workbook with:
- Visible columns: Region, State, Organization Name, Org Classification (NTEE), Business Address, Name (ICO), Email, Website, Phone Number, Ruling Date, Scoring Classification, Average Score
- Raw IRS data columns hidden on the left (unhide to access)
- Individual scorer sub-scores hidden adjacent to Average Score (unhide to compare)
- Frozen header row, auto-filters on all columns, and rows sorted highest to lowest by Average Score

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
- **RULING_DATE** - Ruling date (YYYYMM format, e.g., 202601 for Jan 2026)
- **DEDUCTIBILITY** - Deductibility code
- **FOUNDATION** - Foundation type code
- **PF_FILING_REQ_CD** - Private foundation filing requirement code
- **NTEE_CD** - National Taxonomy of Exempt Entities code
- **region** - Added by script to indicate source region (Northeast, Mid-Atlantic and Great Lakes, Gulf Coast and Pacific Coast, All Other Areas)

