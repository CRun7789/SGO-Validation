import pandas as pd
from irs_data_download import download_and_concatenate_irs_files
from irs_data_filter import filter_organizations, filter_by_name


def main():
    """Main function to download, filter, and process IRS data."""
    print("="*60)
    print("IRS SOI Data Processing Pipeline")
    print("="*60)

    # Download and concatenate all IRS files
    print("\nDownloading IRS data from all regions...")
    print("-"*40)
    irs_data = download_and_concatenate_irs_files()

    if irs_data is not None:
        print(f"\nBefore filtering: {len(irs_data)} rows")

        # Apply filtering
        irs_data = filter_organizations(irs_data)
        irs_data = filter_by_name(irs_data)
        print(f"After filtering: {len(irs_data)} rows")

        # Sort by ruling date (most recent first)
        # RULING is in YYYYMM format (e.g., 202601 for Jan 2026)
        if 'RULING' in irs_data.columns:
            # Convert to numeric for proper sorting, then sort descending
            irs_data['RULING'] = pd.to_numeric(irs_data['RULING'], errors='coerce')
            irs_data = irs_data.sort_values('RULING', ascending=False, na_position='last').reset_index(drop=True)
            print(f"Data sorted by ruling date (most recent first)")

        # Display basic information about the dataset
        print("\nDataset Info:")
        print(f"Shape: {irs_data.shape}")
        print(f"\nColumns: {list(irs_data.columns)}")
        print(f"\nFirst few rows:")
        print(irs_data.head())

        # Optional: Save to CSV file
        output_file = "combined_irs_data.csv"
        irs_data.to_csv(output_file, index=False)
        print(f"\nData saved to {output_file}")

        print("\n" + "="*60)
        print("Processing complete!")
        print("="*60)
    else:
        print("Failed to download IRS data. Exiting.")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())