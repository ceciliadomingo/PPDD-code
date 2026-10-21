# Functions to convert the mentions Excel file into a JSON file of mentions and add information about the code referents
# ---------------------------------------------------------------------------
# FUNCTIONS TO ADD INFORMATION ABOUT THE CODE REFERENT OF EACH MENTION
# ---------------------------------------------------------------------------

# Function to convert code file timestamps to relative when that information is not available
def make_timestamp_relative(timestamp_to_convert, dialogue_data): #starting_point is a string in the format '13:37:40,000'
    # Find a random code file to extract the relative and absolute timestamp relation
    for entry in dialogue_data['SESSION']['TURNS']:
        if len(entry['TURN']['CODE ENTRIES']) > 0:
            for code_entry in entry['TURN']['CODE ENTRIES']:
                #"00:00:44,000"
                code_time_relative_datetime = datetime.strptime(code_entry['TIME'], '%H:%M:%S,%f')
                # Parse the relative time as a timedelta (not a datetime), because it is missing year, month, day
                code_time_relative_timedelta = timedelta(hours=code_time_relative_datetime.hour, minutes=code_time_relative_datetime.minute, 
                                                         seconds=code_time_relative_datetime.second, microseconds=code_time_relative_datetime.microsecond)

                #"20240326190052" from "24_20240326190054"
                code_time_absolute_datetime = datetime.strptime(code_entry['FILE'].split("_")[1], '%Y%m%d%H%M%S')
                code_time_absolute_timedelta = timedelta(hours=code_time_absolute_datetime.hour, minutes=code_time_absolute_datetime.minute,
                                                         seconds=code_time_absolute_datetime.second, microseconds=code_time_absolute_datetime.microsecond)

    # Calculate the difference
    difference = code_time_absolute_timedelta - code_time_relative_timedelta
    # Convert the timestamp to convert to a datetime to be able to add the difference
    #print(f"Code time relative: {code_time_relative_datetime}, Code time absolute: {code_time_absolute_datetime}")
    #print(f"Difference: {difference}")
    try:
        timestamp_to_convert_datetime = datetime.strptime(timestamp_to_convert.split("_")[1].strip(".py"), '%Y%m%d%H%M%S')
    except IndexError:
        # If the timestamp_to_convert is not in the expected format, raise an error
        raise ValueError(f"Timestamp to convert {timestamp_to_convert} is not in the expected format '24_20240326190054' or '20240326190052'. Please check the code file name.")
    timestamp_to_convert_timedelta = timedelta(hours=timestamp_to_convert_datetime.hour, minutes=timestamp_to_convert_datetime.minute,
                                                seconds=timestamp_to_convert_datetime.second, microseconds=timestamp_to_convert_datetime.microsecond)
    converted_timestamp = timestamp_to_convert_timedelta + difference
    # Converted timestamp is in annoying timedelta format of the type "1 day, 12:04:09", so we'll remove the days
    # Only get the time portion of the timedelta (within a 24-hour window)
    seconds_in_day = converted_timestamp.seconds  #  gives you just the seconds since the last full day, so it removes the "1 day"
    hours = seconds_in_day // 3600
    minutes = (seconds_in_day % 3600) // 60
    seconds = seconds_in_day % 60
    microseconds = converted_timestamp.microseconds
    converted_timestamp_string = f"{hours:02}:{minutes:02}:{seconds:02},{microseconds:06}"
    #print(f"Converted timestamp: {converted_timestamp}, as string: {converted_timestamp_string}")
    return converted_timestamp_string

# Function to see if the referent code file is in a timestamp after the turn end time
# This would mean that the speakers mentioned code that had not yet been written
def is_file_in_future(row, dialogue_data):
    turn_id = row['Turn ID']
    for entry in dialogue_data['SESSION']['TURNS']:
        if entry['TURN_ID'] == turn_id:
            #"00:00:26,366"
            turn_end = entry['TURN']['TIME']['END']
            turn_end_datetime = datetime.strptime(turn_end, '%H:%M:%S,%f')
    # ------------------------------------------------
    # MENTION NOT IN CODE FILE
    if row['Code File'] == "Not in file" or row['Code File'] == "Terminal": # Cases where the mention refers to code not in file (terminal, inner workings, etc.)
        return "Mention not in file"
    # ------------------------------------------------
    # FINDING CODE FILE TIMESTAMP
    if pd.notna(row['Code File']) and row['Code File'] != "Not in file" and row['Code File'] != "Terminal": # Cases where the mention refers to code in a file
        # Even though filenames are timestamps, those are absolute timestamps, whereas the turn timestamps are relative to the start of the session
        # So we use the relative timestamps from "TIME" in the code entry
        code_file = row['Code File']
        if "*" in code_file:
            raise ValueError(f"Code file {code_file} contains an asterisk, which is not allowed. Please check the code file name.")
        file_match = False
        for entry in dialogue_data['SESSION']['TURNS']:
            if len(entry['TURN']['CODE ENTRIES']) > 0:
                for code_entry in entry['TURN']['CODE ENTRIES']:
                    code_time_datetime = datetime.strptime(code_entry['TIME'], '%H:%M:%S,%f')
                    if code_entry['FILE'] == code_file:
                        file_match = True
                        if code_time_datetime > turn_end_datetime:
                            # If the time difference between the code referent file and the turn end is less than 2 seconds,
                            # we consider that to not be in the future, as it cna simply be a delay in the file saving process
                            if (code_time_datetime-turn_end_datetime).total_seconds() < 2:
                                return "Almost"
                                #return f"False SMALL DIFF {code_time_datetime-turn_end_datetime}, code time is after turn end: {code_time_datetime} > {turn_end_datetime}"
                            elif (code_time_datetime-turn_end_datetime).total_seconds() >= 2:
                                return "Yes"
                                #return f"True {code_time_datetime-turn_end_datetime}, code time is after turn end: {code_time_datetime} > {turn_end_datetime}"
                        elif code_time_datetime <= turn_end_datetime:
                            return "No"
                            #return f"False {turn_end_datetime-code_time_datetime}, code time is before turn end: {code_time_datetime} <= {turn_end_datetime}"
                        else:
                            return "Filematch but datetime error"
        # -----------------------------------------
        # CODE FILE NOT FOUND IN DIALOGUE JSON
        # We convert the code file into a relative timestamp directly instead of finding it in dialogue json
        if not file_match:
            code_time_extracted_manually = make_timestamp_relative(code_file, dialogue_data)
            code_time_extracted_manually = datetime.strptime(code_time_extracted_manually, '%H:%M:%S,%f')
            if code_time_extracted_manually > turn_end_datetime:
                # If the time difference between the code referent file and the turn end is less than 2 seconds,
                # we consider that to not be in the future, as it cna simply be a delay in the file saving process
                if (code_time_extracted_manually-turn_end_datetime).total_seconds() < 2:
                    return "Almost"
                elif (code_time_extracted_manually-turn_end_datetime).total_seconds() >= 2:
                    return "Yes"
            elif code_time_extracted_manually <= turn_end_datetime:
                return "No"
            else:
                return "No file match and also datetime error"
    # ------------------------------------------------
    # CODE TYPE NOT CODE
    else:
        return "NO CODE REFERENT" # Cases where the mention does not refer to code

# -----------------------------------------------------------
# MAIN FUNCTION
# -----------------------------------------------------------
                      
# Function to convert the spans of the code referent into a readable referent like "my_variable" instead of just line numbers and indices           
def extract_visible_form(row, dialogue_json):
    # Initialise the visible form with an outrageous valuie for debugging purposes
    visible_form = "ERROR EXTRACTING VISIBLE FORM"
    code_file = row['Code File']
    if code_file == "Not in file":
        visible_form =  "Not in file"
    elif code_file == "Terminal":
        visible_form =  "Terminal"
    elif pd.isna(code_file) or code_file == "":
        visible_form = "NO CODE REFERENT"
    elif pd.notna(code_file) and code_file != "Not in file" and code_file != "Terminal":
        if ".py" not in code_file:
            code_file_with_extension = code_file + ".py"
        else:
            code_file_with_extension = code_file
        # Extract the workfolder from the dialogue json
        workfolder = os.path.dirname(dialogue_json)
        # Explore the workfolder to find the code file
        python_files_abspaths = [os.path.abspath(os.path.join(dirpath, file))
                        for dirpath, dirnames, filenames in os.walk(workfolder, topdown=True)
                        for file in filenames if file.endswith(".py")]
        for abspath in python_files_abspaths:
            # Extract the file name from the absolute path
            file = os.path.basename(abspath)
            if file == code_file_with_extension:
                # Read the code file
                with open(abspath, 'r', encoding='utf-8') as f:
                    code_content = f.read()
                # Extract the visible form based on the mention span
                # First check that the content is in string format
                if pd.notna(row['Code Span Start']) and pd.notna(row['Code Span End']): 
                    if type(row['Code Span Start']) is not str or type(row['Code Span End']) is not str:
                        raise ValueError(f"Code Span Start or End for mention {row['Mention']} with ID {row['Row ID']} is not a string. Please check the Excel file.")
                    start_row = int(row['Code Span Start'].split('*')[0]) - 1  # Convert to zero-based index
                    start_index = int(row['Code Span Start'].split('*')[1]) - 1  # Convert to zero-based index
                    end_row = int(row['Code Span End'].split('*')[0]) - 1  # Convert to zero-based index
                    end_index = int(row['Code Span End'].split('*')[1]) - 1  # Convert to zero-based index
                else: # If the mention refers to the whole file, the anntoators may have forgotten to fill the spans
                    start_row = 0
                    start_index = 0
                    end_row = len(code_content.splitlines()) - 1
                    end_index = len(code_content.splitlines()[-1]) - 1
                visible_form = []
                for index, line in enumerate(code_content.splitlines()):
                    if index == start_row:
                        # If the referent spans only one line:
                        if start_row == end_row:
                            # If the referent is in a single line, get the part of the line from the start index to the end index
                            visible_form.append(line[start_index:end_index])
                        # If the referent spans several lines:
                        elif start_row < end_row:
                            # Get the part of the line from the start index to the end of the line
                            visible_form.append(line[start_index:])
                    elif index > start_row and index < end_row:
                        # Get the whole line
                        visible_form.append(line)
                    elif index == end_row and start_row < end_row:
                        # Get the part of the line from the start of the line to the end index
                        visible_form.append(line[:end_index])
                visible_form = '\n'.join(visible_form).strip()
                #print(f"{row['Mention']} has the form {visible_form} in file {code_file}")
    return visible_form

# Main function to create the JSON of mentions (not yet linked in coreference chains) from the mentions Excel file
def create_mentions_json(excel_file, dialogue_json, dialogue_number, output_log):
    # Read the Excel file
    df = pd.read_excel(excel_file)

    # Initialise lists of mentions
    linked_mentions = []
    single_mentions = []

    # Iterate through the DataFrame to assign speakers based on the Turn ID and the dialogue json
    with open(dialogue_json, 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    #Add Speaker column to DataFrame
    df['Speaker'] = None
    for index, row in df.iterrows():
        turn_id = row['Turn ID']
        # Find the speaker in the dialogue data
        for entry in dialogue_data['SESSION']['TURNS']:
            if entry['TURN_ID'] == turn_id:
                try:
                    speaker = entry['TURN']['DIARIZATION']['SPEAKER']
                except KeyError:
                    print(f"DIARIZATION key not found in turn {turn_id} for dialogue {dialogue_number}")
                df.at[index, 'Speaker'] = speaker

    # Iterate through the DataFrame adding all mentions
    for index, row in df.iterrows():
        mention_dict = {
            "MENTION ID": row['Row ID'],
            "MENTION":row['Mention'],
			"TURN ID":row['Turn ID'],
			"SPAN":{
				"START":row['Mention start'],
				"END":row['Mention end'],
			},
			"SPEAKER":row['Speaker'],
			"MULTIMODALITY":row['Multimodality'],
			"LINGUISTIC FORM":row['Mention form'],
			"GRAMAMTICAL NUMBER":row['Mention grammatical number'],
			"PART OF INCOMPLETE":row['Incomplete'],
            "CATAPHORA": False,
            "FIRST MENTION": True,
			"CODE TYPE":row['Code Type'],
			"CODE REFERENT":{
				"FILE": row['Code File'],
				"IS FILE IN THE FUTURE":is_file_in_future(row, dialogue_data),
				"SPAN":{
					"START":row['Code Span Start'],
					"END":row['Code Span End'],
				},
				"VISIBLE FORM":extract_visible_form(row, dialogue_json)
            }
        }
        single_mentions.append(mention_dict)
    # Create json file
    json_structure = {
        "CHAINS":{
            "LINKED MENTIONS": linked_mentions,
            "SINGLE MENTIONS": single_mentions
        }
    }
    # Write the json file
    json_filename = dialogue_number + "_06_mentions.json"
    json_filepath = os.path.join(os.path.dirname(excel_file), json_filename)
    with open(json_filepath, 'w', encoding='utf-8') as json_file:
        json.dump(json_structure, json_file, indent=4, ensure_ascii=False)
    return json_filepath
