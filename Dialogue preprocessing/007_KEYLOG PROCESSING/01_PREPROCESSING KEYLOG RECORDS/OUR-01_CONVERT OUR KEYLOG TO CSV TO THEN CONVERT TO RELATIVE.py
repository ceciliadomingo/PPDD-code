# Convert keylog obtained with OUR keylogger to csv to then run the "convert keylog time to relative" script

# Desired output format:    Time	                Action	Key	    Modifier	MouseClick	X   	Y	Task
# Example with mouseclick: 2021-06-01T13:37:40.000	Pressed	BLANK	  BLANK        Left    BLANK  BLANK	BLANK
# Example with move:       2021-06-01T13:37:40.000	Move	BLANK	  BLANK	       BLANK    666	   33   BLANK
# Example with key:        2021-06-01T13:37:40.000	Key		D2		  Shift       BLANK    BLANK  BLANK	BLANK 

# Input format:
# Example with mouseclick:
# Mouse: Click(226, 95, <Button.left: (4, 2, 0)>, True) Time: 2024-03-05 20:12:01.670295
# Mouse: Released(226, 95, <Button.left: (4, 2, 0)>, False) Time: 2024-03-05 20:12:01.805291 (this we will ignore)
# Example with move:
# Mouse: Move(223, 87) Time: 2024-03-05 20:12:01.294294
# Example with key:
# '4'    2024-03-05 19:33:00.686401
# Key.shift_r    2024-03-05 19:40:40.497124 (when there's a shift, we'll need to merge the entry with the next one)
# '_'    2024-03-05 19:40:40.897646


import csv
import re
from datetime import datetime
import csv
import re

def parse_keylog(input_file):
    # Regular expressions to match the different types of log entries
    mouse_click_re = re.compile(r"Mouse: (Click|Released)\((\d+), (\d+), <Button\.(left|right).*>, (True|False)\) Time: (.*)")
    mouse_move_re = re.compile(r"Mouse: Move\((-?\d+), (-?\d+)\) Time: (.*)") # added -? to allow for negative numbers
    key_press_re = re.compile(r"(.+?)\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)")

    # Output CSV column names
    columns = ['Time', 'Action', 'Key', 'Modifier', 'MouseClick', 'X', 'Y', 'Task']

    # To track skipped entries
    skipped_entries = []

    # Variables to handle modifier keys like Shift
    shift_pressed = False
    last_key_time = None

    output_file = input_file.replace('.txt', '.csv')
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns)
        writer.writeheader()

        for line in infile:
            # Debugging: Print out the current line being processed
            print(f"Processing line: {line.strip()}")

            # Check for mouse clicks
            mouse_click_match = mouse_click_re.match(line)
            if mouse_click_match:
                action, x, y, button, is_pressed, timestamp = mouse_click_match.groups()
                if is_pressed == "True":  # Only log mouse clicks, not releases
                    writer.writerow({
                        'Time': f"'{timestamp}", #Adding ' to force Excel to treat it as text
                        'Action': 'Pressed',
                        'Key': 'BLANK',
                        'Modifier': 'BLANK',
                        'MouseClick': button.capitalize(),
                        'X': 'BLANK',
                        'Y': 'BLANK',
                        'Task': 'BLANK'
                    })
                continue

            # Check for mouse movements
            mouse_move_match = mouse_move_re.match(line)
            if mouse_move_match:
                x, y, timestamp = mouse_move_match.groups()
                writer.writerow({
                    'Time': f"'{timestamp}", #Adding ' to force Excel to treat it as text
                    'Action': 'Move',
                    'Key': 'BLANK',
                    'Modifier': 'BLANK',
                    'MouseClick': 'BLANK',
                    'X': x,
                    'Y': y,
                    'Task': 'BLANK'
                })
                continue

            # Check for key presses
            key_press_match = key_press_re.match(line)
            if key_press_match:
                key, timestamp = key_press_match.groups()
                
                # Check if the key is a modifier (Shift, Ctrl, etc.)
                if "shift" in key.lower():
                    shift_pressed = True
                    last_key_time = timestamp
                    continue
                
                # If shift was pressed earlier, this key gets marked with the modifier
                writer.writerow({
                    'Time': f"'{timestamp}", #Adding ' to force Excel to treat it as text
                    'Action': 'Key',
                    'Key': key,
                    'Modifier': 'Shift' if shift_pressed else 'BLANK',
                    'MouseClick': 'BLANK',
                    'X': 'BLANK',
                    'Y': 'BLANK',
                    'Task': 'BLANK'
                })
                shift_pressed = False  # Reset shift after using it
                last_key_time = timestamp
                continue

            # If none of the above matched, log this line as skipped
            skipped_entries.append(line)
    
    # Print skipped entries to help debug
    if skipped_entries:
        print(f"Skipped {len(skipped_entries)} entries:")
        for skipped in skipped_entries:
            print(skipped.strip())



if __name__ == "__main__":
    input_file = 'path/to/your/keylog.txt'  # Update this to your actual keylog file path
    parse_keylog(input_file)
