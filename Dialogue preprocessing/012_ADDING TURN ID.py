#Adding turn ID
import json
import os


def add_turnID(inputjson_filepath,outputjson_filepath):
    # Open json file
    with open(inputjson_filepath, 'r') as f:
        json_data = json.load(f)

    # Add turn ID
    turn_ID = 1
    for turn_obj in json_data['SESSION']['TURNS']:
        turn_obj['TURN_ID'] =  turn_ID
        turn_ID += 1

    # Save json
    with open(outputjson_filepath, 'w') as f:
        json.dump(json_data, f, indent=4)

if __name__ == "__main__":
	inputjson_filepath = 'path/to/input.json' #Replace with the actual path to your input JSON file
	outputjson_filepath = 'path/to/output.json' #Replace with the desired path for your output JSON file
	add_turnID(inputjson_filepath,outputjson_filepath)