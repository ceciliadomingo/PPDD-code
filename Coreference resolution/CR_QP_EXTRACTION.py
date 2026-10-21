
def cursor_color_extractor(dialogue_number, cursor_color_registry):
	df = pd.read_excel(cursor_color_registry)
	# Find row where Dialogue matches dialogue_number
	cursor_colors_row = df[df['Dialogue'] == dialogue_number]
	# Get the color for speaker A (Cursor color 1) and for speaker B (Cursor color 2)
	cursor_color_A = cursor_colors_row['Cursor color 1'].values[0] if not cursor_colors_row.empty else None
	cursor_color_B = cursor_colors_row['Cursor color 2'].values[0] if not cursor_colors_row.empty else None
	return cursor_color_A, cursor_color_B

def code_and_keylog_retriever(dialogue_number, turn_id, folder_trimmed_keylog_and_code,time_start,time_end):
	time_start_seconds = convert_timestamp_to_seconds(time_start)
	time_end_seconds = convert_timestamp_to_seconds(time_end)
	# The turn id is fed from the dialogue json, so it's an integer
	# But in the files with the code state and keylog records, it's a string
	code_state = None # Initialise as none to have it in case the turn id is not found
	keylog_record = None
	for file in os.listdir(folder_trimmed_keylog_and_code):
		# CODE STATE --> Files will be like Trimmed_data_for_screenshots_032x028
		if dialogue_number in file and "Trimmed" in file:
			with open(os.path.join(folder_trimmed_keylog_and_code, file), 'r') as f:
				code_state_records_json = json.load(f)
				# Look for the code state record in whose value is between the turn start and end, both included 
				for record in code_state_records_json:
					if int(record) >= time_start_seconds and int(record) <= time_end_seconds:
						code_state = code_state_records_json[record]
				# If the no code state record is between the start and end spans, we take the latest one before that turn
				if code_state is None:
					for earlier_record in reversed(code_state_records_json): # If we iterate in reverse, the first match will be the latest one before the turn
						if int(earlier_record) < time_start_seconds:
							code_state = code_state_records_json[earlier_record]
							break
		# KEYLOG RECORDS --> Files will be like Filtered_keylogs_032x028
		elif dialogue_number in file and "Filtered" in file:
			with open(os.path.join(folder_trimmed_keylog_and_code, file), 'r') as f:
				keylog_records_json = json.load(f)
				# Look for the keylog record matching the turn id, if existing
				for record in keylog_records_json[dialogue_number]:
					if int(record) == turn_id:
						keylog_record = keylog_records_json[dialogue_number][record]
				# If the turn ID is not in the keylog records, we just leave it as None: no gestures in this turn
	return code_state, keylog_record

def get_cursor_tagged_code(dialogue_number, time_start, time_end,folder_tagged_code_states):
	for file in os.listdir(folder_tagged_code_states):
		if file.endswith(".json") and dialogue_number in file:
			with open(os.path.join(folder_tagged_code_states, file), 'r') as f:
				tagged_code_states_json = json.load(f)
				time_start_seconds = convert_timestamp_to_seconds(time_start)
				time_end_seconds = convert_timestamp_to_seconds(time_end)
				for record in tagged_code_states_json[dialogue_number]:
					if int(record) >= time_start_seconds and int(record) <= time_end_seconds:
						screenshot_data = tagged_code_states_json[dialogue_number][record]["response_text"]
						return screenshot_data
					# If the no code state record is between the start and end spans, we take the latest one before that turn
					for earlier_record in reversed(tagged_code_states_json[dialogue_number]):
						if int(earlier_record) < time_start_seconds:
							screenshot_data = tagged_code_states_json[dialogue_number][earlier_record]["response_text"]
							return screenshot_data

def mentions_extractor_from_annotations(dialogue_number, turn_id, annotations_folder):
	for file in os.listdir(annotations_folder):
		if dialogue_number in file and "_read_dictate_removed" in file:
			# Open excel
			annotations_df = pd.read_excel(os.path.join(annotations_folder, file))
			# Trim it down to only the columns: Turn ID, Mention, Mention start, Mention end, Row ID
			annotations_df_compact = annotations_df[['Turn ID', 'Mention', 'Mention start', 'Mention end', 'Row ID']]
			annotations_df_this_turn = annotations_df_compact[annotations_df_compact['Turn ID'] == turn_id]
			return annotations_df_this_turn

def dialogue_history_extractor(dialogue_json_data, turn_id, context_window):
	dialogue_history_det = []
	dialogue_history_only_transcripts = []
	# DETAILED HISTORY
	# For the plain dialogue history, we add any turn, whether silent (quiet typing) or with transcript
	for turn in dialogue_json_data["SESSION"]["TURNS"]:
		if turn["TURN_ID"] >= (turn_id - context_window) and turn["TURN_ID"] < turn_id:
			transcript_history = ""
			if "TRANSCRIPT" in turn["TURN"]:
				transcript_history = f"SPEAKER {turn['TURN']['DIARIZATION']['SPEAKER']}: {turn['TURN']['TRANSCRIPT'].replace('\n', '')}"
			keylog_history = ""
			if "KEYLOGS" in turn["TURN"]:
				for keylog_entry in turn["TURN"]["KEYLOGS"]:
					keylog_parts = keylog_entry.split(" ")
					keylog_history_abstime = keylog_parts[0]
					keylog_history_speaker = keylog_parts[2]
					keylog_history_action = keylog_parts[3]
					parts_to_add = ""
					for part in keylog_parts[4:]:
						if "nan" not in part:
							parts_to_add += part + " "
					keylog_history_details = parts_to_add.strip()
					keylog_history += f"{keylog_history_abstime}-{keylog_history_speaker}-{keylog_history_action}-{keylog_history_details} "
			code_history = ""
			if "CODE ENTRIES" in turn["TURN"]:
				for code_entry in turn["TURN"]["CODE ENTRIES"]:
					code_history += f"{code_entry['TIME']}: {code_entry['CODE']} "
			turn_key_bits = {
				"TRANSCRIPT": transcript_history,
				#"TIME_START": turn["TURN"]["TIME"]["START"],
				#"TIME_END": turn["TURN"]["TIME"]["END"],
				#"KEYLOG": keylog_history,
				"CODE": code_history
			}
			dialogue_history_det.append(turn_key_bits)
	# ONLY SPEAKER AND TRANSCRIPT
	# For the dialogue history with only transcripts, we need to skip silent turns, so the first turn in the history may actually be before turn_id - context window
	counter_for_while = 0
	for turn in reversed(dialogue_json_data["SESSION"]["TURNS"]): # Going in reverse we can always add the most relevant (recent) turn until filling the list
		if "TRANSCRIPT" in turn["TURN"] and turn["TURN_ID"] < turn_id and counter_for_while < context_window:
			transcript_speaker = turn["TURN"]["DIARIZATION"]["SPEAKER"]
			dialogue_history_only_transcripts.append(f"SPEAKER {transcript_speaker}: {turn['TURN']['TRANSCRIPT'].replace('\n', '')}")
			counter_for_while += 1
	return dialogue_history_det, dialogue_history_only_transcripts
	

def mention_tag_extractor(mentions_json, transcript):
	# Mentions_json is df with columns: Turn ID, Mention, Mention start, Mention end, Row ID
	# Extract the mention spans
	mention_starts = mentions_json['Mention start'].tolist()
	mention_ends = mentions_json['Mention end'].tolist()
	# Turning the lists into lists of tuples
	for start in mention_starts:
		mention_starts[mention_starts.index(start)] = (start, 'S')
	for end in mention_ends:
		mention_ends[mention_ends.index(end)] = (end, 'E')
	# Combine the two lists into one list of tuples, with the type of the mention (start or end) as the second element
	combined_mention_indexes = mention_starts + mention_ends
    # Sort the combined list by the index (the first element of the tuple), from last to first
	combined_mention_indexes.sort(key=lambda x: x[0], reverse=True)
    # Now we can iterate over the combined list and add the tags to the transcript
	transcript_of_the_turn_for_ev = transcript
	for index, mention_type in combined_mention_indexes:
		if mention_type == 'S':
            # Add the opening tag
			transcript_of_the_turn_for_ev = transcript_of_the_turn_for_ev[:index] + '<M>' + transcript_of_the_turn_for_ev[index:]
		elif mention_type == 'E':
            # Add the closing tag
			transcript_of_the_turn_for_ev = transcript_of_the_turn_for_ev[:index] + '</M>' + transcript_of_the_turn_for_ev[index:]
	mention_tagged_transcript = transcript_of_the_turn_for_ev
	return mention_tagged_transcript
