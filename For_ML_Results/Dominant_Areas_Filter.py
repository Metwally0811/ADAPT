import os
import pandas as pd

def extract_and_save_problem_areas(df):
    """
    Extracts rows for each problem type and saves them into separate CSV files
    inside their respective solution folders, using relative paths.

    Parameters:
        df (pd.DataFrame): The input dataframe.
    """
    # Get base path of the current script
    base_dir = os.path.dirname(os.path.abspath(__file__))
   

    # Map each problem to its output subfolder and CSV filename
    problem_outputs = {
        "Bad Coverage": ("Bad_Coverage_Solution", "Bad_Coverage_Areas_ML.csv"),
        "High Load": ("Highload_Solution", "Highload_Areas_ML.csv"),
        "Inter-Frequency Handover": ("Inter-Handover_Solution", "Inter_HandOver_Areas_ML.csv"),
        "Intra-Frequency Handover": ("Intra-Handover_Solution", "Intra_HandOver_Areas_ML.csv"),
        "Overlapping": ("Overlapping_Solution", "Overlapping_Areas_ML.csv"),
        "Overshooting": ("Overshooting_Solution", "Overshooting_Areas_ML.csv")
    }


    for problem, (folder_name, filename) in problem_outputs.items():
        # Identify problem rows
        problem_indices = df[df["Dominant Problem"] == problem].index
        rows_to_keep = set()

        for idx in problem_indices:
            spot_area_num = df.loc[idx, "Spot_Area_Num"]
            rows_to_keep.add(idx)
            subsequent_rows = df[(df.index > idx) & (df["Spot_Area_Num"] == spot_area_num)].index
            rows_to_keep.update(subsequent_rows)

        problem_df = df.loc[sorted(rows_to_keep)].copy()

        # Build the relative path to the correct solution folder
        output_folder = os.path.join(base_dir,  folder_name)
        os.makedirs(output_folder, exist_ok=True)  # Ensure the folder exists

        # Save to CSV
        output_path = os.path.join(output_folder, filename)
        problem_df.to_csv(output_path, index=False)
        print(f"[✔] Saved {filename} to {output_folder}")

# Load your dataset
# df = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..","..", "Problem_Detection","By Machine Learning", "Problem_Areas_ML_Output.csv"))

# Get base path of the current script
base_dir = os.path.dirname(os.path.abspath(__file__))
print(base_dir)

df = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)),"Problem_Areas_ML_Output.csv"))


# Extract and save each problem into the right folder
extract_and_save_problem_areas(df)
