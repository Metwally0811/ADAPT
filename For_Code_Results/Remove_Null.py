import os
import pandas as pd

# Define relative paths based on current script location
current_dir = os.path.dirname(os.path.abspath(__file__))  # This gets the path to the current .py file
base_path = current_dir  # Since your data files are in the same folder as the script

# Load datasets using relative paths
data_path = os.path.join(base_path, "..", "Table_View_Data.csv")
# Load the datasets
data = pd.read_csv(data_path, low_memory=False)
data = data.dropna(axis=1, how='all') 
data['PDSCH Phy Throughput (kbps)'] = data['PDSCH Phy Throughput (kbps)'].ffill()
data = data.dropna(subset=['PDSCH Phy Throughput (kbps)'])
data = data.dropna(subset=['Serving Cell RSRP (dBm)'])

data.to_csv(os.path.join(current_dir,"..", 'Table_View_Data_Clean.csv'), index=False)
