# Script that takes as input a json file with transcripts and diarization objects
# and reorganises the turns chronologically based on the start time of each turn

import json
import re
import os

# Function to convert time format "HH:MM:SS,mmm" to seconds
def time_to_seconds(time_str):
    parts = re.split('[:,]', time_str)
    hours, minutes, seconds, milliseconds = map(int, parts)
    total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
    return total_seconds

# Function to output reorganized json (sorted by start time)
def json_reorganiser(input_json_fullpath):
    # Load the JSON file
	with open(input_json_fullpath, 'r') as f:
		data = json.load(f)

    # Extract turns
	turns = data['SESSION']['TURNS']
	print("Number of turns:", len(turns))

    # Sort turns by the start time
	sorted_turns = sorted(turns, key=lambda turn: time_to_seconds(turn['TURN']['TIME']['START']))

    # Update the data with sorted turns
	data['SESSION']['TURNS'] = sorted_turns

    # Save the sorted JSON to a new file
	# The output is saved in the same directory as the input file
	output_dir = os.path.dirname(input_json_fullpath)
	output_filename = os.path.basename(input_json_fullpath).replace('.json', '_sorted.json')
	with open(os.path.join(output_dir, output_filename), 'w') as f:
		json.dump(data, f, indent=4)

	print("Turns have been sorted and saved to a new JSON file.")

if __name__ == "__main__":
	input_json_fullpath = 'path/to/your/input.json'  # Replace with your actual path
	json_reorganiser(input_json_fullpath)