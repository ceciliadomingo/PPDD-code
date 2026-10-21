#Add code and trees to json
import os
import json
from datetime import datetime, timedelta

def make_timestamp_relative(timestamp, starting_point): #starting_point is a string in the format '13:37:40,000'
    # Starting point timestamp
    starting_point = datetime.strptime(starting_point, '%H:%M:%S,%f')

    # Calculate the difference
    difference = timestamp - starting_point

    # Extract hours, minutes, seconds, and milliseconds
    hours = difference.seconds // 3600
    minutes = (difference.seconds // 60) % 60
    seconds = difference.seconds % 60
    milliseconds = difference.microseconds // 1000

    # Format the relative timestamp string
    relative_timestamp = '{:02d}:{:02d}:{:02d},{:03d}'.format(hours, minutes, seconds, milliseconds)
    relative_timestamp_datetime = datetime.strptime(relative_timestamp, '%H:%M:%S,%f')

    return relative_timestamp_datetime

def add_code_to_json(code_folder, json_file, starting_point): #starting_point is a string in the format '13:37:40,000'

    # Load JSON data
    with open(json_file, 'r') as json_file_opened:
        session_data = json.load(json_file_opened)

    # Load code data (filepaths)
    code_data_filename_list = []
    for root, dirs, files in os.walk(code_folder):
        for file in files:
            if file.endswith('.py'):
                code_filename_full = os.path.join(root, file)
                #code_filename_base = os.path.splitext(os.path.basename(code_filename_full))[0] # Remove folder and file extension
                code_data_filename_list.append(code_filename_full)

    # Add code data to JSON data
    for turn_obj in session_data['SESSION']['TURNS']:
        start_time = datetime.strptime(turn_obj['TURN']['TIME']['START'], '%H:%M:%S,%f')
        end_time = datetime.strptime(turn_obj['TURN']['TIME']['END'], '%H:%M:%S,%f')
        
        code = []
        for code_filename_full in code_data_filename_list:         
            tree_file = code_filename_full[:-3] + '_tree.txt' #[:-3] removes .py extension
            with open(code_filename_full, 'r') as code_file:
                code_file_nametype = code_file.name # Extract the actual filename from the TextIOWrapper
                code_filename_base = os.path.splitext(os.path.basename(code_file_nametype))[0] # Remove folder and file extension
                if len(code_filename_base) >2: #I want to exclude exercise files without timestamps (originals without edits)
                    code_timestamp = code_filename_base.split('_', 1)[1] #Remove exercise number and underscore
                    code_time_datetime = datetime.strptime(code_timestamp, "%Y%m%d%H%M%S")
                    code_time_formatted = code_time_datetime.strftime('%H:%M:%S,%f')[:-3]  # Removing the last 3 digits of microseconds
                    code_time_formatted_datetime = datetime.strptime(code_time_formatted, '%H:%M:%S,%f')
                    code_time_relative = make_timestamp_relative(code_time_formatted_datetime, starting_point)
                    if start_time <= code_time_relative <= end_time:
                        with open(tree_file, 'r') as tree_file:
                            tree = tree_file.read()
                            code_entry = {
                                    'TIME': code_time_relative.strftime('%H:%M:%S,%f')[:-3],
                                    'FILE': code_filename_base,
                                    'CODE': code_file.read(),
                                    'TREE': tree
                                }
                            code.append(code_entry)              
        turn_obj['TURN']['CODE ENTRIES'] = code

    # Generate a new output filename
    output_filename = json_file[:-5] + '_with_code.json'
    with open(output_filename, 'w') as json_output:
        json.dump(session_data, json_output, indent=4)

    print('Done with ' + json_file)


if __name__ == "__main__":
	code_folder = 'path_to_code_folder' # Replace with the actual path to your code folder
	json_file = 'path_to_json_file' # Replace with the actual path to your JSON
	starting_point = "HH:MM:SS,mmm" # Replace with the actual starting point timestamp
	add_code_to_json(code_folder, json_file, starting_point)