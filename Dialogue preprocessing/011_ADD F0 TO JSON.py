# Add F0 contour to json files

import pandas as pd
import json
from datetime import datetime, timedelta


def add_f0_to_json(json_file, f0_file):
    # Read json file
    with open(json_file) as f:
        session_data = json.load(f)
    
    # Timestamp: 1.93, Formatted time: 00:01, F0: 131.57 Hz
    # Load f0 file as dataframe where we take the time from the second column and F0 from the third column
    f0_df = pd.read_csv(f0_file, sep=',', header=None, names=['Timestamp-seconds', 'Time', 'f0'])

    # Add a column with the time as a datetime object in the format '%H:%M:%S,%f'
    for index, row in f0_df.iterrows():
            # Extract the time from Formatted time: 00:01
            F0_time = row['Time'][16:]
            
            # Parse the time string into a time object
            # Need to do it in several steps to first fill in the missing hours
            minutes, seconds = map(int, F0_time.split(':'))
            F0_time_datetime = datetime(1900, 1, 1, minute=minutes, second=seconds)
            # this returns a string
            F0_time_formatted = F0_time_datetime.strftime('%H:%M:%S,%f')[:-3]
            # so then I need to convert it to datetime again
            F0_time_dt = datetime.strptime(F0_time_formatted, '%H:%M:%S,%f')
            # Add the time as a datetime object to the dataframe
            f0_df.at[index, 'Time-datetime'] = F0_time_dt

    # Turn the 'Time-datetime' and 'f0' columns into a list of tuples
    f0_with_timestamps = list(zip(f0_df['Timestamp-seconds'], f0_df['Time-datetime'], f0_df['f0']))

    # Iterate over the json file and add the f0 value to the json file
    turn_counter = 0 #To print progress
    for turn_obj in session_data['SESSION']['TURNS']:
        # Extract turn start and end times
        start_time = datetime.strptime(turn_obj['TURN']['TIME']['START'], '%H:%M:%S,%f')
        end_time = datetime.strptime(turn_obj['TURN']['TIME']['END'], '%H:%M:%S,%f')

        # List of F0 values for the current turn
        F0forturn_list = []

        # Iterate through the f0 dataframe and find the f0 value for the current turn
        for seconds,timestamp,f0 in f0_with_timestamps:
            # Compare with turn times
            if timestamp >= start_time and timestamp <= end_time and ('nan' not in f0):
                string_to_append = f'{seconds} {timestamp.strftime("%H:%M:%S,%f")[:-3]} {f0}'
                F0forturn_list.append(string_to_append)

        # After going through all F0, add list to current turn before going to next turn
        turn_obj['TURN']['F0'] = F0forturn_list

        turn_counter += 1
        print(f'Added F0 for turn {turn_counter}')

    # Write to json file
    final_filename_json = json_file[:-5] + '_f0.json'
    with open(final_filename_json, 'w') as f:
        json.dump(session_data, f, indent=4)

if __name__ == "__main__":
	json_file = 'session_data.json' # Replace with your json file path
	f0_file = 'f0_data.csv' # Replace with your f0 file path
	add_f0_to_json(json_file, f0_file)