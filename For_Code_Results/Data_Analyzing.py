import pandas as pd
import math
import os
from openpyxl.styles import PatternFill
import pandas as pd
import os
from math import radians, cos, sin, asin, sqrt
import numpy as np
from scipy.spatial import cKDTree

# Function to remove rows between HTTP End and HTTP Start
def filter_http_intervals(df):
    http_flag = 0  # Initialize flag
    filtered_data = []  # Store valid rows

    for _, row in df.iterrows():
        if row['HTTP End'] == 1:
            http_flag = 1  # Start flag when HTTP End is found

        if http_flag == 0:
            filtered_data.append(row)  # Keep row only if flag is 0

        if row['HTTP Start'] == 1:
            http_flag = 0  # Reset flag when HTTP Start is found

    return pd.DataFrame(filtered_data)
# Function to extract Latitude and Longitude for a given Cell Identity
def get_lat_lon(cell_id):
    match = data_Enode[data_Enode['eNodeB id'] == cell_id].head(1)
    if not match.empty:
        return match['Latitude'].values[0], match['Longitude'].values[0]
    return np.nan, np.nan
# Function to extract Cell Name based on PCI, DLARFCN, and eNodeB id
def get_cell_name(row):
    match = data_Enode[
        (data_Enode['PCI'] == row['Serving Cell Identity']) &
        (data_Enode['DLARFCN'] == row['Serving Cell DL EARFCN']) &
        (data_Enode['eNodeB id'] == row['Cell Identity (eNB Part)'])
    ]
    if not match.empty:
        return match['CellNAME'].values[0]  # Replace 'Cell Name' with exact column name if different
    return ""
# Function to get DL_PRB UTILIZATION from data_utilization based on Serving_Cell_Name
def get_PRB_Utilization(row):
    match = data_utilization[data_utilization['Cell Name'] == row['Serving_Cell_Name']]
    if not match.empty:
        return round(float(match['DL_PRB UTILIZATION'].values[0]), 2)
    return ""


# Function to assign Spot_Area_Num
def assign_spots_area_num(df):
    spot_area_num = 1
    count = 0
    prev_Time = None
    spot_area_nums = []

    # First pass: Assign groups based on Coverage and Time rules
    for index, row in df.iterrows():
        if row['Bad Throughput'] == 1:
            if prev_Time is None or count >= MAX_NUM_SAMPLES or (row['Time2'] - prev_Time > 4):
                spot_area_num += 1
                count = 0
            spot_area_nums.append(spot_area_num)
            prev_Time = row['Time2']
            count += 1
        else:
            spot_area_nums.append(0)

    # Second pass: Adjust rows with Coverage == 0 to belong to adjacent groups
    for i in range(1, len(spot_area_nums) - 1):
        if spot_area_nums[i] == 0:
            if spot_area_nums[i - 1] > 0 and spot_area_nums[i + 1] > 0 and spot_area_nums[i - 1] == spot_area_nums[i + 1]:
                count += 1

    df['Spot_Area_Num'] = spot_area_nums

    # Third pass: Invalidate groups with fewer than 7 rows
    group_sizes = df['Spot_Area_Num'].value_counts()
    invalid_groups = group_sizes[group_sizes < MIN_NUM_SAMPLES].index
    df['Spot_Area_Num'] = df['Spot_Area_Num'].apply(lambda x: 0 if x in invalid_groups else x)

    # Adjust Spot_Area_Num to ensure increments are by 1 only for valid groups
    unique_spots = df.loc[df['Spot_Area_Num'] > 0, 'Spot_Area_Num'].unique()
    spot_mapping = {old: new for new, old in enumerate(unique_spots, start=1)}
    df['Spot_Area_Num'] = df['Spot_Area_Num'].map(lambda x: spot_mapping.get(x, 0))

    return df
# Function to calculate the distance between sample and site
def Sample_Site_Distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points 
    on the Earth specified by their latitude and longitude.
    
    Parameters:
    lat1, lon1 - Latitude and Longitude of point 1 in decimal degrees
    lat2, lon2 - Latitude and Longitude of point 2 in decimal degrees
    
    Returns:
    Distance between the two points in meters.
    """
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Earth's radius in meters (mean radius)
    R = 6371000  
    distance = R * c  # Distance in meters
    
    return abs(distance)
# Function to check if the distance to the site is greater than MAX_DISTANCE and UE Transmit Power is greater than MAX_UE_TRANSMIT_POWER
def Distance_Power_Check(row):
    return 1 if row['PDSCH Phy Throughput (kbps)'] < TARGET_THROUGHPUT and row['Distance_To_Site'] > MAX_DISTANCE and row['UE TX Power - PUSCH (dBm) Carrier 1'] > MAX_UE_TRANSMIT_POWER else 0
# Haversine formula to compute distance between two lat/lon coordinates
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth's radius in km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1 
    dlon = lon2 - lon1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * R * asin(sqrt(a)) * 1000  # Convert to meters
# Calculate median distance between sites
def calculate_median_distance(df_input):
   

    # Filter and deduplicate dataframe
    selected_columns = ['Physical_Site_Code', 'Latitude', 'Longitude']
    df_selected = df_input[selected_columns]
    df_unique = df_selected.drop_duplicates(subset='Physical_Site_Code', keep='first').copy()

    # Prepare coordinates in radians
    coords_rad = np.radians(df_unique[['Latitude', 'Longitude']].values)
    tree = cKDTree(coords_rad)
    _, idx = tree.query(coords_rad, k=2)  # k=2 to skip self (first match)

    # Get closest site info
    closest_indices = idx[:, 1]
    closest_sites = df_unique.iloc[closest_indices]['Physical_Site_Code'].values
    distances = [
        haversine(lat1, lon1, lat2, lon2)
        for (lat1, lon1), (lat2, lon2) in zip(
            df_unique[['Latitude', 'Longitude']].values,
            df_unique.iloc[closest_indices][['Latitude', 'Longitude']].values
        )
    ]

    # Assign results safely
    df_unique.loc[:, 'Closest_Site_Code'] = closest_sites
    df_unique.loc[:, 'Distance_m'] = distances

    # Calculate median distance
    unique_distances = df_unique['Distance_m'].unique()
    median_distance = np.median(unique_distances)

    return median_distance
# Function to check if all neighbor RSRP values are below TARGET_RSRP
def bad_coverage(row):
    bad_throughput_condition = row['PDSCH Phy Throughput (kbps)'] < TARGET_THROUGHPUT
    neighbors = [
        row['Neighbor Cell RSRP (dBm): N1'], 
        row['Neighbor Cell RSRP (dBm): N2'], 
        row['Neighbor Cell RSRP (dBm): N3'],
        row['Neighbor Cell RSRP (dBm): N4']
    ]
    bad_serving_rsrp_condtion= row['Serving Cell RSRP (dBm)'] < TARGET_RSRP
    bad_neighbor_rsrp_condtion= all(val<TARGET_RSRP for val in neighbors)

    # Check if Serving Cell RSRP and all neighbors are below TARGET_RSRP
    if bad_throughput_condition and bad_serving_rsrp_condtion and (( bad_neighbor_rsrp_condtion) or ( bad_neighbor_rsrp_condtion==0 and row['Intra-Frequency Handover'] == 0 and row['Inter-Frequency Handover'] == 0)) :
        return 1
    return 0
# Function for intra-frequency handover
def intra_frequency_handover(row):
    bad_throughput_condition = row['PDSCH Phy Throughput (kbps)'] < TARGET_THROUGHPUT
    neighbors = [
        row['Neighbor Cell RSRP (dBm): N1'], 
        row['Neighbor Cell RSRP (dBm): N2'], 
        row['Neighbor Cell RSRP (dBm): N3'],
        row['Neighbor Cell RSRP (dBm): N4']
    ]
    bad_serving_rsrp_condtion= row['Serving Cell RSRP (dBm)'] < TARGET_RSRP
    bad_neighbor_rsrp_condtion= all(val<TARGET_RSRP for val in neighbors)

    serving_rsrp = row['Serving Cell RSRP (dBm)']
    distance_condition = row['Distance_Power_Check']


    intra_frequency_handover_condition = any([
        row['Neighbor Cell RSRP (dBm): N1'] > serving_rsrp + RSRP_NEIGHBOUR_DIFFERENCE and 
        row['Neighbor Cell DL EARFCN: N1'] == row['Serving Cell DL EARFCN'],
        
        row['Neighbor Cell RSRP (dBm): N2'] > serving_rsrp + RSRP_NEIGHBOUR_DIFFERENCE and 
        row['Neighbor Cell DL EARFCN: N2'] == row['Serving Cell DL EARFCN'],
        
        row['Neighbor Cell RSRP (dBm): N3'] > serving_rsrp + RSRP_NEIGHBOUR_DIFFERENCE and 
        row['Neighbor Cell DL EARFCN: N3'] == row['Serving Cell DL EARFCN'],

        row['Neighbor Cell RSRP (dBm): N4'] > serving_rsrp + RSRP_NEIGHBOUR_DIFFERENCE and 
        row['Neighbor Cell DL EARFCN: N4'] == row['Serving Cell DL EARFCN']
    ])
    
    return 1 if bad_throughput_condition and ((bad_serving_rsrp_condtion and bad_neighbor_rsrp_condtion==0 and  intra_frequency_handover_condition)or(bad_serving_rsrp_condtion==0 and distance_condition and intra_frequency_handover_condition)) else 0
# Function for inter-frequency handover
def inter_frequency_handover(row):
    bad_throughput_condition = row['PDSCH Phy Throughput (kbps)'] < TARGET_THROUGHPUT
    neighbors = [
        row['Neighbor Cell RSRP (dBm): N1'], 
        row['Neighbor Cell RSRP (dBm): N2'], 
        row['Neighbor Cell RSRP (dBm): N3'],
        row['Neighbor Cell RSRP (dBm): N4']
    ]
    bad_serving_rsrp_condtion= row['Serving Cell RSRP (dBm)'] < TARGET_RSRP
    bad_neighbor_rsrp_condtion= all(val<TARGET_RSRP for val in neighbors)
    intra_frequency_handover_condition = row['Intra-Frequency Handover']

    serving_rsrp = row['Serving Cell RSRP (dBm)']
    distance_condition = row['Distance_Power_Check']
    serving_rsrp_min= serving_rsrp<MIN_SERVING_RSRP
    inter_frequency_handover_condition = any([
        row['Neighbor Cell RSRP (dBm): N1'] > serving_rsrp + RSRP_NEIGHBOUR_DIFFERENCE and row['Neighbor Cell DL EARFCN: N1'] != row['Serving Cell DL EARFCN'],
        row['Neighbor Cell RSRP (dBm): N2'] > serving_rsrp + RSRP_NEIGHBOUR_DIFFERENCE and row['Neighbor Cell DL EARFCN: N2'] != row['Serving Cell DL EARFCN'],
        row['Neighbor Cell RSRP (dBm): N3'] > serving_rsrp + RSRP_NEIGHBOUR_DIFFERENCE and row['Neighbor Cell DL EARFCN: N3'] != row['Serving Cell DL EARFCN'],
        row['Neighbor Cell RSRP (dBm): N4'] > serving_rsrp + RSRP_NEIGHBOUR_DIFFERENCE and row['Neighbor Cell DL EARFCN: N4'] != row['Serving Cell DL EARFCN']
    ])
    return 1 if bad_throughput_condition and((bad_serving_rsrp_condtion and bad_neighbor_rsrp_condtion==0 and intra_frequency_handover_condition==0 and inter_frequency_handover_condition and serving_rsrp_min ) or (bad_serving_rsrp_condtion==0 and distance_condition and intra_frequency_handover_condition==0 and inter_frequency_handover_condition and serving_rsrp_min))  else 0
# Function for overshooting detection
def overshooting(row):
    bad_throughput_condition = row['PDSCH Phy Throughput (kbps)'] < TARGET_THROUGHPUT
    serving_rsrp_condtion= row['Serving Cell RSRP (dBm)'] > TARGET_RSRP

    return 1 if bad_throughput_condition and serving_rsrp_condtion and row['Distance_Power_Check'] == 1 and row['Intra-Frequency Handover'] == 0 and row['Inter-Frequency Handover'] == 0  else 0
# Function for overlapping detection
def overlapping(row):
    serving_rsrp = row['Serving Cell RSRP (dBm)']
    serving_earfcn = row['Serving Cell DL EARFCN']
    
    try:
        serving_cell_id = int(row['Serving Cell Identity'])  # Convert to int safely
    except (ValueError, TypeError):
        serving_cell_id = None  # Handle missing cell identity

    # Define neighbors while ignoring null values
    neighbors = []
    for i in range(1, 5):  # Iterate over N1 to N4
        rsrp = row.get(f'Neighbor Cell RSRP (dBm): N{i}')
        earfcn = row.get(f'Neighbor Cell DL EARFCN: N{i}')
        try:
            cell_id = int(row.get(f'Neighbor Cell Identity: N{i}'))
        except (ValueError, TypeError):
            cell_id = None  # Handle missing identity safely
        
        if pd.notna(rsrp) and pd.notna(earfcn) and cell_id is not None:
            neighbors.append((rsrp, earfcn, cell_id))

    overlapping_cells = set()  # Store overlapping cell identities
    overlap_count = 0  # Counter for overlapping cells

    for neighbor_rsrp, neighbor_earfcn, neighbor_id in neighbors:
        if abs(serving_rsrp - neighbor_rsrp) <= MAX_RSRP_OVERLAP_RANGE and neighbor_earfcn == serving_earfcn and neighbor_id != serving_cell_id :
            overlap_count += 1
            overlapping_cells.add(str(neighbor_id))  # Store cell identity as a string

    # Determine overlap condition
    overlapping_condition = overlap_count > 0
    rsrp_condition = any(neighbor_rsrp > TARGET_RSRP for neighbor_rsrp, _, _ in neighbors)
    serving_rsrp_condition = serving_rsrp > TARGET_RSRP

    # Overlapping detection logic
    overlap_detected = 1 if (
        row['PDSCH Phy Throughput (kbps)'] < TARGET_THROUGHPUT and 
        rsrp_condition and overlapping_condition and 
        row['Serving Cell RS SINR (dB)'] < MIN_SINR and 
        serving_rsrp_condition
    ) else 0

    # If overlap is detected, add the serving cell to the overlapping cells set
    if overlap_detected and serving_cell_id is not None:
        overlapping_cells.add(str(serving_cell_id))

    # Convert set of overlapping cell identities into a comma-separated string
    overlapping_cells_str = ", ".join(sorted(overlapping_cells)) if overlapping_cells else "None"

    return pd.Series([overlap_detected, overlap_count + 1, overlapping_cells_str])
# Function for highload detection
def highload(row):
    try:
        prb_util = float(row['PRB Utilization'])
    except (ValueError, TypeError):
        return 0  # If PRB is missing or not a number, we can't flag High Load

    return 1 if (
        row['PDSCH Phy Throughput (kbps)'] < TARGET_THROUGHPUT and
        row['Bad Coverage'] == 0 and
        row['Overlapping'] == 0 and
        row['Overshooting'] == 0 and
        row['Intra-Frequency Handover'] == 0 and
        row['Inter-Frequency Handover'] == 0 and
        row['Number of PDSCH Resource Blocks'] < MIN_PRB and
        prb_util > PRB_Utilization_Threshold
    ) else 0
# Function to get the top 3 problems in each Spot_Area_Num with percentage and determine the dominant problem
def get_top_problems(group):
    problem_columns = ['Bad Coverage', 'Intra-Frequency Handover', 'Inter-Frequency Handover', 
                       'Overshooting', 'Overlapping', 'High Load']
    
    # Count the occurrences of each issue
    issue_counts = group[problem_columns].sum()
    area_size = len(group)
    
    # Calculate percentage of each problem
    percentages = {problem: (issue_counts[problem] / area_size) * 100 for problem in problem_columns}
    
    # Filter problems with percentage > 20%
    filtered_problems = {problem: pct for problem, pct in percentages.items() if pct > 20}
    
    if filtered_problems:
        # Sort problems by percentage (descending) and get top 3
        sorted_problems = sorted(filtered_problems.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Create string representation for Area_Problems
        area_problem_str = ', '.join([f"{problem}: {round(pct, 2)}%" for problem, pct in sorted_problems])
        

    else:
        area_problem_str = "Other Issues "


    group = group.copy()
    group['Area_Problems'] = ""


    if not group.empty:
        group.loc[group.index[0], 'Area_Problems'] = str(area_problem_str)


    return group
# Get the dominant problem for each Spot_Area_Num
def Dominant_Problem(df):
    # This will store the results only for the first row of each group
    dominant_results = {}

    def has_three_consecutive_ones(series):
        return any(series.rolling(window=3).sum() == 3)

    def extract_dominant_problem(group):
        row = group.iloc[0]
        problems_str = row['Area_Problems']

        if problems_str == "Other Issues ":
            return "Other Issues"

        try:
            problems = [item.split(": ") for item in problems_str.split(", ")]
            parsed = [(p[0], float(p[1].replace('%', ''))) for p in problems]
        except Exception:
            return " "

        if len(parsed) == 1:
            return parsed[0][0]

        def resolve_pair(p1, p2, group):
            diff = p1[1] - p2[1]
            if diff > 50:
                return p1[0]
            else:
                top1, top2 = p1[0], p2[0]

                if "Intra-Frequency Handover" in (top1, top2):
                    if has_three_consecutive_ones(group['Intra-Frequency Handover']):
                        return "Intra-Frequency Handover"
                if "Inter-Frequency Handover" in (top1, top2):
                    if has_three_consecutive_ones(group['Inter-Frequency Handover']):
                        return "Inter-Frequency Handover"

                analysis_map = {
                    ("Bad Coverage", "Overshooting"): analyze_badcoverage_overshooting,
                    ("Bad Coverage", "Overlapping"): analyze_badcoverage_overlapping,
                    ("Bad Coverage", "High Load"): analyze_badcoverage_highload,
                    ("Overshooting", "Overlapping"): analyze_overshooting_overlapping,
                    ("Overshooting", "High Load"): analyze_overshooting_highload,
                    ("Overlapping", "High Load"): analyze_overlapping_highload,
                }
                key_pair = (top1, top2)
                reverse_pair = (top2, top1)

                if key_pair in analysis_map:
                    result_group = analysis_map[key_pair](group)
                elif reverse_pair in analysis_map:
                    result_group = analysis_map[reverse_pair](group)
                else:
                    return top1

                return result_group['Dominant Problem'].iloc[0]

        if len(parsed) == 2:
            return resolve_pair(parsed[0], parsed[1], group)

        if len(parsed) >= 3:
            first = parsed[0]
            second = parsed[1]
            third = parsed[2]

            if abs(second[1] - third[1]) < 1e-6:
                winner_second_third = resolve_pair(second, third, group)
                winner_percent = next((v for k, v in parsed if k == winner_second_third), 0)
                new_second = (winner_second_third, winner_percent)
                return resolve_pair(first, new_second, group)
            else:
                return resolve_pair(first, second, group)

        return "No Problem Found"

    for area_num, group in df.groupby("Spot_Area_Num"):
        dominant = extract_dominant_problem(group)
        index = group.index[0]
        dominant_results[index] = dominant

    df['Dominant Problem'] = ""

    for idx, value in dominant_results.items():
        df.at[idx, 'Dominant Problem'] = value

    return df
# Analyze between Bad Coverage and Overshooting
def analyze_badcoverage_overshooting(group):
    rsrp_rank_sum = group['rsrp_rank'].sum()
    dist_rank_sum = group['dist_rank'].sum()

    if rsrp_rank_sum > dist_rank_sum:
        dominant = "Bad Coverage"
    elif dist_rank_sum > rsrp_rank_sum:
        dominant = "Overshooting"
    else:
        area_problems_str = group['Area_Problems'].iloc[0]
        try:
            problems = dict((p.split(': ')[0], float(p.split(': ')[1].replace('%', ''))) for p in area_problems_str.split(', '))
            if problems.get("Bad Coverage", 0) >= problems.get("Overshooting", 0):
                dominant = "Bad Coverage"
            else:
                dominant = "Overshooting"
        except:
            dominant = "Bad Coverage"

    group['Dominant Problem'] = dominant
    return group
# Analyze between Bad Coverage and Overlapping
def analyze_badcoverage_overlapping(group):
    rsrp_rank_sum = group['rsrp_rank'].sum()
    sinr_rank_sum = group['sinr_rank'].sum()

    if rsrp_rank_sum > sinr_rank_sum:
        dominant = "Bad Coverage"
    elif sinr_rank_sum > rsrp_rank_sum:
        dominant = "Overlapping"
    else:
        area_problems_str = group['Area_Problems'].iloc[0]
        try:
            problems = dict((p.split(': ')[0], float(p.split(': ')[1].replace('%', ''))) for p in area_problems_str.split(', '))
            if problems.get("Bad Coverage", 0) >= problems.get("Overlapping", 0):
                dominant = "Bad Coverage"
            else:
                dominant = "Overlapping"
        except:
            dominant = "Bad Coverage"

    group['Dominant Problem'] = dominant
    return group
# Analyze between Bad Coverage and Highload
def analyze_badcoverage_highload(group):
    rsrp_rank_sum = group['rsrp_rank'].sum()
    prbs_rank_sum = group['prbs_rank'].sum()

    if rsrp_rank_sum > prbs_rank_sum:
        dominant = "Bad Coverage"
    elif prbs_rank_sum > rsrp_rank_sum:
        dominant = "High Load"
    else:
        area_problems_str = group['Area_Problems'].iloc[0]
        try:
            problems = dict((p.split(': ')[0], float(p.split(': ')[1].replace('%', ''))) for p in area_problems_str.split(', '))
            if problems.get("Bad Coverage", 0) >= problems.get("High Load", 0):
                dominant = "Bad Coverage"
            else:
                dominant = "High Load"
        except:
            dominant = "Bad Coverage"

    group['Dominant Problem'] = dominant
    return group
# Analyze between Overshooting and Overlapping
def analyze_overshooting_overlapping(group):
    dist_rank_sum = group['dist_rank'].sum()
    sinr_rank_sum = group['sinr_rank'].sum()

    if sinr_rank_sum > dist_rank_sum:
        dominant = "Overlapping"
    elif dist_rank_sum > sinr_rank_sum:
        dominant = "Overshooting"
    else:
        area_problems_str = group['Area_Problems'].iloc[0]
        try:
            problems = dict((p.split(': ')[0], float(p.split(': ')[1].replace('%', ''))) for p in area_problems_str.split(', '))
            if problems.get("Overlapping", 0) >= problems.get("Overshooting", 0):
                dominant = "Overlapping"
            else:
                dominant = "Overshooting"
        except:
            dominant = "Overlapping"

    group['Dominant Problem'] = dominant
    return group
# Analyze between Overshooting and Highload
def analyze_overshooting_highload(group):
    prbs_rank_sum = group['prbs_rank'].sum()
    dist_rank_sum = group['dist_rank'].sum()

    if prbs_rank_sum > dist_rank_sum:
        dominant = "High Load"
    elif dist_rank_sum > prbs_rank_sum:
        dominant = "Overshooting"
    else:
        area_problems_str = group['Area_Problems'].iloc[0]
        try:
            problems = dict((p.split(': ')[0], float(p.split(': ')[1].replace('%', ''))) for p in area_problems_str.split(', '))
            if problems.get("Overshooting", 0) >= problems.get("High Load", 0):
                dominant = "Overshooting"
            else:
                dominant = "High Load"
        except:
            dominant = "Overshooting"

    group['Dominant Problem'] = dominant
    return group
# Analyze between Overlapping and Highload
def analyze_overlapping_highload(group):
    sinr_rank_sum = group['sinr_rank'].sum()
    prbs_rank_sum = group['prbs_rank'].sum()

    if sinr_rank_sum > prbs_rank_sum:
        dominant = "Overlapping"
    elif prbs_rank_sum > sinr_rank_sum:
        dominant = "High Load"
    else:
        area_problems_str = group['Area_Problems'].iloc[0]
        try:
            problems = dict((p.split(': ')[0], float(p.split(': ')[1].replace('%', ''))) for p in area_problems_str.split(', '))
            if problems.get("Overlapping", 0) >= problems.get("High Load", 0):
                dominant = "Overlapping"
            else:
                dominant = "High Load"
        except:
            dominant = "Overlapping"

    group['Dominant Problem'] = dominant
    return group
# Ranking Addition Function with Check Conditions
def add_ranks(df, dist, MIN_SINR, TARGET_RSRP):
    df['rsrp_rank'] = None
    df['sinr_rank'] = None
    df['prbs_rank'] = None
    df['dist_rank'] = None

    for area_num, group in df.groupby('Spot_Area_Num'):
        top_probs = group['Area_Problems'].iloc[0].split(', ')
        top_3_probs = [p.split(':')[0] for p in top_probs[:3]]

        if 'Bad Coverage' in top_3_probs:
            rsrp_filtered = df[df['Serving Cell RSRP (dBm)'] < TARGET_RSRP]['Serving Cell RSRP (dBm)']
            rsrp_quantiles = [rsrp_filtered.quantile(q/5) for q in range(1, 6)]
            if not rsrp_filtered.empty:
                def rank_rsrp(x):
                    if x < rsrp_quantiles[0]:
                        return 5
                    elif x < rsrp_quantiles[1]:
                        return 4
                    elif x < rsrp_quantiles[2]:
                        return 3
                    elif x < rsrp_quantiles[3]:
                        return 2
                    elif x < rsrp_quantiles[4]:
                        return 1
                    else:
                        return 0

                mask = (group['Bad Coverage'] == 1)
                df.loc[group.index[mask], 'rsrp_rank'] = group.loc[mask, 'Serving Cell RSRP (dBm)'].apply(rank_rsrp)

        if 'Overlapping' in top_3_probs:
            sinr_filtered = df[df['Serving Cell RS SINR (dB)'] < MIN_SINR]['Serving Cell RS SINR (dB)']
            sinr_quantiles = [sinr_filtered.quantile(q/5) for q in range(1, 6)]
            if not sinr_filtered.empty:
                def rank_sinr(x):
                    if x < sinr_quantiles[0]:
                        return 5
                    elif x < sinr_quantiles[1]:
                        return 4
                    elif x < sinr_quantiles[2]:
                        return 3
                    elif x < sinr_quantiles[3]:
                        return 2
                    elif x < sinr_quantiles[4]:
                        return 1
                    else:
                        return 0

                mask = (group['Overlapping'] == 1)
                df.loc[group.index[mask], 'sinr_rank'] = group.loc[mask, 'Serving Cell RS SINR (dB)'].apply(rank_sinr)

        if 'High Load' in top_3_probs:
            mask = (group['High Load'] == 1)
            df.loc[group.index[mask], 'prbs_rank'] = group.loc[mask, 'Number of PDSCH Resource Blocks'].apply(
                lambda x: 0 if x > 30 else 1 if 25 < x <= 30 else 2 if 20 < x <= 25 else 3 if 15 < x <= 20 else 4 if 10 < x <= 15 else 5)

        if 'Overshooting' in top_3_probs:
            mask = (group['Overshooting'] == 1)
            df.loc[group.index[mask], 'dist_rank'] = group.loc[mask, 'Distance_To_Site'].apply(
                lambda x: 0 if x < dist*2 else 1 if dist*2 < x <= dist*3 else 2 if dist*3 < x <= dist*4 else 3 if dist*4 < x <= dist*5 else 4 if dist*5 < x <= dist*6 else 5)

    return df


# Define the minimum and maximum number of samples for a valid group
MIN_NUM_SAMPLES = 7
MAX_NUM_SAMPLES = 15
# Define the target values and thresholds
TARGET_THROUGHPUT = 10000
MAX_DISTANCE = 500
MAX_UE_TRANSMIT_POWER = 20
TARGET_RSRP = -100
RSRP_NEIGHBOUR_DIFFERENCE = 6
MIN_SERVING_RSRP = -116
MIN_RSRQ = -18
MIN_SINR = 10
MIN_PRB = 30
MAX_RSRP_OVERLAP_RANGE = 5
PRB_Utilization_Threshold= 80

# Define relative paths based on current script location
current_dir = os.path.dirname(os.path.abspath(__file__))  # This gets the path to the current .py file
base_path = current_dir  # Since your data files are in the same folder as the script

# Load datasets using relative paths
data_path = os.path.join(base_path, "..", "Uploaded_Test.csv")
enodeb_path = os.path.join(base_path, "..", "Uploaded_Cell.xlsx")
uploaded_utilization_path = os.path.join(base_path, "..", "Uploaded_Utilization.xlsx")
default_utilization_path = os.path.join(base_path,"..", "Nasr_City_PRB_Utilization.xlsx")

# Load the datasets
data = pd.read_csv(data_path, low_memory=False)
data_Enode = pd.read_excel(enodeb_path)
if os.path.exists(uploaded_utilization_path):
    data_utilization = pd.read_excel(uploaded_utilization_path)
    print(f"Using uploaded RB Utilization file: {uploaded_utilization_path}")
elif os.path.exists(default_utilization_path):
    data_utilization = pd.read_excel(default_utilization_path)
    print(f"Using default RB Utilization file: {default_utilization_path}")
else:
    data_utilization = pd.DataFrame() # Create empty DataFrame if neither file exists
    print("Warning: Neither uploaded nor default RB Utilization file found.")

# Drop the initial column if it contains only null values
data = data.dropna(axis=1, how='all') 

# Fill forward missing values in 'Cell Identity (eNB Part)' and 'Cell Identity (Cell Part)' columns, as they dont appear except in rows that conatin null throughput
data['Cell Identity (eNB Part)'] = data['Cell Identity (eNB Part)'].ffill()
data['Cell Identity (Cell Part)'] = data['Cell Identity (Cell Part)'].ffill()

# Convert HTTP Start & HTTP End to binary (1 if not NaN, 0 otherwise)
data['HTTP Start'] = data['HTTP Start'].notna().astype(int)
data['HTTP End'] = data['HTTP End'].notna().astype(int)
data['HTTP IP Service Access Failure'] = data['HTTP IP Service Access Failure'].notna().astype(int)

# Apply function to remove rows between HTTP End & HTTP Start
data = filter_http_intervals(data)

# Drop 'HTTP IP Service Access Failure' column
data = data.drop(columns=['HTTP Start'])
data = data.drop(columns=['HTTP End'])
data = data.drop(columns=['HTTP IP Service Access Failure'])

# Drop rows where 'PDSCH Phy Throughput (kbps)' is null
data = data.dropna(subset=['PDSCH Phy Throughput (kbps)'])

excluded_columns = [
    'Neighbor Cell RSRP (dBm): N1', 'Neighbor Cell Identity: N1', 'Neighbor Cell DL EARFCN: N1',
    'Neighbor Cell RSRP (dBm): N2', 'Neighbor Cell Identity: N2', 'Neighbor Cell DL EARFCN: N2',
    'Neighbor Cell RSRP (dBm): N3', 'Neighbor Cell Identity: N3', 'Neighbor Cell DL EARFCN: N3',
    'Neighbor Cell RSRP (dBm): N4', 'Neighbor Cell Identity: N4', 'Neighbor Cell DL EARFCN: N4'
]
data = data.dropna(subset=[col for col in data.columns if col not in excluded_columns])


 # Apply function to extract latitude and longitude for each row
data[['Latitude_EnodeB', 'Longitude_EnodeB']] = data['Cell Identity (eNB Part)'].apply(lambda x: pd.Series(get_lat_lon(x)))
data['Serving_Cell_Name'] = data.apply(get_cell_name, axis=1)
data['PRB Utilization'] = data.apply(get_PRB_Utilization, axis=1)


# Add the "Bad Throughput" column
data['Bad Throughput'] = (data['PDSCH Phy Throughput (kbps)'] < TARGET_THROUGHPUT).astype(int)

# Convert Time column to numeric format for processing
data['Time2'] = data['Time'].apply(lambda x: sum(int(float(t)) * 60 ** i for i, t in enumerate(reversed(x.split(':')))))
data = data.sort_values(by='Time2').reset_index(drop=True)

# Convert 'Date' and 'Time' to DateTime for proper sorting
data['Date'] = pd.to_datetime(data['Date'])
data['Time'] = pd.to_datetime(data['Time'], format='%H:%M:%S').dt.time

# Sort by Date then by Time
data = data.sort_values(by=['Date', 'Time'])

# Apply Spot_Area_Num logic
data = assign_spots_area_num(data)

# Remove the Time2 column as it is no longer needed
data = data.drop(columns=['Time2'])
# Compute Distance_To_Site using haversine formula

data['Distance_To_Site'] = data.apply(lambda row: Sample_Site_Distance(row['Latitude'], row['Longitude'], row['Latitude_EnodeB'], row['Longitude_EnodeB']), axis=1)
# Check if the distance to the site is greater than MAX_DISTANCE and UE Transmit Power is greater than MAX_UE_TRANSMIT_POWER
data['Distance_Power_Check'] = data.apply(Distance_Power_Check, axis=1).astype(int)


# Reorder columns to place 'Spot_Area_Num' before 'Bad Throughput'
columns = list(data.columns)
columns.insert(columns.index('Bad Throughput'), columns.pop(columns.index('Latitude_EnodeB')))
columns.insert(columns.index('Bad Throughput'), columns.pop(columns.index('Longitude_EnodeB')))
columns.insert(columns.index('Bad Throughput'), columns.pop(columns.index('Distance_To_Site')))
columns.insert(columns.index('Bad Throughput'), columns.pop(columns.index('Distance_Power_Check')))
columns.insert(columns.index('Bad Throughput'), columns.pop(columns.index('Spot_Area_Num')))
data = data[columns]

# Add the "Bad Coverage" column (1 if it's bad coverage, else 0)
data['Bad Coverage'] = ""

# Apply Intra-Frequency handover calculations
data['Intra-Frequency Handover'] = data.apply(intra_frequency_handover, axis=1).astype(int)

# Apply Inter-Frequency handover calculations
data['Inter-Frequency Handover'] = data.apply(inter_frequency_handover, axis=1).astype(int)

data['Bad Coverage'] = data.apply(bad_coverage, axis=1).astype(int)

# Apply overshooting calculation
data['Overshooting'] = data.apply(overshooting, axis=1).astype(int)
    
# Apply overlapping detection and count
data[['Overlapping', 'overlap_count', 'overlapping_cell_ids']] = data.apply(overlapping, axis=1)

# Apply HighLoad detection
data['High Load'] = data.apply(highload, axis=1).astype(int)

# Add a new column that sums the specified issue columns
data['Total Issues'] = data[['Bad Coverage', 'Intra-Frequency Handover', 'Inter-Frequency Handover', 'Overshooting', 'Overlapping', 'High Load']].sum(axis=1)

# Ensure 'Area_Problems' column exists and is of string type
data['Area_Problems'] = ""

data = data.drop(columns=['Serving_Cell_Name', 'PRB Utilization'])

# Apply the function to each Spot_Area_Num group
data = data.groupby('Spot_Area_Num', group_keys=False, as_index=False).apply(lambda g: get_top_problems(g), include_groups=True)


# Filter rows for Spots.csv where Spot_Area_Num > 0
data_problem = data[data['Spot_Area_Num'] > 0].reset_index(drop=True)
median_site_to_site_distance=calculate_median_distance(data_Enode)
data_problem = add_ranks(data_problem,median_site_to_site_distance,MIN_SINR,TARGET_RSRP)
data_problem = Dominant_Problem(data_problem)

# Filter rows for Spots.csv where Spot_Area_Num = 0
data_problem_free = data[data['Spot_Area_Num'] == 0].reset_index(drop=True)



# Save the updated file
data_problem.to_csv(os.path.join(current_dir, 'Problem_Areas_Code_Output.csv'), index=False)

# Save the updated file
data_problem_free = data_problem_free[data_problem_free['PDSCH Phy Throughput (kbps)'] >= TARGET_THROUGHPUT]
data_problem_free.to_csv(os.path.join(current_dir, 'Problem_Free_Areas_Code_Output.csv'), index=False)