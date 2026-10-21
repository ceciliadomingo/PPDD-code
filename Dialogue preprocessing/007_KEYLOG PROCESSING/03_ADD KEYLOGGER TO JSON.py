import json
from datetime import datetime
import numpy as np
import pandas as pd

#----------------------------------------------------------------------------------
# ADD SPEAKER LABELS AND MERGE CSVs AND ORDER CHRONOLOGICALLY
def merge_and_order_csvs(csv_a, csv_b, speaker_a_number, speaker_b_number):
    #Read the CSV files
    df_A = pd.read_csv(csv_a)
    df_B = pd.read_csv(csv_b)
    #Add speaker label to each keylogger entry
    df_A['Speaker'] = speaker_a_number
    df_B['Speaker'] = speaker_b_number
    #Merge the CSV files
    df_merged = pd.concat([df_A, df_B])
    #Iterate through df_merged and convert the timestamp column to datetime format
    datetime_list = []
    for index, row in df_merged.iterrows():
        time_string = row['Time'].strip() # Remove leading/trailing whitespace
        time_dt = datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%S:%f')
        datetime_list.append(time_dt)
    df_merged['Time_dt'] = datetime_list
    #Sort the DataFrame based on the Time_dt column
    #Get the indices that would sort the 'Time_dt' column
    sort_indices = np.argsort(df_merged['Time_dt'])
    #Use the indices to rearrange the rows of the entire DataFrame
    df_sorted = df_merged.iloc[sort_indices]
    return df_sorted
#----------------------------------------------------------------------------------

#----------------------------------------------------------------------------------
# MAIN
# GO THROUGH JSON AND ADD SILENT TURNS AND KEYLOGS
def add_keylogs_to_json(csv_a, csv_b, speaker_a_number, speaker_b_number, json_file_path):
    #Read the CSV files
    df_merged_sorted = merge_and_order_csvs(csv_a, csv_b, speaker_a_number, speaker_b_number)
    list_to_add_to_json_as_silent_turns = []
    with open(json_file_path, 'r') as json_file:
        json_data = json.load(json_file)

    #Store session ID for later
    session_id = json_data['SESSION']['sessionID']

    # Sort the TURN objects by their start timestamps
    sorted_json_data = sorted(json_data['SESSION']['TURNS'], key=lambda x: x['TURN']['TIME']['START'])


    # Iterate through TURN objects with access to previous and next.
    # This converts the json data to list of dictionaries
    for idx, turn_obj in enumerate(sorted_json_data):
    #The index works basically as a counter, so it starts at 0 and goes up by 1 for each turn
    #But it can also be used to access the previous and next turn
    #The problem is that we can't add things to the json directly, so we need to add them to a list
    #And then add the list to the json at the end, and then we need to sort the json by start time
        keylogs_for_turn = []
        keylogs_for_silent_turn = []
 
        start_time_str = turn_obj['TURN']['TIME']['START']
        end_time_str = turn_obj['TURN']['TIME']['END']

        # Convert timestamp strings to datetime objects
        start_time = datetime.strptime(start_time_str, '%H:%M:%S,%f')
        end_time = datetime.strptime(end_time_str, '%H:%M:%S,%f')

        # Access the previous TURN (if it exists)
        if idx > 0:
            previous_turn = sorted_json_data[idx - 1]
        else:
            previous_turn = None

        # Now, you can access information from the previous and next TURN objects
        if previous_turn != None:
            # Access and use information from the previous TURN
            prev_end_time_str = previous_turn['TURN']['TIME']['END']
            prev_end_time = datetime.strptime(prev_end_time_str, '%H:%M:%S,%f')

        #Check if it's first or last turn
        #FIRST TURN
        if idx == 0:
            #for index, row in df_merged.iterrows():
            for index, row in df_merged_sorted.iterrows():
                csv_timestamp = row['Relative Timestamp']
                csv_timestamp_clock_dt = datetime.strptime(csv_timestamp, "%H:%M:%S:%f")
                #If the keylog timestamp is within the turn timeframe, add it to the turn
                if start_time <= csv_timestamp_clock_dt <= end_time:
                    keylog_entry = str(row['Relative Timestamp']) + ' ' + str(row['Time']) + ' '  + str(row['Speaker']) + ' ' + row['Action'] + ' ' + str(row['Key']) + ' ' + str(row['Modifier']) + ' ' + str(row['MouseClick']) + ' ' + str(row['X']) + ' ' + str(row['Y'])
                    keylogs_for_turn.append(keylog_entry)
                #If the keylog timestamp goes before the first turn, add it as silent turn
                if csv_timestamp_clock_dt < start_time:
                    keylog_entry = str(row['Time']) + ' '  + str(row['Speaker']) + ' ' + row['Action'] + ' ' + str(row['Key']) + ' ' + str(row['Modifier']) + ' ' + str(row['MouseClick']) + ' ' + str(row['X']) + ' ' + str(row['Y'])
                    keylogs_for_silent_turn.append(keylog_entry)
                    silent_turn = {
                            'TURN':{
                                'TIME': {
                                    'START': '00:00:00,000',
                                    'END': start_time_str
                                    },
                                'KEYLOGS': keylogs_for_silent_turn
                                }
                            } 
                    if len(keylogs_for_silent_turn) > 0:
                        list_to_add_to_json_as_silent_turns.append(silent_turn)
            #Add keylog to normal turn
            if len(keylogs_for_turn) > 0:
                turn_obj['TURN']['KEYLOGS'] = keylogs_for_turn

        #LAST TURN
        elif idx == len(json_data) - 1:
            list_of_relative_timestamps = []
            #for index, row in df_merged.iterrows():
            for index, row in df_merged_sorted.iterrows():
                csv_timestamp = row['Relative Timestamp']
                list_of_relative_timestamps.append(csv_timestamp)
                csv_timestamp_clock_dt = datetime.strptime(csv_timestamp, "%H:%M:%S:%f")
                #If the keylog timestamp is within the turn timeframe, add it to the turn
                if start_time <= csv_timestamp_clock_dt <= end_time:
                    keylog_entry = str(row['Relative Timestamp']) + ' ' + str(row['Time']) + ' '  + str(row['Speaker']) + ' ' + row['Action'] + ' ' + str(row['Key']) + ' ' + str(row['Modifier']) + ' ' + str(row['MouseClick']) + ' ' + str(row['X']) + ' ' + str(row['Y'])
                    keylogs_for_turn.append(keylog_entry)
                #If the keylog timestamp goes after the last turn, add it as silent turn
                if csv_timestamp_clock_dt > end_time:
                    keylog_entry = str(row['Relative Timestamp']) + ' ' + str(row['Time']) + ' '  + str(row['Speaker']) + ' ' + row['Action'] + ' ' + str(row['Key']) + ' ' + str(row['Modifier']) + ' ' + str(row['MouseClick']) + ' ' + str(row['X']) + ' ' + str(row['Y'])
                    keylogs_for_silent_turn.append(keylog_entry)
                    silent_turn = {
                            'TURN':{
                                'TIME': {
                                    'START': end_time_str,
                                    'END': list_of_relative_timestamps[-1]
                                    },
                                'KEYLOGS': keylogs_for_silent_turn
                                }
                            } 
                    if len(keylogs_for_silent_turn) > 0:
                        list_to_add_to_json_as_silent_turns.append(silent_turn)
            #Add keylog to normal turn
            if len(keylogs_for_turn) > 0:
                turn_obj['TURN']['KEYLOGS'] = keylogs_for_turn

        #NORMAL TURN
        else:
            #Go thru csv to find keylogs inside this turn timeframe
            #for index, row in df_merged.iterrows():
            for index, row in df_merged_sorted.iterrows(): 
                csv_timestamp = row['Relative Timestamp']
                csv_timestamp_clock_dt = datetime.strptime(csv_timestamp, "%H:%M:%S:%f")
                #If the keylog timestamp is within the turn timeframe, add it to the turn
                if start_time <= csv_timestamp_clock_dt <= end_time:
                    keylog_entry = str(row['Relative Timestamp']) + ' ' + str(row['Time']) + ' '  + str(row['Speaker']) + ' ' + row['Action'] + ' ' + str(row['Key']) + ' ' + str(row['Modifier']) + ' ' + str(row['MouseClick']) + ' ' + str(row['X']) + ' ' + str(row['Y'])
                    keylogs_for_turn.append(keylog_entry)
                #If the keylog timestamp is before this turn, but after the previous one, add as silent turn
                if prev_end_time < csv_timestamp_clock_dt < start_time:
                    keylog_entry = str(row['Relative Timestamp']) + ' ' + str(row['Time']) + ' '  + str(row['Speaker']) + ' ' + row['Action'] + ' ' + str(row['Key']) + ' ' + str(row['Modifier']) + ' ' + str(row['MouseClick']) + ' ' + str(row['X']) + ' ' + str(row['Y'])
                    keylogs_for_silent_turn.append(keylog_entry)
                    #Add silent turn to json
                    silent_turn = {
                            'TURN':{
                                'TIME': {
                                    'START': prev_end_time_str,
                                    'END': start_time_str
                                    },
                                'KEYLOGS': keylogs_for_silent_turn
                                }
                            } 
                    if len(keylogs_for_silent_turn) > 0:
                        list_to_add_to_json_as_silent_turns.append(silent_turn)
            #Add keylog to normal turn
            if len(keylogs_for_turn) > 0:
                turn_obj['TURN']['KEYLOGS'] = keylogs_for_turn

    #Add silent turns to json
    #I added to the dictionary sorted_json_data, as that's where I added the keylog for normal turns
    for silent_turn in list_to_add_to_json_as_silent_turns:
        sorted_json_data.append(silent_turn) #--> why does it say it's nonetype T_T
    #Save turns json_data to file
    filename_to_save_turns = json_file_path[:-5] + ' - keylog turns.json'
    with open(filename_to_save_turns, 'w') as json_file:
        json.dump(sorted_json_data, json_file, indent=4)

    #Reopen updated json file and sort by start time
    with open(filename_to_save_turns, 'r') as json_file:
        json_data = json.load(json_file)

    #Remove duplicates from list of turns
    #First sort json. Then convert to set to remove duplicates. Then back to list
    sorted_json_data = sorted(json_data, key=lambda x: x['TURN']['TIME']['START'])
    sorted_json_data_unique_list = list()
    for sorted_turn in sorted_json_data:
        if sorted_turn not in sorted_json_data_unique_list:
            sorted_json_data_unique_list.append(sorted_turn)

    #Save json_data to file
    #Create new json with all the data
    annotation_json = {
        "SESSION": {
            "sessionID": session_id,
            "TURNS": sorted_json_data_unique_list
        }
    }
    filename_to_save_json_sorted = json_file_path[:-5] + ' - with keylog and sorted.json'
    with open(filename_to_save_json_sorted, 'w') as json_file:
        json.dump(annotation_json, json_file, indent=4)
    print('Done with', filename_to_save_json_sorted)

#----------------------------------------------------------------------------------

if __name__ == "__main__":
	csv_a = 'path_to_csv_a.csv' # Replace with the actual path to your keylog CSV file for speaker A
	csv_b = 'path_to_csv_b.csv' # Replace with the actual path to your keylog CSV file for speaker B
	speaker_a_number = 'ddd' # Replace with the actual speaker number for speaker A
	speaker_b_number = 'ddd' # Replace with the actual speaker number for speaker B
	json_file_path = 'path_to_json_file.json' # Replace with the actual path to your dialogue JSON file
	add_keylogs_to_json(csv_a, csv_b, speaker_a_number, speaker_b_number, json_file_path)