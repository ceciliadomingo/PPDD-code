import pandas as pd
from datetime import datetime #, timedelta

def convert_rui_keylog_to_relative(merged_csv):
	# Read the Excel file
	df = pd.read_csv(merged_csv)
	# Starting point timestamp
	starting_point = datetime.strptime('11:43:46:000', '%H:%M:%S:%f') #ACHTUNG ACHTUNG ACHTUNG ACHTUNG ACHTUNG ACHTUNG ACHTUNG ACHTUNG

	# Retrieve the absolute timestamp values from the "Time" column
	absolute_timestamps_column_list = df['Time'].tolist()


	# Convert absolute timestamps to relative timestamps
	relative_timestamps = []
	for absolute_timestamp in absolute_timestamps_column_list:

		
		# Parse the absolute timestamp string
		timestamp = datetime.strptime(str(absolute_timestamp), '%Y-%m-%dT%H:%M:%S:%f')

		# Calculate the difference
		difference = timestamp - starting_point

		# Extract hours, minutes, seconds, and milliseconds
		hours = difference.seconds // 3600
		minutes = (difference.seconds // 60) % 60
		seconds = difference.seconds % 60
		milliseconds = difference.microseconds // 1000

		# Format the relative timestamp string
		relative_timestamp = '{:02d}:{:02d}:{:02d}:{:03d}'.format(hours, minutes, seconds, milliseconds)
		
		relative_timestamps.append(relative_timestamp)


	# Add the relative timestamps as a new column in the DataFrame
	df['Relative Timestamp'] = relative_timestamps

	# Write the updated DataFrame to a new Excel file
	output_filepath = merged_csv.replace('.csv', '-relative.xls')
	df.to_excel(output_filepath, index=False, engine='xlsxwriter')

if __name__ == "__main__":

	merged_csv = 'path/to/your/merged.csv'  # Replace with your actual merged CSV file path
	convert_rui_keylog_to_relative(merged_csv)