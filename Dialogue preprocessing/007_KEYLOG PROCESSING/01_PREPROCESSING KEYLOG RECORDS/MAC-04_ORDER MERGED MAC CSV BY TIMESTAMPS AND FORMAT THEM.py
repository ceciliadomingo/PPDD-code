import pandas as pd
from datetime import datetime
import numpy as np
import os

def sort_mac_csv(mac_csv):
	# Read the CSV file
	csv_file_path = mac_csv
	df = pd.read_csv(csv_file_path)

	# Convert the timestamp column to datetime format
	df['Time'] = pd.to_datetime(df['Time']).dt.floor('ms')


	# Sort the DataFrame based on the timestamp column
	# Get the indices that would sort the 'Time' column
	sort_indices = np.argsort(df['Time'])
	# Use the indices to rearrange the rows of the entire DataFrame
	df_sorted = df.iloc[sort_indices]


	#Save the new df to a csv file
	output_filepath = os.path.splitext(mac_csv)[0] + '_sorted.csv'
	df_sorted.to_csv(output_filepath, index=False)

if __name__ == "__main__":
	mac_csv = 'path/to/your/mac_csv_file.csv'  # Replace with the actual path to your MAC CSV file
	sort_mac_csv(mac_csv)