import requests
import pandas as pd
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from io import StringIO

# IRS CSV file URLs for different regions
IRS_FILE_URLS = {
    "Northeast": "https://www.irs.gov/pub/irs-soi/eo1.csv",
    "Mid-Atlantic and Great Lakes": "https://www.irs.gov/pub/irs-soi/eo2.csv",
    "Gulf Coast and Pacific Coast": "https://www.irs.gov/pub/irs-soi/eo3.csv",
    "All Other Areas": "https://www.irs.gov/pub/irs-soi/eo4.csv",
}

def download_irs_file(url):
    """Download IRS CSV file from the given URL."""
    try:
        response = requests.get(url, verify=False) # Disables SSL verification for this request
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        return None

def load_csv_to_dataframe(csv_text):
    """Load CSV text into a pandas DataFrame."""
    if csv_text is None:
        return None
    try:
        df = pd.read_csv(StringIO(csv_text))
        return df
    except pd.errors.ParserError as e:
        print(f"Error parsing CSV: {e}")
        return None

def download_and_concatenate_irs_files():
    """Download all IRS files and concatenate them into one DataFrame."""
    dataframes = []
    
    for region, url in IRS_FILE_URLS.items():
        print(f"Downloading {region} region data...")
        csv_text = download_irs_file(url)
        
        if csv_text:
            df = load_csv_to_dataframe(csv_text)
            if df is not None:
                # Add region column for reference
                df['region'] = region
                dataframes.append(df)
                print(f"✓ Successfully loaded {region} region ({len(df)} rows)")
            else:
                print(f"✗ Failed to parse {region} region CSV")
        else:
            print(f"✗ Failed to download {region} region")
    
    # Concatenate all dataframes
    if dataframes:
        combined_df = pd.concat(dataframes, ignore_index=True)
        print(f"\nCombined dataset: {len(combined_df)} rows")
        return combined_df
    else:
        print("No data was successfully downloaded.")
        return None
