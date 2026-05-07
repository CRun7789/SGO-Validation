import pandas as pd


def filter_organizations(df):
    """
    Filter organizations based on criteria.
    Organizations must meet at least 5 of the following 6 criteria to be kept.
    """
    # Define the valid values for each criterion
    valid_ntee_codes = ['B01', 'B12', 'B20', 'B21', 'B24', 'B25', 'B82', 'B90', 'B99',
                        'P20', 'P82', 'P84', 'T30', 'T31', 'T99', 'W05']
    valid_subsection = 3
    valid_affiliation = [3, 9]
    valid_classification = [1000, 1200, 1700, 2000]
    valid_deductibility = 1
    valid_foundation = [10, 15, 16]

    def count_criteria_met(row):
        """Count how many criteria a row meets."""
        criteria_count = 0

        # Criterion 1: NTEE_CD
        if 'NTEE_CD' in row.index:
            ntee_value = str(row['NTEE_CD']).strip()
            if ntee_value in valid_ntee_codes or ntee_value == '0' or ntee_value == '' or pd.isna(row['NTEE_CD']):
                criteria_count += 1

        # Criterion 2: SUBSECTION
        if 'SUBSECTION' in row.index:
            if pd.notna(row['SUBSECTION']) and row['SUBSECTION'] == valid_subsection:
                criteria_count += 1

        # Criterion 3: AFFILIATION
        if 'AFFILIATION' in row.index:
            if pd.notna(row['AFFILIATION']) and row['AFFILIATION'] in valid_affiliation:
                criteria_count += 1

        # Criterion 4: CLASSIFICATION
        if 'CLASSIFICATION' in row.index:
            if pd.notna(row['CLASSIFICATION']) and row['CLASSIFICATION'] in valid_classification:
                criteria_count += 1

        # Criterion 5: DEDUCTIBILITY
        if 'DEDUCTIBILITY' in row.index:
            if pd.notna(row['DEDUCTIBILITY']) and row['DEDUCTIBILITY'] == valid_deductibility:
                criteria_count += 1

        # Criterion 6: FOUNDATION
        if 'FOUNDATION' in row.index:
            if pd.notna(row['FOUNDATION']) and row['FOUNDATION'] in valid_foundation:
                criteria_count += 1

        return criteria_count

    # Apply the criteria check to each row
    df['criteria_met'] = df.apply(count_criteria_met, axis=1)

    # Filter to keep only rows meeting at least 5 criteria
    filtered_df = df[df['criteria_met'] >= 5].copy()

    # Drop the temporary criteria_met column
    filtered_df = filtered_df.drop(columns=['criteria_met'])

    return filtered_df