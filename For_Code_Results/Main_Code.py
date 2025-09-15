import subprocess
import os

# Change working directory to the folder containing the scripts
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Get the current directory of Main_ML.py
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to Input_filtering_Area_Division.py
# script_path = os.path.join(current_dir, "Input_filtering_Area_Division.py")

# Run the script using subprocess
# subprocess.run(["python", script_path], check=True)

subprocess.run(["python", "Input_filtering_Area_Division.py"], check=True)
subprocess.run(["python", "Data_Analyzing.py"], check=True)

print("All scripts executed successfully. Final output saved in 'Analyzed_Areas_Code_Output.csv'.")
