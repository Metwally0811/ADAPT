import os
import pandas as pd
import numpy as np

# Get the current script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Path to Highload_Areas_Code.csv
highload_areas_path = os.path.join(script_dir, 'Highload_Areas_Code.csv')

# Path to Uploaded_Cell.xlsx
uploaded_cell_path = os.path.abspath(
    os.path.join(script_dir, '..', '..', 'Uploaded_Cell.xlsx')
)

# Read the Highload_Areas_Code.csv file
highload_df = pd.read_csv(highload_areas_path)

# Columns to analyze
columns_to_analyze = [
    'Serving Cell DL EARFCN',
    'Serving Cell Identity',
    'Cell Identity (eNB Part)'
]

# Create a new column that combines all three values
highload_df['Combined_Values'] = highload_df[columns_to_analyze].apply(
    lambda row: '_'.join(row.astype(str)), axis=1
)

# Group by Spot_Area_Num and find the most frequent combination
result_df = highload_df.groupby('Spot_Area_Num')['Combined_Values'].agg(
    lambda x: x.value_counts().index[0] if not x.empty else None
).reset_index()

# Split the combined values back into separate columns
result_df[columns_to_analyze] = result_df['Combined_Values'].str.split('_', expand=True)

# Drop the temporary combined column
result_df = result_df.drop('Combined_Values', axis=1)

# Save the results to a new CSV file
result_output_path = os.path.join(script_dir, 'Highload_Most_Frequent_CellsPerArea_1.csv')
result_df.to_csv(result_output_path, index=False)

print(f"Analysis results saved to: {result_output_path}")

# Read the Uploaded_Cell.xlsx file
uploaded_cell_df = pd.read_excel(uploaded_cell_path)

# Create a modified_CellName column based on the specified rules
def modify_cell_name(cell_name):
    if not isinstance(cell_name, str):
        return cell_name
    
    # Check if the cell name starts with L26_ and ends with _11, _12, _13, or _14
    if cell_name.startswith('L26_'):
        if cell_name.endswith('_11'):
            return cell_name[:-3] + '_01'
        elif cell_name.endswith('_12'):
            return cell_name[:-3] + '_02'
        elif cell_name.endswith('_13'):
            return cell_name[:-3] + '_03'
        elif cell_name.endswith('_14'):
            return cell_name[:-3] + '_04'
    
    # Return original name if no modifications needed
    return cell_name

# Apply the function to create the new column
uploaded_cell_df['modified_CellName'] = uploaded_cell_df['CellNAME'].apply(modify_cell_name)

# Save the modified DataFrame to a new Excel file
modified_cell_path = os.path.abspath(
    os.path.join(script_dir, '..', '..', 'Uploaded_Cell_modified.xlsx')
)
uploaded_cell_df.to_excel(modified_cell_path, index=False)

print(f"Modified cell file saved to: {modified_cell_path}")

# Rename columns in result_df to match with uploaded_cell_df
result_df = result_df.rename(columns={
    'Serving Cell DL EARFCN': 'DLARFCN',
    'Serving Cell Identity': 'PCI',
    'Cell Identity (eNB Part)': 'eNodeB id'
})

# Convert columns to numeric types
result_df['DLARFCN'] = pd.to_numeric(result_df['DLARFCN'], errors='coerce')
result_df['PCI'] = pd.to_numeric(result_df['PCI'], errors='coerce')
result_df['eNodeB id'] = pd.to_numeric(result_df['eNodeB id'], errors='coerce')

# Ensure the same data types in uploaded_cell_df
uploaded_cell_df['DLARFCN'] = pd.to_numeric(uploaded_cell_df['DLARFCN'], errors='coerce')
uploaded_cell_df['PCI'] = pd.to_numeric(uploaded_cell_df['PCI'], errors='coerce')
uploaded_cell_df['eNodeB id'] = pd.to_numeric(uploaded_cell_df['eNodeB id'], errors='coerce')

# Merge the dataframes based on the specified columns
merged_df = pd.merge(
    result_df,
    uploaded_cell_df[['DLARFCN', 'PCI', 'eNodeB id', 'CellNAME', 'Freq Band', 'Cell Bandwidth', 'Cell FDD TDD Indication']],
    on=['DLARFCN', 'PCI', 'eNodeB id'],
    how='left'
)

# Save the final results with the specified column order
ordered_cols = ['Spot_Area_Num', 'DLARFCN', 'PCI', 'eNodeB id', 'CellNAME', 'Freq Band', 'Cell Bandwidth', 'Cell FDD TDD Indication']
ordered_cols_cells = [col for col in ordered_cols if col in merged_df.columns]
merged_df = merged_df[ordered_cols_cells]
final_output_path = os.path.join(script_dir, 'Highload_Problem_Cells_Detailed_2.csv')
merged_df.to_csv(final_output_path, index=False)

print(f"Detailed cell information saved to: {final_output_path}")

# Additional analysis based on PCI and eNodeB id only
# Create a new result dataframe for sector and band analysis
sector_result_df = highload_df.groupby('Spot_Area_Num')[['Serving Cell Identity', 'Cell Identity (eNB Part)']].agg(
    lambda x: x.value_counts().index[0] if not x.empty else None
).reset_index()

# Rename columns to match with uploaded_cell_df
sector_result_df = sector_result_df.rename(columns={
    'Serving Cell Identity': 'PCI',
    'Cell Identity (eNB Part)': 'eNodeB id'
})

# Convert columns to numeric types
sector_result_df['PCI'] = pd.to_numeric(sector_result_df['PCI'], errors='coerce')
sector_result_df['eNodeB id'] = pd.to_numeric(sector_result_df['eNodeB id'], errors='coerce')

# Merge with uploaded_cell_df based on PCI and eNodeB id only
sector_merged_df = pd.merge(
    sector_result_df,
    uploaded_cell_df[['DLARFCN', 'PCI', 'eNodeB id', 'CellNAME', 'Freq Band', 'Cell Bandwidth', 'Cell FDD TDD Indication']],
    on=['PCI', 'eNodeB id'],
    how='left'
)

# Read Highload_Problem_Cells_Detailed_2.csv for the CellNAME-based matching approach
cell_details_path = os.path.join(script_dir, 'Highload_Problem_Cells_Detailed_2.csv')
cell_details_df = pd.read_csv(cell_details_path)

# Extract the right part of CellNAME (e.g., L1214_03 from L21_L1214_03) 
# by removing first 4 characters
cell_details_df['CellNAME_Lookup'] = cell_details_df['CellNAME'].apply(
    lambda x: x[x.find('_')+1:] if isinstance(x, str) and '_' in x else x
)

# Create a modified_CellName column for cell_details_df using the same rules
cell_details_df['modified_CellName'] = cell_details_df['CellNAME'].apply(modify_cell_name)

# Extract the right part of CellNAME
# Option 1: Extract from original CellNAME
# cell_details_df['CellNAME_Lookup'] = cell_details_df['CellNAME'].apply(
#     lambda x: x[x.find('_')+1:] if isinstance(x, str) and '_' in x else x
# )

# Option 2: Extract from modified_CellName instead
cell_details_df['CellNAME_Lookup'] = cell_details_df['modified_CellName'].apply(
    lambda x: x[x.find('_')+1:] if isinstance(x, str) and '_' in x else x
)

# Create a new dataframe with the lookup values including modified names
sector_result_df = cell_details_df[['Spot_Area_Num', 'CellNAME', 'modified_CellName', 'CellNAME_Lookup']].copy()

# Add the same transformation to the uploaded_cell_df
uploaded_cell_df['CellNAME_Lookup'] = uploaded_cell_df['modified_CellName'].apply(
    lambda x: x[x.find('_')+1:] if isinstance(x, str) and '_' in x else x
)

# Merge with uploaded_cell_df based on the CellNAME_Lookup
sector_merged_df = pd.merge(
    sector_result_df,
    uploaded_cell_df[['CellNAME_Lookup', 'DLARFCN', 'PCI', 'eNodeB id', 'CellNAME', 'Freq Band', 'Cell Bandwidth', 'Cell FDD TDD Indication']],
    on='CellNAME_Lookup',
    how='left',
    suffixes=('_original', '')
)

# If there are duplicate column names after merge, use the one from uploaded_cell_df
if 'CellNAME_original' in sector_merged_df.columns and 'CellNAME' in sector_merged_df.columns:
    sector_merged_df = sector_merged_df.drop('CellNAME_original', axis=1)

# Create the serving_band_flag by merging with the dominant cells (result_df)
# Define key columns for merging - must be present in both dataframes
key_cols = ['Spot_Area_Num', 'DLARFCN', 'PCI', 'eNodeB id']

# Ensure key columns are in both dataframes before merging
result_df_subset = result_df[key_cols].copy()
sector_merged_df_subset = sector_merged_df[key_cols].copy()

# Perform a left merge from sector_merged_df to result_df
# Rows in sector_merged_df that match result_df are the dominant ones
flag_df = pd.merge(
    sector_merged_df_subset,
    result_df_subset,
    on=key_cols,
    how='left',
    indicator='_merge' # Add indicator column to show merge status
)

# Create serving_band_flag: 1 if merged successfully (present in result_df), 0 otherwise
sector_merged_df['serving_band_flag'] = (flag_df['_merge'] == 'both').astype(int)

# Drop the temporary merge indicator column from flag_df (no longer needed after flag is set)
# (The flag_df itself is temporary and can be garbage collected)

# Read PRB Utilization file and merge DL_PRB UTILIZATION
uploaded_utilization_path = os.path.abspath(
    os.path.join(script_dir, '..', '..', 'Uploaded_Utilization.xlsx')
)
default_utilization_path = os.path.abspath(
    os.path.join(script_dir, '..', '..', 'Nasr_City_PRB_Utilization.xlsx')
)

if os.path.exists(uploaded_utilization_path):
    prb_util_df = pd.read_excel(uploaded_utilization_path)
    print(f"Using uploaded RB Utilization file: {uploaded_utilization_path}")
elif os.path.exists(default_utilization_path):
    prb_util_df = pd.read_excel(default_utilization_path)
    print(f"Using default RB Utilization file: {default_utilization_path}")
else:
    prb_util_df = pd.DataFrame() # Create empty DataFrame if neither file exists
    print("Warning: Neither uploaded nor default RB Utilization file found for Highload Recommendation.")

# Merge DL_PRB UTILIZATION into sector_merged_df based on Cell Name/CellNAME
sector_merged_df = sector_merged_df.merge(
    prb_util_df[['Cell Name', 'DL_PRB UTILIZATION']],
    left_on='CellNAME',
    right_on='Cell Name',
    how='left'
)

# Drop the extra 'Cell Name' column after merge
if 'Cell Name' in sector_merged_df.columns:
    sector_merged_df = sector_merged_df.drop('Cell Name', axis=1)

# Calculate Utilization_difference for rows with serving_band_flag == 0
def calc_util_diff_flag0(row, df):
    if row['serving_band_flag'] != 0 or pd.isna(row['DL_PRB UTILIZATION']):
        return np.nan
    
    # Check for valid CellNAME_Lookup
    if not isinstance(row['CellNAME_Lookup'], str):
        return np.nan
    
    # Find cells in same spot area with same CellNAME_Lookup but serving_band_flag==1
    matches = []
    for idx, other_row in df[df['Spot_Area_Num'] == row['Spot_Area_Num']].iterrows():
        if other_row['serving_band_flag'] != 1 or not isinstance(other_row['CellNAME_Lookup'], str):
            continue
        
        if row['CellNAME_Lookup'] == other_row['CellNAME_Lookup'] and not pd.isna(other_row['DL_PRB UTILIZATION']):
            matches.append(other_row)
    
    if not matches:
        return np.nan
    
    # Use the first matching row
    diff = matches[0]['DL_PRB UTILIZATION'] - row['DL_PRB UTILIZATION']
    return round(diff, 2)

sector_merged_df['Utilization_difference'] = sector_merged_df.apply(lambda row: calc_util_diff_flag0(row, sector_merged_df), axis=1)

# Add Recommendation column based on offload logic
sector_merged_df['Recommendation'] = ''

# Store the original DL_PRB UTILIZATION before any updates
sector_merged_df['DL_PRB UTILIZATION_old'] = sector_merged_df['DL_PRB UTILIZATION']

# Only process if DL_PRB UTILIZATION is not null
for idx, row in sector_merged_df.iterrows():
    if (
        row['serving_band_flag'] == 1 and
        row['Cell FDD TDD Indication'] == 'TDD' and
        not pd.isna(row['DL_PRB UTILIZATION']) and
        row['DLARFCN'] in [40290, 40092]
    ):
        if row['DL_PRB UTILIZATION'] > 80:
            utilization_to_offload = row['DL_PRB UTILIZATION'] - 80

            # Determine offload order based on serving DLARFCN
            if row['DLARFCN'] == 40290:
                offload_targets = [40092]
            else:
                offload_targets = [40290]

            offload_details = []
            for target_dlarfcn in offload_targets:
                # Check for valid CellNAME_Lookup before creating mask
                if not isinstance(row['CellNAME_Lookup'], str) or '_' not in row['CellNAME_Lookup']:
                    continue
                cell_prefix = row['CellNAME_Lookup'].split('_')[0]
                
                # Find difference row
                mask = (
                    (sector_merged_df['Spot_Area_Num'] == row['Spot_Area_Num']) &
                    # Match rows with same cell identifier
                    (sector_merged_df['CellNAME_Lookup'] == row['CellNAME_Lookup']) &
                    (sector_merged_df['serving_band_flag'] == 0) &
                    (sector_merged_df['DLARFCN'] == target_dlarfcn)
                )
                diff_rows = sector_merged_df[mask]
                if not diff_rows.empty:
                    for diff_idx, diff_row in diff_rows.iterrows():
                        if pd.isna(diff_row['DL_PRB UTILIZATION']):
                            continue
                        can_receive = max(0, 80 - diff_row['DL_PRB UTILIZATION'])
                        offload_amt = min(utilization_to_offload, can_receive)
                        if offload_amt > 0:
                            # Update the difference row's DL_PRB UTILIZATION
                            sector_merged_df.at[diff_idx, 'DL_PRB UTILIZATION'] = round(diff_row['DL_PRB UTILIZATION'] + offload_amt, 2)
                            # Add recommendation to the difference row
                            sector_merged_df.at[diff_idx, 'Recommendation'] = f"Received {round(offload_amt,2)}% from DLARFCN {row['DLARFCN']}. New DL_PRB UTILIZATION: {round(diff_row['DL_PRB UTILIZATION'] + offload_amt,2)}%"
                            # Track offload
                            offload_details.append(f"{round(offload_amt,2)}% to DLARFCN {target_dlarfcn}")
                            utilization_to_offload -= offload_amt
                        if utilization_to_offload <= 0:
                            break
                if utilization_to_offload <= 0:
                    break
            if offload_details:
                new_util = 80 if utilization_to_offload <= 0 else row['DL_PRB UTILIZATION'] - utilization_to_offload
                sector_merged_df.at[idx, 'Recommendation'] = f"Offloaded {', '.join(offload_details)}. New DL_PRB UTILIZATION: {round(new_util,2)}%"
                # Update the serving row's DL_PRB UTILIZATION
                sector_merged_df.at[idx, 'DL_PRB UTILIZATION'] = round(new_util, 2)
            else:
                # Find available FDD DLARFCNs for this sector
                fdd_mask = (
                    (sector_merged_df['Spot_Area_Num'] == row['Spot_Area_Num']) &
                    (sector_merged_df['CellNAME_Lookup'] == row['CellNAME_Lookup']) &
                    (sector_merged_df['serving_band_flag'] == 0) &
                    (sector_merged_df['Cell FDD TDD Indication'] == 'FDD') &
                    (sector_merged_df['DLARFCN'].isin([525, 1760, 3725]))
                )
                fdd_cells = sector_merged_df[fdd_mask]
                
                if fdd_cells.empty:
                    sector_merged_df.at[idx, 'Recommendation'] = "No offload possible: No FDD bands available for handover"
                else:
                    available_fdds = fdd_cells['DLARFCN'].tolist()
                    # Sort in the preferred order and remove decimals
                    sorted_fdds = sorted(available_fdds, key=lambda x: [525, 1760, 3725].index(int(x)) if int(x) in [525, 1760, 3725] else 999)
                    formatted_fdds = [str(int(x)) for x in sorted_fdds]
                    sector_merged_df.at[idx, 'Recommendation'] = f"No offload possible: Consider handover to available FDD DLARFCNs: {', '.join(formatted_fdds)}"
        else:
            sector_merged_df.at[idx, 'Recommendation'] = "DL_PRB UTILIZATION is below 80"
    


    # FDD logic for DLARFCN 525, 1760, and 3725
    elif (
        row['serving_band_flag'] == 1 and
        row['Cell FDD TDD Indication'] == 'FDD' and
        row['DLARFCN'] in [525, 1760, 3725] and
        not pd.isna(row['DL_PRB UTILIZATION'])
    ):
        if row['DL_PRB UTILIZATION'] > 80:
            utilization_to_offload = row['DL_PRB UTILIZATION'] - 80
            serving_util = row['DL_PRB UTILIZATION']
            offload_details = []
            
            # First step: Find TDD bands and offload to them regardless of utilization difference
            tdd_offload_targets = [40290, 40092]
            found_tdd = False
            for target_dlarfcn in tdd_offload_targets:
                # Check for valid CellNAME_Lookup before creating mask
                if not isinstance(row['CellNAME_Lookup'], str):
                    continue
                
                # Find matching TDD cells
                mask_target = (
                    (sector_merged_df['Spot_Area_Num'] == row['Spot_Area_Num']) &
                    (sector_merged_df['CellNAME_Lookup'] == row['CellNAME_Lookup']) &
                    (sector_merged_df['serving_band_flag'] == 0) &
                    (sector_merged_df['DLARFCN'] == target_dlarfcn) &
                    (sector_merged_df['Cell FDD TDD Indication'] == 'TDD')
                )
                
                target_rows = sector_merged_df[mask_target]
                if not target_rows.empty:
                    found_tdd = True
                    for t_idx, t_row in target_rows.iterrows():
                        if pd.isna(t_row['DL_PRB UTILIZATION']):
                            continue
                        
                        # For TDD: Offload until target reaches 80% regardless of utilization difference
                        can_receive = max(0, 80 - t_row['DL_PRB UTILIZATION'])
                        if can_receive > 0:
                            offload_amt = min(utilization_to_offload, can_receive)
                            if offload_amt > 0:
                                new_diff_util = round(t_row['DL_PRB UTILIZATION'] + offload_amt, 2)
                                sector_merged_df.at[t_idx, 'DL_PRB UTILIZATION'] = new_diff_util
                                sector_merged_df.at[t_idx, 'Recommendation'] = f"Received {round(offload_amt,2)}% from DLARFCN {row['DLARFCN']} (TDD priority). New DL_PRB UTILIZATION: {new_diff_util}%"
                                offload_details.append(f"{round(offload_amt,2)}% to TDD DLARFCN {target_dlarfcn} (new util: {new_diff_util}%)")
                                utilization_to_offload -= offload_amt
                                serving_util -= offload_amt
                        
                        if utilization_to_offload <= 0:
                            break
                
                if utilization_to_offload <= 0:
                    break
            
            # If no TDD bands are present or couldn't offload everything, use band-specific strategies
            if utilization_to_offload > 0:
                # Different offload strategies based on current band
                if row['DLARFCN'] == 1760:
                    # For 1760: First try 525, then 3725
                    fdd_priority_targets = [525, 3725]
                elif row['DLARFCN'] == 3725:
                    # For 3725: First try 525, then 1760
                    fdd_priority_targets = [525, 1760]
                elif row['DLARFCN'] == 525:
                    # For 525: First try 1760, then 3725
                    fdd_priority_targets = [1760, 3725]
                else:
                    fdd_priority_targets = []
                
                # Process each target band according to the priority order
                for target_dlarfcn in fdd_priority_targets:
                    mask_target = (
                        (sector_merged_df['Spot_Area_Num'] == row['Spot_Area_Num']) &
                        (sector_merged_df['CellNAME_Lookup'] == row['CellNAME_Lookup']) &
                        (sector_merged_df['serving_band_flag'] == 0) &
                        (sector_merged_df['DLARFCN'] == target_dlarfcn)
                    )
                    
                    target_rows = sector_merged_df[mask_target]
                    for t_idx, t_row in target_rows.iterrows():
                        if pd.isna(t_row['DL_PRB UTILIZATION']):
                            continue
                        
                        # Check for 40% difference
                        diff = serving_util - t_row['DL_PRB UTILIZATION']
                        if diff > 40:
                            # Set target utilization based on the band
                            if target_dlarfcn == 1760:
                                max_target_util = 70  # 1760 can be filled up to 70%
                            elif target_dlarfcn == 3725:
                                max_target_util = 60  # 3725 can be filled up to 60%
                            else:
                                max_target_util = 80  # 525 can be filled up to 80%
                                
                            can_receive = max(0, max_target_util - t_row['DL_PRB UTILIZATION'])
                            if can_receive > 0:
                                offload_amt = min(utilization_to_offload, can_receive)
                                if offload_amt > 0:
                                    new_diff_util = round(t_row['DL_PRB UTILIZATION'] + offload_amt, 2)
                                    sector_merged_df.at[t_idx, 'DL_PRB UTILIZATION'] = new_diff_util
                                    sector_merged_df.at[t_idx, 'Recommendation'] = f"Received {round(offload_amt,2)}% from DLARFCN {row['DLARFCN']} (Band {target_dlarfcn} priority). New DL_PRB UTILIZATION: {new_diff_util}%"
                                    offload_details.append(f"{round(offload_amt,2)}% to DLARFCN {target_dlarfcn} (new util: {new_diff_util}%)")
                                    utilization_to_offload -= offload_amt
                                    serving_util -= offload_amt
                        
                        if utilization_to_offload <= 0:
                            break
                    
                    if utilization_to_offload <= 0:
                        break
            
            # Update the serving row and recommendation
            if offload_details:
                new_serving_util = round(serving_util, 2)
                sector_merged_df.at[idx, 'Recommendation'] = f"Offloaded {'; '.join(offload_details)}. Serving new DL_PRB UTILIZATION: {new_serving_util}%"
                sector_merged_df.at[idx, 'DL_PRB UTILIZATION'] = new_serving_util
            else:
                # Check if there are TDD offload target cells present
                tdd_target_present_mask = (
                    (sector_merged_df['Spot_Area_Num'] == row['Spot_Area_Num']) &
                    (sector_merged_df['CellNAME_Lookup'] == row['CellNAME_Lookup']) &
                    (sector_merged_df['serving_band_flag'] == 0) &
                    (sector_merged_df['DLARFCN'].isin([40290, 40092]))
                )
                tdd_target_cells_present = not sector_merged_df[tdd_target_present_mask].empty
                
                if tdd_target_cells_present:
                     # No offload possible, and TDD targets are present -> TDD likely highly utilized
                     sector_merged_df.at[idx, 'Recommendation'] = "No offloading possible to other FDD bands (TDD utilized above 80%)"
                else:
                    # No offload possible, and no TDD targets present
                    sector_merged_df.at[idx, 'Recommendation'] = "No offloading possible to other FDD bands (no TDD band present)"
        else:
            sector_merged_df.at[idx, 'Recommendation'] = "DL_PRB UTILIZATION is below 80"

# After all updates, rename DL_PRB UTILIZATION to DL_PRB UTILIZATION_new
sector_merged_df = sector_merged_df.rename(columns={'DL_PRB UTILIZATION': 'DL_PRB UTILIZATION_new'})

# Sort so that for each Spot_Area_Num, serving_band_flag==1 is first
sector_merged_df = sector_merged_df.sort_values(['Spot_Area_Num', 'serving_band_flag'], ascending=[True, False])

# Remove rows where DLARFCN is empty
sector_merged_df = sector_merged_df.dropna(subset=['DLARFCN'])

# Save the sector and band analysis results with the specified column order
ordered_cols_flag = ordered_cols + ['serving_band_flag', 'DL_PRB UTILIZATION_old', 'DL_PRB UTILIZATION_new', 'Utilization_difference', 'Recommendation']
ordered_cols_sector = [col for col in ordered_cols_flag if col in sector_merged_df.columns]
sector_merged_df = sector_merged_df[ordered_cols_sector]
sector_output_path = os.path.join(script_dir, 'Highload_Problem_SectorBands_Detailed_3.csv')
sector_merged_df.to_csv(sector_output_path, index=False)

print(f"Detailed sector and band information saved to: {sector_output_path}")

