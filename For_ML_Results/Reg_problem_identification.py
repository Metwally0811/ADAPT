import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import os
import math

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

# Define the minimum and maximum number of samples for a valid group
MIN_NUM_SAMPLES = 7
MAX_NUM_SAMPLES = 15
# Define the target values and thresholds
MAX_DISTANCE = 500
MAX_UE_TRANSMIT_POWER = 20
TARGET_THROUGHPUT = 10000

# Define relative paths based on current script location
current_dir = os.path.dirname(os.path.abspath(__file__))  # This gets the path to the current .py file
base_path = os.path.dirname(current_dir)  # This gets the parent directory (gui_full)

# Load datasets using relative paths
data_path = os.path.join(base_path, "Uploaded_Test.csv")
enodeb_path = os.path.join(base_path, "Uploaded_Cell.xlsx")

# Load datasets using relative paths
training_data_path = os.path.join(current_dir, "Uploaded_Train.csv")
# loading the dataset to a Pandas DataFrame
training_dataset = pd.read_csv(training_data_path, low_memory=False)

# Load the datasets
data = pd.read_csv(data_path, low_memory=False)
data_Enode = pd.read_excel(enodeb_path)

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


# Filter rows for Spots.csv where Spot_Area_Num = 0
data_problem_free = data[data['Spot_Area_Num'] == 0].reset_index(drop=True)
# Save the updated file
data_problem_free = data_problem_free[data_problem_free['PDSCH Phy Throughput (kbps)'] >= TARGET_THROUGHPUT]
data_problem_free.to_csv(os.path.join(current_dir, 'Problem_Free_Areas_ML_Output.csv'), index=False)

# Filter rows for Spots.csv where Spot_Area_Num > 0
data = data[data['Spot_Area_Num'] > 0].reset_index(drop=True)	

#removed_columns = data["Latitude","Longitude","PDSCH Phy Throughput (kbps)", "Bad Throughput"]
x = training_dataset[
    ['Serving Cell RSRP (dBm)', 'Serving Cell Identity', 'Serving Cell DL EARFCN',
     'Neighbor Cell RSRP (dBm): N1', 'Neighbor Cell Identity: N1', 'Neighbor Cell DL EARFCN: N1',
     'Neighbor Cell RSRP (dBm): N2', 'Neighbor Cell Identity: N2', 'Neighbor Cell DL EARFCN: N2',
     'Neighbor Cell RSRP (dBm): N3', 'Neighbor Cell Identity: N3', 'Neighbor Cell DL EARFCN: N3',
     'Neighbor Cell RSRP (dBm): N4', 'Neighbor Cell Identity: N4', 'Neighbor Cell DL EARFCN: N4',
     'Serving Cell RSRQ (dB)', 'Number of PDSCH Resource Blocks',
     'Serving Cell RS SINR (dB)', 'UE TX Power - PUSCH (dBm) Carrier 1']
]
Y = training_dataset['Problem Number'].astype(int)  # Ensure it's an integer

# Train the model on the entire dataset
model = RandomForestClassifier(random_state=3)
model.fit(x,Y)

new_data1 =  data

# Ensure new data has same features as training data
new_data = new_data1[x.columns]  # Selecting only relevant columns

# Retrieve Spot_Area_Num and Time for test data
spot_area_test2 = new_data1.loc[new_data.index, ['Spot_Area_Num', 'Time']]

# Making predictions on new data
new_predictions = model.predict(new_data)

# Convert predictions to DataFrame with 'Problem number' as column name
new_pred_df = pd.DataFrame(new_predictions, columns=['Problem number'], index=new_data.index)
# We are specifying the column name directly since Y is a Series
# Mapping numbers back to problem names
problem_name_mapping = {
    1: "Bad Coverage",
    2: "Intra-Frequency Handover",
    3: "Inter-Frequency Handover",
    4: "Overshooting",
    5: "Overlapping",
    6: "High Load",
    7: "Other Issues"
}

# Add Problem_Name column based on Problem number
new_pred_df['Problem_Name'] = new_pred_df['Problem number'].map(problem_name_mapping)

# Merging predictions with original new dataset
predicted_new_data = pd.concat([new_data, new_pred_df,spot_area_test2], axis=1)

# Sorting dataset by Spot_Area_Num
predicted_new_data = predicted_new_data.sort_values(by=['Spot_Area_Num'])
# Calculate dominant problem name and its percentage for each Spot_Area_Num
dominants = (
    predicted_new_data.groupby('Spot_Area_Num')['Problem_Name']
    .value_counts(normalize=True)
    .groupby(level=0)
    .head(1)
    .reset_index(name='percentage')
)

# Create the Dominant column text (e.g., "Bad Coverage (72.73%)")
dominants['Dominant'] = dominants['Problem_Name'] + " (" + (dominants['percentage'] * 100).round(2).astype(str) + "%)"
dominants['Dominant Problem'] = dominants['Problem_Name'] 

# Merge Dominant info back to the predicted_new_data
predicted_new_data = predicted_new_data.merge(dominants[['Spot_Area_Num', 'Dominant']], on='Spot_Area_Num', how='left')
predicted_new_data = predicted_new_data.merge(dominants[['Spot_Area_Num', 'Dominant Problem']], on='Spot_Area_Num', how='left')

# Keep Dominant only in the first occurrence of each Spot_Area_Num, set others to NaN
predicted_new_data['Dominant'] = predicted_new_data.groupby('Spot_Area_Num')['Dominant'].transform(
    lambda group: [group.iloc[0]] + [np.nan] * (len(group) - 1)
)
predicted_new_data['Dominant Problem'] = predicted_new_data.groupby('Spot_Area_Num')['Dominant Problem'].transform(
    lambda group: [group.iloc[0]] + [np.nan] * (len(group) - 1)
)
# Evaluating accuracy of new predictions (if true labels are available in the file)
if 'Bad Coverage' in new_data.columns:
    new_data_accuracy = accuracy_score(new_data[Y.columns], new_predictions) # Assuming ground truth is available for evaluation
    print('New Data Accuracy:', new_data_accuracy)

# Define the columns to move to the beginning
priority_columns = ["Time","Latitude", "Longitude", "PDSCH Phy Throughput (kbps)", "Cell Identity (eNB Part)"]

# Add back these columns from new_data1 if they exist
for col in priority_columns + ["Bad Throughput"]:  # Also adding 'Bad Throughput' later
    if col in new_data1.columns:
        predicted_new_data[col] = new_data1[col].values

# Now reorder the columns: first the priority columns, then the rest
remaining_columns = [col for col in predicted_new_data.columns if col not in priority_columns]
ordered_columns = priority_columns + remaining_columns

# Apply the new order
predicted_new_data = predicted_new_data[ordered_columns]

# Saving predictions to CSV
output_file = "Problem_Areas_ML_Output.csv"
predicted_new_data.to_csv(os.path.join(current_dir, output_file), index=False)

print(f"Predictions saved to {output_file}")
