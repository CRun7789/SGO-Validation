# IRS SOI Data Downloader

This project downloads IRS Statistics of Income (SOI) data from multiple regions and combines them into a single dataset.

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

## Output

The script will generate:
- Console output showing download progress and statistics
- `combined_irs_data.csv` - The combined dataset from all regions

## Column Names

The IRS data includes the following columns:

- **EIN** - Employer Identification Number
- **NAME** - Organization name
- **ICO** - In Care Of
- **STREET** - Street address
- **CITY** - City
- **STATE** - State
- **ZIP** - ZIP code
- **GROUP** - Group code
- **SUBSECTION** - Subsection
- **AFFILIATION** - Affiliation code
- **CLASSIFICATION** - Organization classification
- **RULING_DATE** - Ruling date (YYYYMM format, e.g., 202601 for Jan 2026)
- **DEDUCTIBILITY** - Deductibility code
- **FOUNDATION** - Foundation type code
- **ACTIVITY** - Activity code
- **ORGANIZATION** - Organization type
- **STATUS** - Status code
- **TAX_PERIOD** - Tax period
- **ASSET_CD** - Asset code
- **INCOME_CD** - Income code
- **FILING_REQ_CD** - Filing requirement code
- **PF_FILING_REQ_CD** - Private foundation filing requirement code
- **ACCT_PD** - Accounting period
- **ASSET_AMT** - Asset amount
- **INCOME_AMT** - Income amount
- **REVENUE_AMT** - Revenue amount
- **NTEE_CD** - National Taxonomy of Exempt Entities code
- **SORT_NAME** - Sort name
- **region** - Added by script to indicate source region (Northeast, Mid-Atlantic and Great Lakes, Gulf Coast and Pacific Coast, All Other Areas)

