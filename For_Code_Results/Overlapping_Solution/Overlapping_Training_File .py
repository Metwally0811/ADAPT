import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
def add_matching_neighbor_earfcn(Overlapping_df):
    """
    Adds columns to Overlapping_df that store RSRP values of neighbors 
    that have the same EARFCN as "Serving Cell DL EARFCN" and checks if the
    "Serving Cell RSRP (dBm)" is within ±5 dBm of the neighbor's RSRP.
    Also calculates the absolute difference between "Serving Cell RSRP (dBm)" and the matched neighbor RSRP values.
    
    Parameters:
        Overlapping_df (pd.DataFrame): The input dataframe.
    
    Returns:
        pd.DataFrame: Updated dataframe with new columns.
    """
    # Initialize new columns with NaN
    for i in range(1, 5):
        Overlapping_df[f"OL_N{i}_RSRP"] = None
        Overlapping_df[f"OL_N{i}_RSRP_Diff"] = None
    
    # Iterate through each row to find matching neighbor EARFCN
    for index, row in Overlapping_df.iterrows():
        dl_earfcn = row["Serving Cell DL EARFCN"]
        serving_rsrp = row["Serving Cell RSRP (dBm)"]
        
        try:
            serving_cell_id = int(row['Serving Cell Identity'])  # Convert to int safely
        except (ValueError, TypeError):
            serving_cell_id = None  # Handle missing cell identity

        # Neighbor EARFCNs, RSRPs, and PCIs
        neighbor_earfcns = {f"N{i}": row[f"Neighbor Cell DL EARFCN: N{i}"] for i in range(1, 5)}
        neighbor_rsrps = {f"N{i}": row[f"Neighbor Cell RSRP (dBm): N{i}"] for i in range(1, 5)}
        neighbor_pci = {f"N{i}": row[f"Neighbor Cell Identity: N{i}"] for i in range(1, 5)}
        
        # Iterate through each neighbor and apply conditions
        for i in range(1, 5):
            neighbor = f"N{i}"
            
            # Check if EARFCN matches and cell IDs are different
            if neighbor_earfcns[neighbor] == dl_earfcn and serving_cell_id is not None and neighbor_pci[neighbor] != serving_cell_id:
                neighbor_rsrp = neighbor_rsrps[neighbor]
                
                # Check if the RSRP difference is within ±5 dBm
                if abs(serving_rsrp - neighbor_rsrp) <= 5:
                    Overlapping_df.at[index, f"OL_N{i}_RSRP"] = neighbor_rsrp
                    Overlapping_df.at[index, f"OL_N{i}_RSRP_Diff"] = abs(serving_rsrp - neighbor_rsrp)
    
    return Overlapping_df
def only_neighbors_with_same_earfcn(Overlapping_df):
    """
    Adds columns to Overlapping_df that store the RSRP values of neighbors 
    (N1 to N3) that have the same EARFCN as the serving cell.
    
    Parameters:
        Overlapping_df (pd.DataFrame): The input dataframe.
    
    Returns:
        pd.DataFrame: Updated dataframe with new columns.
    """
    # Initialize new columns
    for i in range(1, 4):
        Overlapping_df[f"N{i}_with_SameEARFCN_RSRP"] = None

    # Iterate through each row
    for index, row in Overlapping_df.iterrows():
        serving_earfcn = row.get("Serving Cell DL EARFCN")

        # Skip rows with missing serving EARFCN
        if pd.isnull(serving_earfcn):
            continue

        for i in range(1, 4):
            neighbor_earfcn = row.get(f"Neighbor Cell DL EARFCN: N{i}")
            neighbor_rsrp = row.get(f"Neighbor Cell RSRP (dBm): N{i}")

            if neighbor_earfcn == serving_earfcn:
                Overlapping_df.at[index, f"N{i}_with_SameEARFCN_RSRP"] = neighbor_rsrp

    return Overlapping_df



# Get current script directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Build relative paths to the two input CSV files
overlapping_path = os.path.join(current_dir, "Overlapping_Areas_Code.csv")
problem_free_path = os.path.join(current_dir, "..", "Problem_Free_Areas_Code_Output.csv")

# Load the CSV files using the relative paths
Overlapping_df = pd.read_csv(overlapping_path)
Problem_Free_df = pd.read_csv(problem_free_path)

# Drop unnecessary columns
Problem_Free_df = Problem_Free_df[["Time","Latitude","Longitude","Overlapping","Spot_Area_Num","PDSCH Phy Throughput (kbps)", "Serving Cell RS SINR (dB)","Serving Cell RSRP (dBm)","Bad Throughput","Neighbor Cell RSRP (dBm): N1", "Neighbor Cell RSRP (dBm): N2", "Neighbor Cell RSRP (dBm): N3","Neighbor Cell RSRP (dBm): N4","Serving Cell DL EARFCN", "Neighbor Cell DL EARFCN: N1", "Neighbor Cell DL EARFCN: N2", "Neighbor Cell DL EARFCN: N3","Neighbor Cell DL EARFCN: N4","Serving Cell Identity","Neighbor Cell Identity: N1","Neighbor Cell Identity: N2","Neighbor Cell Identity: N3","Neighbor Cell Identity: N4"]]
#remove rows that have nulls in the "Neighbor Cell RSRP (dBm): N1" Problem_Free_df
Problem_Free_df = Problem_Free_df.dropna(subset=["Neighbor Cell RSRP (dBm): N1"])
Problem_Free_df = only_neighbors_with_same_earfcn(Problem_Free_df)
Problem_Free_df["Neighbor Cell RSRP (dBm): N1"]= Problem_Free_df["N1_with_SameEARFCN_RSRP"]
Problem_Free_df["Neighbor Cell RSRP (dBm): N2"]= Problem_Free_df["N2_with_SameEARFCN_RSRP"]
Problem_Free_df["Neighbor Cell RSRP (dBm): N3"]= Problem_Free_df["N3_with_SameEARFCN_RSRP"]
# Drop rows with null in all "Neighbor Cell RSRP (dBm): N1", "Neighbor Cell RSRP (dBm): N2", "Neighbor Cell RSRP (dBm): N3" columns
Problem_Free_df = Problem_Free_df.dropna(
    subset=["Neighbor Cell RSRP (dBm): N1", "Neighbor Cell RSRP (dBm): N2", "Neighbor Cell RSRP (dBm): N3"],
    how='all'
)

Problem_Free_df = Problem_Free_df[["Time","Latitude","Longitude","Spot_Area_Num","PDSCH Phy Throughput (kbps)", "Serving Cell RS SINR (dB)","Serving Cell RSRP (dBm)","Bad Throughput","Neighbor Cell RSRP (dBm): N1", "Neighbor Cell RSRP (dBm): N2", "Neighbor Cell RSRP (dBm): N3"]]

Overlapping_df = Overlapping_df[["Time","Latitude","Longitude","Overlapping","Spot_Area_Num","PDSCH Phy Throughput (kbps)", "Serving Cell RS SINR (dB)","Bad Throughput","Serving Cell RSRP (dBm)","Neighbor Cell RSRP (dBm): N1", "Neighbor Cell RSRP (dBm): N2", "Neighbor Cell RSRP (dBm): N3","Neighbor Cell RSRP (dBm): N4","Serving Cell DL EARFCN", "Neighbor Cell DL EARFCN: N1", "Neighbor Cell DL EARFCN: N2", "Neighbor Cell DL EARFCN: N3","Neighbor Cell DL EARFCN: N4","Serving Cell Identity","Neighbor Cell Identity: N1","Neighbor Cell Identity: N2","Neighbor Cell Identity: N3","Neighbor Cell Identity: N4"]]
Overlapping_df = Overlapping_df[Overlapping_df["Overlapping"] != 0]
Overlapping_df = add_matching_neighbor_earfcn(Overlapping_df)
Overlapping_df["Neighbor Cell RSRP (dBm): N1"]= Overlapping_df["OL_N1_RSRP"]
Overlapping_df["Neighbor Cell RSRP (dBm): N2"]= Overlapping_df["OL_N2_RSRP"]
Overlapping_df["Neighbor Cell RSRP (dBm): N3"]= Overlapping_df["OL_N3_RSRP"]

Overlapping_df = Overlapping_df.dropna(
    subset=["Neighbor Cell RSRP (dBm): N1", "Neighbor Cell RSRP (dBm): N2", "Neighbor Cell RSRP (dBm): N3"],
    how='all'
)

Overlapping_df = Overlapping_df[["Time","Latitude","Longitude","Overlapping","Spot_Area_Num","PDSCH Phy Throughput (kbps)", "Serving Cell RS SINR (dB)","Serving Cell RSRP (dBm)","Bad Throughput","Neighbor Cell RSRP (dBm): N1", "Neighbor Cell RSRP (dBm): N2", "Neighbor Cell RSRP (dBm): N3"]]

# Define columns to be used
throughput_col = 'PDSCH Phy Throughput (kbps)'
sinr_col = 'Serving Cell RS SINR (dB)'
rsrp_col = 'Serving Cell RSRP (dBm)'


# Highlighting outliers using IQR method
Q1_Overlapping = Overlapping_df[sinr_col].quantile(0.25)
Q3_Overlapping = Overlapping_df[sinr_col].quantile(0.75)
IQR_Overlapping = Q3_Overlapping - Q1_Overlapping
# Define outliers as points beyond 1.5*IQR
lower_bound_Overlapping = Q1_Overlapping - 1.5 * IQR_Overlapping
upper_bound_Overlapping = Q3_Overlapping + 1.5 * IQR_Overlapping
Overlapping_Without_Outliers_df = Overlapping_df[(Overlapping_df[sinr_col] > lower_bound_Overlapping) & (Overlapping_df[sinr_col] < upper_bound_Overlapping)]


# Highlighting outliers using IQR method
Q1_Problem_Free_RSRP = Problem_Free_df[rsrp_col].quantile(0.25)
Q3_Problem_Free_RSRP = Problem_Free_df[rsrp_col].quantile(0.75)
IQR_Problem_Free_RSRP = Q3_Problem_Free_RSRP - Q1_Problem_Free_RSRP
# Define outliers as points beyond 1.5*IQR
lower_bound_Problem_Free_RSRP = Q1_Problem_Free_RSRP - 1 * IQR_Problem_Free_RSRP
upper_bound_Problem_Free_RSRP = Q3_Problem_Free_RSRP + 1.5 * IQR_Problem_Free_RSRP
Problem_Free_Without_RSRP_Outlier_df = Problem_Free_df[(Problem_Free_df[rsrp_col] > lower_bound_Problem_Free_RSRP) & (Problem_Free_df[rsrp_col] < upper_bound_Problem_Free_RSRP)]

# Highlighting outliers using IQR method
Q1_Problem_Free_SINR = Problem_Free_Without_RSRP_Outlier_df[sinr_col].quantile(0.25)
Q3_Problem_Free_SINR = Problem_Free_Without_RSRP_Outlier_df[sinr_col].quantile(0.75)
IQR_Problem_Free_SINR = Q3_Problem_Free_SINR - Q1_Problem_Free_SINR
# Define outliers as points beyond 1.5*IQR
lower_bound_Problem_Free_SINR = Q1_Problem_Free_SINR - 1 * IQR_Problem_Free_SINR
upper_bound_Problem_Free_SINR = Q3_Problem_Free_SINR + 1.5 * IQR_Problem_Free_SINR
Problem_Free_Without_RSRP_SINR_Outlier_df = Problem_Free_Without_RSRP_Outlier_df[(Problem_Free_Without_RSRP_Outlier_df[sinr_col] > lower_bound_Problem_Free_SINR) & (Problem_Free_Without_RSRP_Outlier_df[sinr_col] < upper_bound_Problem_Free_SINR)]


# Merge Problem_Free_df and Overlapping_df while keeping column names only once
df_final = pd.concat([Problem_Free_Without_RSRP_SINR_Outlier_df, Overlapping_Without_Outliers_df], ignore_index=True).sort_values(by="Time")
# Reset the index after sorting
df_final = df_final.reset_index(drop=True)

#df_final = df_final.drop(columns=["Time"])
df_final = df_final.drop(columns=["Overlapping"])

df_final.to_csv(os.path.join(current_dir, 'Overlapping_Training_Data.csv'), index=False)
