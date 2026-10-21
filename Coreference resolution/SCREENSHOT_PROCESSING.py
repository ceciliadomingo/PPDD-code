from random import random, sample
import cv2
import os
import json
import re
import base64
from openai import OpenAI
import time


# Function to find the screen resolution for each speaker
def find_resolution(speaker_A, speaker_B, folder_of_dialogues):
    # Looking for folder for this session
    session_folder = ""
    for subfolder in os.listdir(folder_of_dialogues):
        if speaker_A in subfolder and speaker_B in subfolder:
            session_folder = os.path.join(folder_of_dialogues,subfolder)
            break
    # Now I have to find the keylog folder for each speaker
    resolution_info_files = []
    for root, dirs, files in os.walk(session_folder):
        for file in files:
            if "resolution" in file or "Resolution" in file:
                resolution_info_files.append(os.path.join(root, file))
    # Now I use the files to read the resolution info
    # I first add a default value in case no alternative value is found. I use the resolution of my laptop, which is the most common worldwide these days.
    resolution_A = (1920, 1080)
    resolution_B = (1920, 1080)
    # It is in the format Size(width=1920, height=1080)
    for res_file in resolution_info_files:
        with open(res_file, 'r') as file:
            content = file.read()
            # Extract the resolution using regex
            match = re.search(r'Size\(width=(\d+), height=(\d+)\)', content)
            if match:
                width = int(match.group(1))
                height = int(match.group(2))
                if speaker_A in res_file:
                    resolution_A = (width, height)
                elif speaker_B in res_file:
                    resolution_B = (width, height)
    # (xa, ya), (xb, yb)
    return resolution_A, resolution_B

# Function to find keylog records that may be significant (clicking and typing)
def extract_significant_keylogs(movements_A, keys_A, resolution_A):
    # MOVEMENTS
    main_points_movement = []
    if len(movements_A) > 0:
        # The input movements list is in the format [(keylog_entry, x_coord, y_coord),...]
        # I define a significant difference as 25% of the screen resolution
        SIGNIFICANCE_THRESHOLD_X = resolution_A[0] * 0.25
        SIGNIFICANCE_THRESHOLD_Y = resolution_A[1] * 0.25
        # I initialise the filtering list and add the first point
        latest_relevant_point = movements_A[0]
        main_points_movement.append(latest_relevant_point)
        # I go through the movements and find those that are significantly different from the last point we saved as significant
        for keylog_entry, x, y in movements_A[1:]:
            if abs(x - latest_relevant_point[1]) >= SIGNIFICANCE_THRESHOLD_X or abs(y - latest_relevant_point[2]) >= SIGNIFICANCE_THRESHOLD_Y:
                #print(f"x - latest_relevant_point[1]) >= SIGNIFICANCE_THRESHOLD_X or abs(y - latest_relevant_point[2]) >= SIGNIFICANCE_THRESHOLD_Y: {abs(x - latest_relevant_point[1])} is {x} - {latest_relevant_point[1]} >= {SIGNIFICANCE_THRESHOLD_X} or {abs(y - latest_relevant_point[2])} is{y} - {latest_relevant_point[2]} >= {SIGNIFICANCE_THRESHOLD_Y}")
                main_points_movement.append((keylog_entry, x, y))
                latest_relevant_point = (keylog_entry, x, y)

    # KEYS
    main_points_keys = []
    if len(keys_A) > 0:
        # The input keys list is in the format [(keylog_entry, timestamp),...]
        # For the keys, the criterion for significance will be time. If keys are typed in quick succession, I just want the position of the last one (so the screenshot will show the whole typed word)
        # I set the time threshold as 3 seconds, which may also result in a new code file
        TIME_THRESHOLD = 3
        # I initialise the filtering list and add the last point
        latest_relevant_keypoint = keys_A[-1]
        main_points_keys.append(latest_relevant_keypoint)
        # I go through the keys in reverse order starting after the last one and find those that are significantly different from the last point we saved as significant (latest_relevant_keypoint)
        for keylog_entry, timestamp in reversed(keys_A[:-1]):
            if abs(timestamp - latest_relevant_keypoint[1]) >= TIME_THRESHOLD:
                main_points_keys.append((keylog_entry, timestamp))
        # Now I de-reverse the list main_points_keys
        main_points_keys = list(reversed(main_points_keys))
    return main_points_movement, main_points_keys

# Function to transform timestamp formats
def convert_timestamp_to_seconds(timestamp_string): 
    # In the code entries, the time is in the format 00:05:37,000
    if "," in timestamp_string:
        parts = timestamp_string.split(',')
        milliseconds = int(parts[1])
        subparts = parts[0].split(':')
        seconds = int(subparts[2]) + (milliseconds/1000)
        minutes = int(subparts[1]) + (seconds/60)
        hours = int(subparts[0]) + (minutes/60)
    else:
        # Convert string in the format 00:00:55:895 to seconds
        parts = timestamp_string.split(':')
        milliseconds = int(parts[3])
        seconds = int(parts[2]) + (milliseconds/1000)
        minutes = int(parts[1]) + (seconds/60)
        hours = int(parts[0]) + (minutes/60)
    return hours*3600

# Function to find code states to link them to keylog events
def find_code_state_with_timestamp(dialogue_json_path, filtered_keylog_events_folder,folder_of_dialogues):
    dictionary_of_data_for_screenshots = {}
    dictionary_of_filtered_keylogs = {}
    timestamp_in_keylog_pattern = re.compile(r'(\d\d:\d\d:\d\d:\d\d\d) \d\d\d\d') # 00:00:55:895 2024-03-20T20:29:31:895 028 Key 'e' nan nan nan nan
    with open(dialogue_json_path, 'r') as file:
        data = json.load(file)
        # Get dialogue number
        dialogue_number = data["SESSION"]["sessionID"]
        dialogue_number = dialogue_number.replace("&","x").replace("_","x").replace("-","x").replace("X","x") # Ensure uniform formatting of dialogue numbers
        # Get speakers. I make sure they're strings to find them in the keylog entries
        speaker_A = str(dialogue_number[:3])
        speaker_B = str(dialogue_number[4:])
        dictionary_of_data_for_screenshots[dialogue_number] = {} # Initialise dicitonary where we'll store timestamps and the associated code state
        dictionary_of_filtered_keylogs[dialogue_number] = {} # Initialise dictionary for filtered keylogs
        # Add timestamps for relevant keylog events
        # I will also use this loop to save all the code state data to link it later
        code_entries_list = []
        for turn in data["SESSION"]["TURNS"]:
            if len(turn["TURN"]["CODE ENTRIES"]) > 0:
                for code_entry in turn["TURN"]["CODE ENTRIES"]:
                    code_entries_list.append(code_entry)
            try: # Turns without keylogs don't have an empty key
                poteito = turn["TURN"]["KEYLOGS"]
            except KeyError:
                print(f"Turn {turn["TURN_ID"]} has no keylogs")
                continue
            if len(turn["TURN"]["KEYLOGS"]) > 0:
                # Initialise lists to store events that are not clicking to then filter the important ones
                movements_A = []
                movements_B = []
                keys_A = []
                keys_B = []
                pressed_A = []
                pressed_B = []
                for keylog_entry in turn["TURN"]["KEYLOGS"]:
                    partecitas = keylog_entry.split(" ")
                    if len(partecitas) != 9:
                        print(keylog_entry)
                    # If there was mouse movement or typing, we only want big changes, or if the movement is small, the last state
                    if f" {speaker_A} " in keylog_entry:
                        if "Move" in keylog_entry:
                            parts = keylog_entry.split(" ")
                            x_coord = int(float(parts[7]))
                            y_coord = int(float(parts[8]))
                            movements_A.append((keylog_entry, x_coord, y_coord))
                        if "Key" in keylog_entry:
                            parts = keylog_entry.split(" ")
                            timestamp = convert_timestamp_to_seconds(parts[0])
                            keys_A.append((keylog_entry, timestamp))
                    if f" {speaker_B} " in keylog_entry:
                        if "Move" in keylog_entry:
                            parts = keylog_entry.split(" ")
                            x_coord = int(float(parts[7]))
                            y_coord = int(float(parts[8]))
                            movements_B.append((keylog_entry, x_coord, y_coord))
                        if "Key" in keylog_entry:
                            parts = keylog_entry.split(" ")
                            timestamp = convert_timestamp_to_seconds(parts[0])
                            keys_B.append((keylog_entry, timestamp))
                    # If the user clicked, this is an important event
                    if "Pressed" in keylog_entry:
                        parts = keylog_entry.split(" ")
                        keylog_timestamp = parts[0]
                        keylog_timestamp_seconds = convert_timestamp_to_seconds(keylog_timestamp)
                        dictionary_of_data_for_screenshots[dialogue_number][keylog_timestamp_seconds] = "pending code state"
                        if f" {speaker_A} " in keylog_entry:
                            pressed_A.append((keylog_entry, keylog_timestamp_seconds))
                        if f" {speaker_B} " in keylog_entry:
                            pressed_B.append((keylog_entry, keylog_timestamp_seconds))
                # FILTERING MOVE EVENTS: Now I need to look at the coordinates and find big changes
                resolution_A, resolution_B = find_resolution(speaker_A, speaker_B,folder_of_dialogues) # (xa, ya), (xb, yb)
                # moves --> [("keylog",x,y),...]
                # keys --> [("keylog",timestamp in seconds),...]
                significant_moves_A, significant_keys_A = extract_significant_keylogs(movements_A, keys_A, resolution_A)
                significant_moves_B, significant_keys_B = extract_significant_keylogs(movements_B, keys_B, resolution_B)
                # Save a log for quality control
                turn_id = turn["TURN_ID"]
                dictionary_of_filtered_keylogs[dialogue_number][turn_id] = {
                    "speaker_A": {
                        "significant_moves": significant_moves_A,
                        "significant_keys": significant_keys_A,
                        "pressed": pressed_A
                    },
                    "speaker_B": {
                        "significant_moves": significant_moves_B,
                        "significant_keys": significant_keys_B,
                        "pressed": pressed_B
                    }
                }
                # Adding the significant points to the dictionary
                if len(significant_moves_A) > 0:
                    for significant_move in significant_moves_A:
                        parts = significant_move[0].split(" ")
                        timestamp = convert_timestamp_to_seconds(parts[0])
                        dictionary_of_data_for_screenshots[dialogue_number][timestamp] = "pending code state"
                if len(significant_moves_B) > 0:
                    for significant_move in significant_moves_B:
                        parts = significant_move[0].split(" ")
                        timestamp = convert_timestamp_to_seconds(parts[0])
                        dictionary_of_data_for_screenshots[dialogue_number][timestamp] = "pending code state"
                if len(significant_keys_A) > 0:
                    for significant_key in significant_keys_A:
                        dictionary_of_data_for_screenshots[dialogue_number][significant_key[1]] = "pending code state"
                if len(significant_keys_B) > 0:
                    for significant_key in significant_keys_B:
                        dictionary_of_data_for_screenshots[dialogue_number][significant_key[1]] = "pending code state"
    # Now I go through the dictionary of data for screenshots and add the code states
    for timestamp in dictionary_of_data_for_screenshots[dialogue_number]:
        # I iterate through code entries list and find a timestamp that is the same or the closest before it
        for code_entry in code_entries_list: # This tests every code entry, so it will add some early ones, but they will be iteratively replaced by the latest
            if convert_timestamp_to_seconds(code_entry["TIME"]) <= timestamp:
                dictionary_of_data_for_screenshots[dialogue_number][timestamp] = code_entry["CODE"]
    # Issue 1: early keylogs that don't create code will have no code entries (e.g, mouse movements) --> need to add task instructions
    keys = list(dictionary_of_data_for_screenshots[dialogue_number].keys()) # List of keys to be able to use indexes
    for index, key in enumerate(dictionary_of_data_for_screenshots[dialogue_number]):
        if dictionary_of_data_for_screenshots[dialogue_number][key] == "pending code state":
            # I advance forward until I find instructions
            instructions = ""
            while instructions == "":
                code_entry_as_code = dictionary_of_data_for_screenshots[dialogue_number][keys[index + 1]] # I check if the next dictionary entry has a code state
                if code_entry_as_code != "pending code state":
                    match = re.match(r'^(# .+?\n)+', code_entry_as_code)
                    instructions = match.group(0)
                else:
                    index = index + 1
            # I add the instructions to the dictionary
            dictionary_of_data_for_screenshots[dialogue_number][key] = instructions            
    # Issue 2: some dialogues do 2 exercises (or more). There might be movements over a new exercise before a code entry for that exercise is saved
    # Find the changing point(s) using the code_entries_list
    list_of_changing_points = [] # I use a list because there can be several transitions (e.g., one session had 5 exercises)
    for index, code_entry in enumerate(code_entries_list):
        current_code_beginning_match = re.match(r'^(#.+?\n)+', code_entry["CODE"])
        current_code_beginning = current_code_beginning_match.group(0)
        if index < len(code_entries_list) - 1:
            next_code_beginning_match = re.match(r'^(#.+?\n)+', code_entries_list[index+1]["CODE"])
            next_code_beginning = next_code_beginning_match.group(0)
            if current_code_beginning != next_code_beginning:
                task_change_start = convert_timestamp_to_seconds(code_entry["TIME"])
                task_change_end = convert_timestamp_to_seconds(code_entries_list[index+1]["TIME"])
                interval_length = task_change_end - task_change_start
                list_of_changing_points.append((task_change_start,task_change_end,interval_length,code_entry["CODE"],next_code_beginning))
        else:
            print(f"Last code entry in {dialogue_number} is {code_entry['CODE']}, so no next code beginning to compare with")
    # Now I find the points in the dictionary_of_data_for_screenshots that fall inside this interval
    for timestamp in dictionary_of_data_for_screenshots[dialogue_number]:
        for changing_point in list_of_changing_points: # changing_point = (task_change_start, task_change_end, interval_length, code_entry["CODE"], next_code_beginning)
            if timestamp >= changing_point[0] and timestamp <= changing_point[1]:
                # If it's on the lower bound of the interval, earlier task
                if timestamp < (timestamp + (interval_length/2)):
                    dictionary_of_data_for_screenshots[dialogue_number][timestamp] = changing_point[3]
                # If it's on the upper bound of the interval, later task
                if timestamp >= (timestamp + (interval_length/2)):
                    dictionary_of_data_for_screenshots[dialogue_number][timestamp] = changing_point[4]
    # Save the dictionary_of_data_for_screenshots
    data_for_screenshots_filename = f"Data_for_screenshots_{dialogue_number}.json"
    with open(os.path.join(filtered_keylog_events_folder, data_for_screenshots_filename), "w") as f:
        json.dump(dictionary_of_data_for_screenshots, f, indent=4)
    # Save filtered keylogs dictionary with indent
    filtered_keylogs_filename = f"Filtered_keylogs_{dialogue_number}.json"
    with open(os.path.join(filtered_keylog_events_folder, filtered_keylogs_filename), "w") as f:
        json.dump(dictionary_of_filtered_keylogs, f, indent=4)
    return dictionary_of_data_for_screenshots, dialogue_number

# Function to reduce the number of keylog events to the potentially most important ones
def trim_down_data_for_screenshots_further(filtered_keylog_events_folder,dictionary_of_data_for_screenshots, dialogue_number):
    # Sort the items by timestamp (float value of keys)
    items = sorted(dictionary_of_data_for_screenshots[dialogue_number].items(), key=lambda kv: float(kv[0]))
    # Round timestamps and keep latest occurrence if duplicate
    rounded_data = {}
    for original_timestamp, value in items:
        ts = float(original_timestamp)
        rounded_ts = round(ts)  # Python's round() rounds .5 to nearest even
        rounded_data[rounded_ts] = value  # Later overwrites earlier
    # Save as json
    json_filename = f"Trimmed_data_for_screenshots_{dialogue_number}.json"
    trimmed_keylog_data_path = os.path.join(filtered_keylog_events_folder, json_filename)
    with open(trimmed_keylog_data_path, "w") as f:
        json.dump(rounded_data, f, indent=4)
    return trimmed_keylog_data_path

# Function to take screenshots at the relevant times (significant keylog events)
def take_screenshot(video_path, image_folder, trimmed_keylog_data_path, dialogue_number):
    # List of timestamps in seconds. They are the keys from the keylog events json
    with open(trimmed_keylog_data_path, "r") as f:
        data = json.load(f)
        timestamp_list = list(data.keys())
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    # Get the framerate
    fps = cap.get(cv2.CAP_PROP_FPS)

    for t in timestamp_list:
        # Calculate frame number
        frame_number = int(int(t) * fps)
        # Set the video position
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

        ret, frame = cap.read() # Ret is a boolean that indicates if the frame was successfully captured
        if ret:
            output_path = os.path.join(image_folder, f"{dialogue_number}_screenshot_{t}.jpg")
            cv2.imwrite(output_path, frame)
            print(f"Saved screenshot at {t}s → {output_path}")
        else:
            print(f"Failed to capture frame at {t}s")

    cap.release()
    
# Function to call a GPT model to detect cursors in the screenshots and add tags to the code state text
def call_gpt_to_detect_cursor(key_path,image_path, code_state, cursor_colours, model):
    # Initialize OpenAI client
    with open(key_path, 'r') as file:
        key = file.read().strip()
    client = OpenAI(api_key=key)

    #start_time_image = time.time()
    # Function to encode the image
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    # Getting the Base64 string
    base64_image = encode_image(image_path)
    #end_time_image = time.time()
    #print(f"Image encoding took {end_time_image - start_time_image:.2f} seconds")

    start_time_model = time.time()
    response = client.responses.create(
        model = model,
        input=[
            {
                "role": "user",
                "content": [
                    { "type": "input_text", "text": f"You are a cursor-detection tool in an NLP pipeline. Look for the cursors with the colors {cursor_colours[0]} and {cursor_colours[1]} in the image and, if you find them, add <<COLOR CURSOR>> tags of the right color in the appropriate point(s) of the following text, which transcribes the content of the code window: {code_state}" },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{base64_image}",
                    },
                ],
            }
        ]
    )
    end_time_model = time.time()
    model_inference_time = end_time_model - start_time_model
    response_text = response.output_text
    temperature_used = response.temperature
    top_p_used = response.top_p
    model_used = response.model
    reasoning_used = response.reasoning # json object should be like 
                #"reasoning": {
                #"effort": null,
                #"summary": null
                #},
    tokens_used = response.usage # json object should be like
            #"usage": {
            #"input_tokens": 32,
            #"input_tokens_details": {
            #  "cached_tokens": 0
            #},
            #"output_tokens": 18,
            #"output_tokens_details": {
            #  "reasoning_tokens": 0
            #},
            #"total_tokens": 50
    return response_text, model_inference_time, temperature_used, top_p_used, model_used, reasoning_used, tokens_used

def process_images_in_folder(key_path, image_folder, dialogue_number, cursor_colours, model):
    for image in os.listdir(image_folder):
        image_path = os.path.join(image_folder, image)
        list_of_images = []
        if image_path.endswith(".jpg") and dialogue_number in image_path:
            list_of_images.append(image_path)
    # USING REDUCED LIST
    for image_path in list_of_images:
        # Load the corresponding code state
        timestamp = image_path.split("_screenshot_")[1].replace("_compressed.png","")
        with open(trimmed_keylog_data_path, 'r') as f:
            data = json.load(f)
            code_state = data[timestamp]
        # Call GPT to detect cursors
        print(f"About to call GPT with {image_path}")
        response_text, model_inference_time, temperature_used, top_p_used, model_used, reasoning_used, tokens_used = call_gpt_to_detect_cursor(key_path, image_path, code_state, cursor_colours, model)
        json_of_code_states_with_cursor_detected_by_llm[dialogue_number][timestamp] = {
                "original code state": code_state,
                "response_text": response_text,
                "model_inference_time": model_inference_time,
                "temperature_used": temperature_used,
                "top_p_used": top_p_used,
                "model_used": model_used,
                "reasoning_used": str(reasoning_used),
                "tokens_used": str(tokens_used)
            }
        # Save a txt backup in case the code has issues
        txt_backup_filename = os.path.join(image_folder, f"GPT_response_backup_{dialogue_number}.txt")
        with open(txt_backup_filename, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] = {{\n")
                f.write(f"  \"original code state\": {code_state},\n")
                f.write(f"  \"response_text\": {response_text},\n")
                f.write(f"  \"model_inference_time\": {model_inference_time},\n")
                f.write(f"  \"temperature_used\": {temperature_used},\n")
                f.write(f"  \"top_p_used\": {top_p_used},\n")
                f.write(f"  \"model_used\": {model_used},\n")
                f.write(f"  \"reasoning_used\": {reasoning_used},\n")
                f.write(f"  \"tokens_used\": {tokens_used}\n")
                f.write(f"}}\n")

    # Save the json
    json_output_folder = os.path.join(image_folder, "Code states with detected cursors")
    json_output_filename = f"json_of_code_states_with_cursor_detected_by_llm_{dialogue_number}.json"
    json_output_path = os.path.join(json_output_folder, json_output_filename)
    with open(json_output_path, "w") as f:
        json.dump(json_of_code_states_with_cursor_detected_by_llm, f, indent=4)
    return json_of_code_states_with_cursor_detected_by_llm


if __name__ == "__main__":
	# Parameters
	model = "gpt-5" # Replace with suitable API model ID for a multimodal model
	dialogue_number = 'dddxddd' # Replace with the dialogue number you want to process (e.g., '002x045')
	cursor_colours = ["purple", "pink"] # Replace with the cursor colours used in the video being processed (e.g., ["purple", "pink"])
    # Input files
	key_path = 'path/to/your/openai/api/key.txt' # Replace with the path to your OpenAI API key
	folder_of_dialogues = 'path/to/folder/of/dataset/folders' # Replace with teh path to the folder containing all the dialogue folders
	video_path = 'path/to/video/file.mp4' # Replace with the path to the video file showing the code
	dialogue_json_path = 'path/to/dialogue/json/file.json' # Replace with the path to the dialogue JSON file containing the combined dialogue data (keylogs, code states, etc.) for the dialogue being processed
	# Outputs
	image_folder = 'output/path/for/screenshots' # Replace with desired output path for screenshots
	filtered_keylog_events_folder = 'path/to/save/filtered/keylog/events' # Replace with desired output path for filtered keylog events
    # Functions
	dictionary_of_data_for_screenshots, dialogue_number = find_code_state_with_timestamp(filtered_keylog_events_folder,dialogue_json_path,folder_of_dialogues)
	trimmed_keylog_data_path = trim_down_data_for_screenshots_further(filtered_keylog_events_folder,dictionary_of_data_for_screenshots, dialogue_number)
	take_screenshot(video_path, image_folder,trimmed_keylog_data_path, dialogue_number)
	json_of_code_states_with_cursor_detected_by_llm = process_images_in_folder(key_path, image_folder, dialogue_number, cursor_colours, model)