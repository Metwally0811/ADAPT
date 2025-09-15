import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_percentage_error, accuracy_score
import os

def calculate_rsrp_percentage(df):
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
        
        # Retrieve the first row's calculated statistics
        avg_val = first_row["avg_diff_rsrp"]
        harmonic_val = first_row["harmonic_mean_difference"]
        geometric_val = first_row["geometric_mean_difference"]
        median_val = first_row["Median"]
        percentile_75_val = first_row["75th Percentile"]

        # Calculate percentage of rows resolved according to each measure
        avg_diff_resolved = (group["Needed_RSRP_Increase"] <= avg_val).sum() / len(group) * 100
        harmonic_mean_resolved = (group["Needed_RSRP_Increase"] <= harmonic_val).sum() / len(group) * 100
        geometric_mean_resolved = (group["Needed_RSRP_Increase"] <= geometric_val).sum() / len(group) * 100
        median_resolved = (group["Needed_RSRP_Increase"] <= median_val).sum() / len(group) * 100
        percentile_75_resolved = (group["Needed_RSRP_Increase"] <= percentile_75_val).sum() / len(group) * 100

        insights = (
            # f"By using the Average Difference value, {avg_diff_resolved:.2f}% of the area is resolved.\n"
            # f"By using the Harmonic Mean Difference value, {harmonic_mean_resolved:.2f}% of the area is resolved.\n"
            # f"By using the Geometric Mean Difference value, {geometric_mean_resolved:.2f}% of the area is resolved.\n"
            # f"By using the Median value, {median_resolved:.2f}% of the area is resolved.\n"
            f"By using the 75th Percentile value, {percentile_75_resolved:.2f}% of the area is resolved."
        )

        # Assign insights only to the first row of the group
        df.loc[group.index[0], "Insights"] = insights

    return df

current_dir = os.path.dirname(os.path.abspath(__file__))
training_data_path = os.path.join(current_dir, "Bad_Coverage_Training_Data_ML.csv")
Bad_Coverage_training_df = pd.read_csv(training_data_path)
Bad_Coverage_training_df = Bad_Coverage_training_df.sort_values(by=["Spot_Area_Num","Time"])

# Split dataset into features and target
X = Bad_Coverage_training_df.drop(columns=["PDSCH Phy Throughput (kbps)", "Bad Throughput", "Spot_Area_Num",
                                           "Neighbor Cell RSRP (dBm): N1", "Neighbor Cell RSRP (dBm): N2",
                                           "Neighbor Cell RSRP (dBm): N3","Time","Latitude","Longitude"])
y = Bad_Coverage_training_df["Bad Throughput"]

# Train RandomForestClassifier
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.4, random_state=42)
rf = RandomForestClassifier()
rf.fit(X_train, y_train)

# Make predictions
y_pred = rf.predict(X_test)
Bad_Coverage_training_df["Predicted Throughput (Mbps)"] = rf.predict(X)

# Evaluate the model
mse = mean_squared_error(y_test, y_pred)

accuracy = accuracy_score(y_test, y_pred)

print("Mean Squared Error:", mse)
print("Accuracy:", accuracy)

Bad_Coverage_training_df["Updated_RSRP"] = np.nan

# Iterate through each sample
for index, row in Bad_Coverage_training_df.iterrows():
    if row["Bad Throughput"] == 0:
        continue

    # Extract feature columns as a DataFrame with correct format
    feature_cols = X.columns  # Ensure the correct feature set is used
    current_features = row[feature_cols].copy().to_frame().T

    while True:
        # Increase the RSRP value
        current_features["Serving Cell RSRP (dBm)"] += 1
        
        # Predict the Bad Throughput status
        prediction = rf.predict(current_features)[0]

        if prediction == 0:
            # If the prediction is 0, store the updated RSRP and break
            Bad_Coverage_training_df.at[index, "Updated_RSRP"] = current_features["Serving Cell RSRP (dBm)"].values[0]
            break

# Add Needed_RSRP_Increase column (difference between Updated_RSRP and Serving Cell RSRP)
Bad_Coverage_training_df["Needed_RSRP_Increase"] = (
    Bad_Coverage_training_df["Updated_RSRP"] - Bad_Coverage_training_df["Serving Cell RSRP (dBm)"]
)

# Save the updated dataframe
Bad_Coverage_training_df.to_csv(os.path.join(current_dir, 'Suggestion_BadCoverage.csv'), index=False)

# Filter out rows where Spot_Area_Num is 0
Bad_Coverage_training_df = Bad_Coverage_training_df[Bad_Coverage_training_df["Spot_Area_Num"] != 0]

# Initialize columns with None
Bad_Coverage_training_df["avg_diff_rsrp"] = None
Bad_Coverage_training_df["harmonic_mean_difference"] = None
Bad_Coverage_training_df["geometric_mean_difference"] = None
Bad_Coverage_training_df["Median"] = None
Bad_Coverage_training_df["75th Percentile"] = None


# Assign calculated values only to the first occurrence of each Spot_Area_Num
for spot_area_num, group in Bad_Coverage_training_df.groupby("Spot_Area_Num"):
    values = group["Needed_RSRP_Increase"]

    avg_diff = values.mean()
    harmonic_mean = len(values) / np.sum(1 / values)
    geometric_mean = np.exp(np.log(values).mean())
    min_max_mean = ((values - values.min()) / (values.max() - values.min())).sum()
    median = values.median()
    percentile_75 = values.quantile(0.75)

    first_index = group.index[0]

    Bad_Coverage_training_df.at[first_index, "avg_diff_rsrp"] = avg_diff
    Bad_Coverage_training_df.at[first_index, "harmonic_mean_difference"] = harmonic_mean
    Bad_Coverage_training_df.at[first_index, "geometric_mean_difference"] = geometric_mean
    Bad_Coverage_training_df.at[first_index, "Median"] = median
    Bad_Coverage_training_df.at[first_index, "75th Percentile"] = percentile_75


# Uncomment this line to enable Insights generation
Bad_Coverage_training_df = calculate_rsrp_percentage(Bad_Coverage_training_df)


# Initialize column
Bad_Coverage_training_df["RSRP Range increase per Area"] = None

# Assign 75th percentile - max range only to the first row of each group
for spot_area_num, group in Bad_Coverage_training_df.groupby("Spot_Area_Num"):
    percentile_75 = group["Needed_RSRP_Increase"].quantile(0.75)
    max_val = group["Needed_RSRP_Increase"].max()
    range_string = f"{percentile_75:.2f} - {max_val:.2f}"
    Bad_Coverage_training_df.loc[group.index[0], "RSRP Range increase per Area"] = range_string


Bad_Coverage_training_df = Bad_Coverage_training_df.drop(columns=["avg_diff_rsrp", "harmonic_mean_difference", "geometric_mean_difference", "Median", "75th Percentile"])


# Save the filtered dataset
Bad_Coverage_training_df.to_csv(os.path.join(current_dir, 'Suggestion_BadCoverage_onlybad.csv'), index=False)



print("Updated RSRP values, Needed_RSRP_Increase, and avg_diff_rsrp have been saved.")
