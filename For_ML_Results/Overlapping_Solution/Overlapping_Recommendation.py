import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_percentage_error, accuracy_score
from scipy.stats import hmean
import os

def calculate_sinr_percentage(df):
    """
    Add an 'Insights' column to the input dataframe.
    The insights are written only at the first occurrence of each Spot_Area_Num,
    using the first row's statistics for comparison.
    
    Parameters:
        df (pd.DataFrame): The input dataframe containing Spot_Area_Num, Needed_SINR_Increase,
                           avg_diff_SINR, harmonic_mean_difference, geometric_mean_difference,
                           Median, and 75th Percentile.
        
    Returns:
        pd.DataFrame: The input dataframe with an additional 'Insights' column.
    """
    df = df.copy()
    df["Insights"] = None  # Initialize column

    for spot_area_num, group in df.groupby("Spot_Area_Num"):
        first_row = group.iloc[0]
        
        # Retrieve the first row’s calculated statistics
        avg_val = first_row["avg_diff_SINR"]
        harmonic_val = first_row["harmonic_mean_difference"]
        geometric_val = first_row["geometric_mean_difference"]
        median_val = first_row["Median"]
        percentile_75_val = first_row["75th Percentile"]

        # Calculate percentage of rows resolved according to each measure
        avg_diff_resolved = (group["Needed_SINR_Increase"] <= avg_val).sum() / len(group) * 100
        harmonic_mean_resolved = (group["Needed_SINR_Increase"] <= harmonic_val).sum() / len(group) * 100
        geometric_mean_resolved = (group["Needed_SINR_Increase"] <= geometric_val).sum() / len(group) * 100
        median_resolved = (group["Needed_SINR_Increase"] <= median_val).sum() / len(group) * 100
        percentile_75_resolved = (group["Needed_SINR_Increase"] <= percentile_75_val).sum() / len(group) * 100

        insights = (
            f"By using the Average Difference value, {avg_diff_resolved:.2f}% of the area is resolved.\n"
            f"By using the Harmonic Mean Difference value, {harmonic_mean_resolved:.2f}% of the area is resolved.\n"
            f"By using the Geometric Mean Difference value, {geometric_mean_resolved:.2f}% of the area is resolved.\n"
            f"By using the Median value, {median_resolved:.2f}% of the area is resolved.\n"
            f"By using the 75th Percentile value, {percentile_75_resolved:.2f}% of the area is resolved."
        )

        # Assign insights only to the first row of the group
        df.loc[group.index[0], "Insights"] = insights

    return df



current_dir = os.path.dirname(os.path.abspath(__file__))
training_data_path = os.path.join(current_dir, "Overlapping_Training_Data_ML.csv")
Overlapping_training_df = pd.read_csv(training_data_path)
Overlapping_training_df = Overlapping_training_df.sort_values(by=["Spot_Area_Num","Time"])

#Overlapping_training_df["harmonic_mean_diff"] = Overlapping_training_df.apply(calculate_harmonic_mean, axis=1)

# Split dataset into features and target
X = Overlapping_training_df.drop(columns=["PDSCH Phy Throughput (kbps)", "Bad Throughput", "Spot_Area_Num","Time","Latitude","Longitude"])
y = Overlapping_training_df["Bad Throughput"]

# Train RandomForestClassifier
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.4, random_state=42)
rf = RandomForestClassifier()
rf.fit(X_train, y_train)

# Make predictions
y_pred = rf.predict(X_test)
Overlapping_training_df["Predicted Throughput (Mbps)"] = rf.predict(X)

# Evaluate the model
mse = mean_squared_error(y_test, y_pred)
accuracy = accuracy_score(y_test, y_pred)

# Initialize Updated_SINR column with NaN values
Overlapping_training_df["Updated_SINR"] = np.nan

# Iterate through each sample
for index, row in Overlapping_training_df.iterrows():
    if row["Bad Throughput"] == 0:
        continue

    # Extract feature columns as a DataFrame
    feature_cols = X.columns
    current_features = row[feature_cols].copy().to_frame().T

    original_sinr = row["Serving Cell RS SINR (dB)"]
    original_rsrp = row["Serving Cell RSRP (dBm)"]
    
    sinr_increase = 0
    prediction = 1

    # Step 1: Try increasing SINR by up to 7
    while sinr_increase < 20:
        current_features["Serving Cell RS SINR (dB)"] += 1
        sinr_increase += 1
        prediction = rf.predict(current_features)[0]
        if prediction == 0:
            break

    if prediction == 0:
        # Only SINR increase was needed
        Overlapping_training_df.at[index, "Updated_SINR"] = current_features["Serving Cell RS SINR (dB)"].values[0]
    else:
        # Revert SINR and start increasing RSRP instead
        current_features["Serving Cell RS SINR (dB)"] = original_sinr
        current_features["Serving Cell RSRP (dBm)"] = original_rsrp

        while prediction == 1:
            current_features["Serving Cell RSRP (dBm)"] += 1
            prediction = rf.predict(current_features)[0]

        Overlapping_training_df.at[index, "Updated_RSRP"] = current_features["Serving Cell RSRP (dBm)"].values[0]

# Add Needed_SINR_Increase column where applicable
Overlapping_training_df["Needed_SINR_Increase"] = (
    Overlapping_training_df["Updated_SINR"] - Overlapping_training_df["Serving Cell RS SINR (dB)"]
)

# Add Needed_RSRP_Increase column where applicable
if "Updated_RSRP" in Overlapping_training_df.columns:
    Overlapping_training_df["Needed_RSRP_Increase"] = (
        Overlapping_training_df["Updated_RSRP"] - Overlapping_training_df["Serving Cell RSRP (dBm)"]
    )

# Save the updated dataframe
Overlapping_training_df.to_csv(os.path.join(current_dir, 'Suggestion_Overlapping.csv'), index=False)


# Filter out rows where Spot_Area_Num is 0
Overlapping_training_df = Overlapping_training_df[Overlapping_training_df["Spot_Area_Num"] != 0]

# Initialize columns with None
Overlapping_training_df["avg_diff_SINR"] = None
Overlapping_training_df["harmonic_mean_difference"] = None
Overlapping_training_df["geometric_mean_difference"] = None
Overlapping_training_df["Median"] = None
Overlapping_training_df["75th Percentile"] = None

# Populate only the first row of each Spot_Area_Num group
for spot_area_num, group in Overlapping_training_df.groupby("Spot_Area_Num"):
    avg_diff = group["Needed_SINR_Increase"].mean()
    harmonic_mean = len(group) / np.sum(1 / group["Needed_SINR_Increase"])
    geometric_mean = np.exp(np.log(group["Needed_SINR_Increase"]).mean())
    median = group["Needed_SINR_Increase"].median()
    percentile_75 = group["Needed_SINR_Increase"].quantile(0.75)

    idx = group.index[0]  # First index of the group

    Overlapping_training_df.at[idx, "avg_diff_SINR"] = avg_diff
    Overlapping_training_df.at[idx, "harmonic_mean_difference"] = harmonic_mean
    Overlapping_training_df.at[idx, "geometric_mean_difference"] = geometric_mean
    Overlapping_training_df.at[idx, "Median"] = median
    Overlapping_training_df.at[idx, "75th Percentile"] = percentile_75


#Overlapping_training_df = calculate_sinr_percentage(Overlapping_training_df)

# Initialize column
Overlapping_training_df["SINR Range increase per Area"] = None

# Assign 75th percentile - max range only to the first row of each group
for spot_area_num, group in Overlapping_training_df.groupby("Spot_Area_Num"):
    percentile_75 = group["Needed_SINR_Increase"].quantile(0.75)
    max_val = group["Needed_SINR_Increase"].max()
    range_string = f"{percentile_75:.2f} - {max_val:.2f}"
    Overlapping_training_df.loc[group.index[0], "SINR Range increase per Area"] = range_string


Overlapping_training_df = Overlapping_training_df.drop(columns=["avg_diff_SINR", "harmonic_mean_difference", "geometric_mean_difference", "Median", "75th Percentile"])

# Save the filtered dataset
Overlapping_training_df.to_csv(os.path.join(current_dir, 'Suggestion_Overlapping_onlybad.csv'), index=False)



print("Updated SINR values, Needed_SINR_Increase, and avg_diff_SINR have been saved.")
