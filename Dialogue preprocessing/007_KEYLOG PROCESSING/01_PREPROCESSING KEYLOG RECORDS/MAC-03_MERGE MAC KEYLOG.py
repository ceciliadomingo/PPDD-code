import re
import csv
from datetime import datetime
import os

# Function to parse mouse log entries
def parse_mouse_log(entry):
    match = re.search(r'Mouse: (\w+)\((.*?)\) Time: (.*?)$', entry)
    if match:
        mouse_action = match.group(1)
        mouse_params = match.group(2)
        timestamp = match.group(3)
        return mouse_action, mouse_params, timestamp
    return None, None, None

# Function to parse keyboard log entries
def parse_keyboard_log(entry):
    parts = entry.split()
    if len(parts) >= 2:
        word_and_key = parts[0]
        try:
            key_search = re.search(r'Key\.(.*)', word_and_key)
            key = key_search.group(1)
        except:
            key = word_and_key.strip("'")
        timestamp = parts[1] + ' ' + parts[2]
        return key, timestamp
    return None, None

def merge_mac_keylog(mouse_trimmed_txt, keyboard_trimmed_txt, speaker):
	# Read and process mouse log
	mouse_data = []
	with open(mouse_trimmed_txt, 'r') as mouse_file:
		for line in mouse_file:
			mouse_action, mouse_params, timestamp = parse_mouse_log(line)
			if mouse_action and mouse_params and timestamp:
				mouse_data.append((mouse_action, mouse_params, timestamp))

	# Read and process keyboard log
	keyboard_data = []
	with open(keyboard_trimmed_txt, 'r') as keyboard_file:
		for line in keyboard_file:
			key, timestamp = parse_keyboard_log(line)
			#Remove trailing whitespace from timestamp
			if key and timestamp:
				keyboard_data.append((key, timestamp))

	# Merge mouse and keyboard data
	merged_data = []
	for mouse_entry in mouse_data:
		mouse_action, mouse_params, mouse_timestamp = mouse_entry
		mouse_timestamp = mouse_timestamp.strip() # Remove trailing whitespace from mouse_timestamp, else datetime conversion will fail
		#Remove trailing whitespace from mouse_timestamp
		if mouse_action == 'Move':
			x, y = re.search(r'(.*?), (.*)', mouse_params).groups()
			#Format is Move(791.9664306640625, 459.5268249511719)
			#I need to change regex to round to no decimal places
			#DONE
			rounded_x = round(float(x), 0)
			rounded_y = round(float(y), 0)
			merged_data.append((mouse_timestamp, 'Move', '', '', '', rounded_x, rounded_y))
		elif mouse_action == 'Click':
			#Format of mosueparams here is Click(1107.2633056640625, 242.18179321289062, <Button.left: ((1, 2, 6), 0)>, True)
			#I need to add a regex to extract the button pressed
			#DONE
			button = re.search(r'Button\.(.*?):', mouse_params).group(1)
			merged_data.append((mouse_timestamp, 'Pressed', '', '', button.capitalize(), '', '', ''))

	for keyboard_entry in keyboard_data:
		key, keyboard_timestamp = keyboard_entry
		merged_data.append((keyboard_timestamp, 'Key', key.capitalize(), '', '', '', '', ''))


	# Write merged data to CSV
	csv_columns = ['Time', 'Action', 'Key', 'Modifier', 'Mouse', 'X', 'Y']
	# join the directory of the mosue txt and add the name of the output file to it
	output_filepath = os.path.join(os.path.dirname(mouse_trimmed_txt), f'Merged_Keylog_{speaker}.csv')


	with open(output_filepath, 'w', newline='') as csv_file:
		csv_writer = csv.writer(csv_file)
		csv_writer.writerow(csv_columns)
		csv_writer.writerows(merged_data)

	print(f'Data has been merged and saved to {output_filepath}')

if __name__ == "__main__":
	# Example usage
	mouse_trimmed_txt = 'path/to/mouse_trimmed_logs.txt'  # Change this to the path of your mouse log file
	keyboard_trimmed_txt = 'path/to/keyboard_trimmed_logs.txt'  # Change this to the path of your keyboard log file
	speaker = 'ddd'  # Change this to the appropriate speaker ID
	merge_mac_keylog(mouse_trimmed_txt, keyboard_trimmed_txt, speaker)
