import pandas as pd
from datetime import datetime #, timedelta

def convert_keylog_to_colon_format(input_csv):
	# Read the Excel file
	df = pd.read_csv(input_csv)

	# Retrieve the absolute timestamp values from the "Time" column
	absolute_timestamps_column_list = df['Time'].tolist()
	formatted_timestamps = []
	for absolute_timestamp in absolute_timestamps_column_list:

		# LINES NEEDED IF USED SCRIPT "CONVERT OUR KEYLOG TO CSV TO THEN CONVERT TO RELATIVE.py", as it adds a ' to the timestamp
		clean_timestamp = str(absolute_timestamp).lstrip("'")
		# Add a 'T' between the date and time
		# ValueError: time data '2024-03-05 19:32:41.562592' does not match format '%Y-%m-%dT%H:%M:%S:%f'
		clean_timestamp = clean_timestamp[:10] + 'T' + clean_timestamp[11:]
		# Remove trailing whitespace
		clean_timestamp= clean_timestamp.rstrip()
		#dt = datetime.fromisoformat(clean_timestamp)
	# formatted_timestamp = dt.strftime('%Y-%m-%dT%H:%M:%S:%f')
		absolute_timestamp = clean_timestamp


		# Parse the absolute timestamp string
		initial_format_string = '%Y-%m-%dT%H:%M:%S.%f'
		parsed_datetime = datetime.strptime(absolute_timestamp, initial_format_string)

		final_format_string = '%Y-%m-%dT%H:%M:%S:%f'
		converted_datetime_string = parsed_datetime.strftime(final_format_string)
		formatted_timestamps.append(converted_datetime_string)

	# Add the formatted timestamps as a new column in the DataFrame
	df['Time'] = formatted_timestamps

	# Write the updated DataFrame to a new Excel file
	output_filepath = input_csv.replace('.csv', '-withcolon.csv')
	df.to_csv(output_filepath, index=False)

if __name__ == "__main__":
	input_csv = 'path/to/your/keylog.csv'  # Replace with your input CSV file path
	convert_keylog_to_colon_format(input_csv)