import pandas as pd
from irs_data_filter import filter_organizations


def test_filtering_with_test_data():
    """Test the filtering function with hardcoded test data."""
    # Hardcoded test data
    test_data = {
        'EIN': [462286764, 860957419],
        'NAME': ['SCHOLARSHIPS FOR KIDS INC', 'ARIZONA ADVENTIST SCHOLARSHIPS INC'],
        'ICO': ['% NICOLE CUNNINGHAM', ''],
        'STREET': ['PO BOX 10204', 'PO BOX 12340'],
        'CITY': ['BIRMINGHAM', 'SCOTTSDALE'],
        'STATE': ['AL', 'AZ'],
        'ZIP': ['35202-0204', '85267-2340'],
        'GROUP': [0, 1071],
        'SUBSECTION': [3, 3],
        'AFFILIATION': [3, 9],
        'CLASSIFICATION': [1000, 7000],
        'RULING': [201306, 194704],
        'DEDUCTIBILITY': [1, 1],
        'FOUNDATION': [15, 10],
        'ACTIVITY': [0, 211029000],
        'ORGANIZATION': [1, 5],
        'STATUS': [1, 1],
        'TAX_PERIOD': [202412, None],
        'ASSET_CD': [8, 0],
        'INCOME_CD': [8, 0],
        'FILING_REQ_CD': [1, 6],
        'PF_FILING_REQ_CD': [0, 0],
        'ACCT_PD': [12, 12],
        'ASSET_AMT': [45035594, None],
        'INCOME_AMT': [31870886, None],
        'REVENUE_AMT': [24884088, None],
        'NTEE_CD': ['B82', ''],
        'SORT_NAME': ['', '']
    }
    
    test_df = pd.DataFrame(test_data)
    print(f"\nRunning test with {len(test_df)} test records...")
    
    try:
        # Apply filter
        filtered_df = filter_organizations(test_df)
        
        # Check results
        expected_count = 2
        actual_count = len(filtered_df)
        
        if actual_count == expected_count:
            print(f"✓ Test PASSED: Expected {expected_count} rows, got {actual_count}")
            print(f"  Organizations that passed filtering:")
            for idx, row in filtered_df.iterrows():
                print(f"    - {row['NAME']} (EIN: {row['EIN']})")
            return True
        else:
            print(f"✗ Test FAILED: Expected {expected_count} rows, got {actual_count}")
            print(f"  Filtered data:")
            print(filtered_df[['EIN', 'NAME']])
            return False
    
    except Exception as e:
        print(f"✗ Test ERROR: {e}")
        return False


if __name__ == "__main__":
    test_filtering_with_test_data()
