# IRS Nonprofit Organization Data Downloader

This project downloads IRS nonprofit data from multiple regions, combines them into a single dataset, filters them down to likely Scholarship Granting Organizations (SGOs), and returns a shortened list of organizations with an added SGO likelihood rating & associated confidence score.

## Files

- `main.py` - Main entry point that orchestrates the entire IRS data processing pipeline
- `irs_data_download.py` - Functions for downloading and processing IRS data files
- `irs_data_filter.py` - Functions for filtering IRS organization data
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

