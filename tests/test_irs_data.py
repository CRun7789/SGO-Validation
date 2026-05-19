import pandas as pd
from src.processing.irs_data_filter import filter_by_irs_criteria, filter_by_name, filter_out_avoid_words


def test_filtering_with_test_data():
    """Test the filtering function with hardcoded test data."""
    # Hardcoded test data
    test_data = {
        'EIN': [462286764, 860957419, 123456789],
        'NAME': ['SCHOLARSHIPS FOR KIDS INC', 'ARIZONA ADVENTIST SCHOLARSHIPS INC', 'UNRELATED NONPROFIT INC'],
        'ICO': ['% NICOLE CUNNINGHAM', '', ''],
        'STREET': ['PO BOX 10204', 'PO BOX 12340', 'PO BOX 99999'],
        'CITY': ['BIRMINGHAM', 'SCOTTSDALE', 'CHICAGO'],
        'STATE': ['AL', 'AZ', 'IL'],
        'ZIP': ['35202-0204', '85267-2340', '60601'],
        'GROUP': [0, 1071, 0],
        'SUBSECTION': [3, 3, 3],
        'AFFILIATION': [3, 9, 3],
        'CLASSIFICATION': [1000, 7000, 1000],
        'RULING': [201306, 194704, 202312],
        'DEDUCTIBILITY': [1, 1, 1],
        'FOUNDATION': [15, 10, 10],
        'ACTIVITY': [0, 211029000, 100000],
        'ORGANIZATION': [1, 5, 1],
        'STATUS': [1, 1, 1],
        'TAX_PERIOD': [202412, None, 202412],
        'ASSET_CD': [8, 0, 8],
        'INCOME_CD': [8, 0, 8],
        'FILING_REQ_CD': [1, 6, 1],
        'PF_FILING_REQ_CD': [0, 0, 0],
        'ACCT_PD': [12, 12, 12],
        'ASSET_AMT': [45035594, None, 1000000],
        'INCOME_AMT': [31870886, None, 1000000],
        'REVENUE_AMT': [24884088, None, 1500000],
        'NTEE_CD': ['B82', '', 'B82'],
        'SORT_NAME': ['', '', '']
    }
    
    test_df = pd.DataFrame(test_data)
    print(f"\nRunning test with {len(test_df)} test records...")
    
    try:
        # Apply filter
        filtered_df = filter_by_irs_criteria(test_df)
        
        # Check results
        expected_count = 3
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


def test_name_filtering():
    """Test the name-based filtering separately from numeric criteria."""
    test_data = {
        'EIN': [462286764, 860957419, 123456789],
        'NAME': ['SCHOLARSHIPS FOR KIDS INC', 'ARIZONA ADVENTIST SCHOLARSHIPS INC', 'UNRELATED NONPROFIT INC'],
        'NTEE_CD': ['B82', '', 'B82']
    }
    test_df = pd.DataFrame(test_data)

    filtered_df = filter_by_name(test_df)
    expected_count = 2
    actual_count = len(filtered_df)

    print(f"\nRunning name filter test with {len(test_df)} test records...")
    if actual_count == expected_count:
        print(f"✓ Name filter test PASSED: Expected {expected_count} rows, got {actual_count}")
        return True
    else:
        print(f"✗ Name filter test FAILED: Expected {expected_count} rows, got {actual_count}")
        print(filtered_df[['EIN', 'NAME']])
        return False


def test_avoid_word_filtering():
    """Test exclusion filtering for NAME values containing avoid words."""
    test_data = {
        'EIN': [111111111, 222222222, 333333333],
        'NAME': ['GOOD SCHOLARSHIP FUND', 'FRANCE EDUCATION GRANT', 'TUITIONSCHOICE ORGANIZATION']
    }
    test_df = pd.DataFrame(test_data)

    filtered_df = filter_out_avoid_words(test_df)
    expected_count = 1
    actual_count = len(filtered_df)

    print(f"\nRunning avoid-word filter test with {len(test_df)} test records...")
    if actual_count == expected_count:
        print(f"✓ Avoid-word filter test PASSED: Expected {expected_count} rows, got {actual_count}")
        return True
    else:
        print(f"✗ Avoid-word filter test FAILED: Expected {expected_count} rows, got {actual_count}")
        print(filtered_df[['EIN', 'NAME']])
        return False


if __name__ == "__main__":
    test_filtering_with_test_data()
    test_name_filtering()
