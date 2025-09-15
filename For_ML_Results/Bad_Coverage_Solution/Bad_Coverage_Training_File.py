import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Get current script directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Build relative paths to the two input CSV files
bad_coverage_path = os.path.join(current_dir, "Bad_Coverage_Areas_ML.csv")
problem_free_path = os.path.join(current_dir, "..", "Problem_Free_Areas_ML_Output.csv")

# Load the CSV files using the relative paths
Bad_Coverage_df = pd.read_csv(bad_coverage_path)
Problem_Free_df = pd.read_csv(problem_free_path)

# Check if 'Problem_Name' column exists, if not, create it with value "Bad Coverage" for bad coverage areas
if 'Problem_Name' not in Bad_Coverage_df.columns:
    Bad_Coverage_df['Problem_Name'] = "Bad Coverage"  # Assuming all rows in Bad_Coverage_df are bad coverage areas

# Drop unnecessary columns
columns_to_keep = ["Time", "Latitude", "Longitude", "Spot_Area_Num", "PDSCH Phy Throughput (kbps)",
                   "Serving Cell RSRP (dBm)", "Bad Throughput", "Neighbor Cell RSRP (dBm): N1",
                   "Neighbor Cell RSRP (dBm): N2", "Neighbor Cell RSRP (dBm): N3", "Problem_Name"]

# Keep only columns that exist in the dataframe
Bad_Coverage_df = Bad_Coverage_df[[col for col in columns_to_keep if col in Bad_Coverage_df.columns]]
Problem_Free_df = Problem_Free_df[[col for col in columns_to_keep if col in Problem_Free_df.columns and col != "Problem_Name"]]

# Keep only rows where Problem_Name is "Bad Coverage" if the column exists
if 'Problem_Name' in Bad_Coverage_df.columns:
    Bad_Coverage_df = Bad_Coverage_df[Bad_Coverage_df["Problem_Name"] == "Bad Coverage"]

# Map "Bad Coverage" to 1 and anything else to 0
if 'Problem_Name' in Bad_Coverage_df.columns:
    Bad_Coverage_df["Problem_Name"] = Bad_Coverage_df["Problem_Name"].apply(lambda x: 1 if x == "Bad Coverage" else 0)

# Define columns to be used
throughput_col = 'PDSCH Phy Throughput (kbps)'
rsrp_col = 'Serving Cell RSRP (dBm)'

# Highlighting outliers using IQR method
Q1_Bad_Coverage = Bad_Coverage_df[rsrp_col].quantile(0.25)
Q3_Bad_Coverage = Bad_Coverage_df[rsrp_col].quantile(0.75)
IQR_Bad_Coverage = Q3_Bad_Coverage - Q1_Bad_Coverage

# Define outliers as points beyond 1.5*IQR
lower_bound_Bad_Coverage = Q1_Bad_Coverage - 1.5 * IQR_Bad_Coverage
upper_bound_Bad_Coverage = Q3_Bad_Coverage + 1.5 * IQR_Bad_Coverage
Bad_Coverage_Without_Outliers_df = Bad_Coverage_df[(Bad_Coverage_df[rsrp_col] > lower_bound_Bad_Coverage) & (Bad_Coverage_df[rsrp_col] < upper_bound_Bad_Coverage)]

# Highlighting outliers using IQR method
Q1_Problem_Free = Problem_Free_df[rsrp_col].quantile(0.25)
Q3_Problem_Free = Problem_Free_df[rsrp_col].quantile(0.75)
IQR_Problem_Free = Q3_Problem_Free - Q1_Problem_Free

# Define outliers as points beyond 1.5*IQR
lower_bound_PF = Q1_Problem_Free - 1 * IQR_Problem_Free
upper_bound_PF = Q3_Problem_Free + 1.5 * IQR_Problem_Free

Problem_Free_Without_Outlier_df = Problem_Free_df[(Problem_Free_df[rsrp_col] > lower_bound_PF) & (Problem_Free_df[rsrp_col] < upper_bound_PF)]

# Merge Problem_Free_df and Bad_Coverage_df while keeping column names only once
df_final = pd.concat([Problem_Free_Without_Outlier_df, Bad_Coverage_Without_Outliers_df], ignore_index=True).sort_values(by="Time")
# Reset the index after sorting
df_final = df_final.reset_index(drop=True)

# Save final merged training data
df_final.to_csv(os.path.join(current_dir, 'Bad_Coverage_Training_Data_ML.csv'), index=False)


