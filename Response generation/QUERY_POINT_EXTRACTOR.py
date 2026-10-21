# Query point extractor

# What the code does:
# Load dialogue json data
# Create latest_code variable with the state of teh code
# Create big list to store all QPs
# Iterate through json turn objects
# At each turn (i):
    # Always check if there is speaker; skip turns without it, changes implemented silently with teh keyboard will be reflected in next turn's code
    # STORE SPEAKER
    # STORE TIMESTAMPS
    # STORE LATEST CODE (global variable)
    # Create empty list to contain one QP. QP consists of list of dictionaries, each item contains info for one turn. Info is speaker, timestamps, latest_code
    # Check if the next turn is significant and has a change of speaker
    # If speaker at i+1 is the same
        # go to next iteration
    # If speaker at i+1 is different
        # Significance: if (i+1) lasts more than 1 second
            # If it doesn't (i+1<1s), check if it is at the end of the current turn or if there is overlap of 50% or more of duration of i+1
                # If i+1 is short and fully or almost fully overlapping, it's a backchannel of spoken language that we wouldn't expect in written language
                    # We omit i+1 and check i+2 as if it was i+1
                # If i+1 is short but not overlapping (or not much), it's simply a short reply, we store i and i+1 in QP list 
                # (with their info, checking if we need to update value of latest code for i+1 dicitonary)
    # We repeat this until the length of QP list = context window or a condition is reached that moves us to the next iteration of the main loop (speakers in subsequent turns being the same)
    # IF length of QP list reaches = context window, we add it to the big lsit of QPs

# Once we iterate through all the turns (when there is an index out of range)
# We iterate through QPs in big list to output each mini list as a txt file in our desired format for LLM prompting
#{"role": "user", "content": "(turn transcript) CODE STATE: (latest code)"}
#{"role": "assistant", "content": "(turn transcript) CODE STATE: (latest code)"}
#{"role": "user", "content": "(turn transcript) CODE STATE: (latest code)"}
#{"role": "assistant", "content": "(turn transcript) CODE STATE: (latest code)"}

#{"role": "user", "content": "(turn transcript) CODE STATE: (latest code)"}

# The output also includes the ground truth to make it easier to compare LLM output with GT

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# IMPORTS
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import re
import os
import json

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# FUNCTIONS FOR SEPARATING INSTRUCTIONS AND CODE
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def extract_task_instructions(code_file_string, task_instruction_folder):
    import os
    valid_instructions = []
    for task_instruction_file in os.listdir(task_instruction_folder):
        task_instruction_file_fullpath = os.path.abspath(os.path.join(task_instruction_folder, task_instruction_file))
        instruction_string = open(task_instruction_file_fullpath).read()
        if instruction_string in code_file_string:
            valid_instructions.append(instruction_string)
    longest_matching_instruction = max(valid_instructions, key=len)
    return longest_matching_instruction

def extract_code_part_of_task(code_file_string,task_instruction_folder):
    longest_matching_instruction = extract_task_instructions(code_file_string, task_instruction_folder)
    only_code = code_file_string.replace(longest_matching_instruction, "") # Replaces the instructions with blank
    return only_code

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# FUNCTION TO PARSE TIMESTAMP
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Function to convert timestamps to seconds for easy comparison
def parse_timestamp(timestamp):
    # Split the timestamp into hours, minutes, seconds, and milliseconds
    hours, minutes, seconds_millis = timestamp.split(':')
    seconds, millis = seconds_millis.split(',')

    # Convert all parts into seconds and sum them
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000
    return total_seconds

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# FUNCTION TO DEFINE WHETHER NEXT TURN IS SIGNIFICANT
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Function to check if next turn is significant:
# If the enxt turn is by the same speaker, we merge it with teh current one
# If the next turn is by a different speaker, it is only significant if there's no overlap or if it's long enough (more than 1 second)
# (if it's very short and mostly overlapping, its' a backchannel like "Uhum")
def is_next_turn_significant(next_turn_index):
    global i
    global latest_code
    global qp_list
    global latest_instructions
    latest_valid_turn_index_before_next = i
    # While the query point is not complete and we haven't checked if there's a significant next turn, keep looking at next turns
    while len(qp_list) < (context_window+1): #context + prompt
        if next_turn_index <= len(data['SESSION']['TURNS'])-1: #Do not go over the last turn
        #I use <= because last turn might still be useful as last item of qplist
            next_turn = data['SESSION']['TURNS'][next_turn_index]
            latest_valid_turn_before_next = data['SESSION']['TURNS'][latest_valid_turn_index_before_next]
            next_turn = data['SESSION']['TURNS'][next_turn_index]
            # Check SPEAKER
            try: # If turn and next_turn speakers are the same --> merge turns
                if next_turn['TURN']['DIARIZATION']['SPEAKER'] == latest_valid_turn_before_next['TURN']['DIARIZATION']['SPEAKER']:
                    try:
                        # Update latest code
                        latest_code = extract_code_part_of_task(next_turn['TURN']['CODE ENTRIES'][len(['CODE ENTRIES'])-1]['CODE'],task_instruction_folder) 
                        latest_instructions = extract_task_instructions(next_turn['TURN']['CODE ENTRIES'][len(['CODE ENTRIES'])-1]['CODE'], task_instruction_folder)
                    except IndexError:
                        pass
                    merged_turn = {
                        'speaker': next_turn['TURN']['DIARIZATION']['SPEAKER'],
                        'transcript': latest_valid_turn_before_next['TURN']['TRANSCRIPT'] + next_turn['TURN']['TRANSCRIPT'],
                        'timestamp start': latest_valid_turn_before_next['TURN']['TIME']['START'],
                        'timestamp_end': next_turn['TURN']['TIME']['END'],
                        'latest_code': latest_code
                    }
                    new_qp_list = []
                    for index in range(len(qp_list)):
                        if index != len(qp_list)-1:
                            new_qp_list.append(qp_list[index])
                        else:
                            new_qp_list.append(merged_turn)
                    qp_list = []
                    for item in new_qp_list:
                        qp_list.append(item) 
                    latest_valid_turn_index_before_next = next_turn_index
                    next_turn_index += 1
                    
                    continue
                else: # different speakers
                    # Check DURATION (more than 1 second)
                    # If next turn is LONG enough --> significant
                    if (parse_timestamp(next_turn['TURN']['TIME']['START']) - parse_timestamp(next_turn['TURN']['TIME']['END'])) > 1:
                        try:
                            # Update latest code
                            latest_code = extract_code_part_of_task(next_turn['TURN']['CODE ENTRIES'][len(['CODE ENTRIES'])-1]['CODE'],task_instruction_folder) 
                            latest_instructions = extract_task_instructions(next_turn['TURN']['CODE ENTRIES'][len(['CODE ENTRIES'])-1]['CODE'], task_instruction_folder)
                        except IndexError:
                            pass
                            speaker = next_turn['TURN']['DIARIZATION']['SPEAKER']
                        qp_list.append({
                                'speaker': speaker,
                                'transcript': next_turn['TURN']['TRANSCRIPT'],
                                'timestamp start': next_turn['TURN']['TIME']['START'],
                                'timestamp_end': next_turn['TURN']['TIME']['END'],
                                'latest_code': latest_code
                            })
                        latest_valid_turn_index_before_next =  next_turn_index
                        next_turn_index += 1
                        continue
                    # If next turn is SHORT
                    else:
                        # Check overlap percentage
                        overlap = (min(parse_timestamp(turn['TURN']['TIME']['END']), parse_timestamp(next_turn['TURN']['TIME']['END'])) - max(parse_timestamp(turn['TURN']['TIME']['START']), parse_timestamp(next_turn['TURN']['TIME']['START']))) / (parse_timestamp(next_turn['TURN']['TIME']['END']) - parse_timestamp(next_turn['TURN']['TIME']['START']))
                        # If very overlapping backchannel --> not significant, but skippable
                        if overlap >= 0.5:
                            print(f"NEXT TURN OVERLAPS TOO MUCH {next_turn_index}", file=open("Which turns overlap too much.txt", "a+"))
                            next_turn_index += 1    
                            continue # Updates value of next turn to check and goes straight to next while iteration to check it
                        # If short but not too overlapping --> significant
                        else:
                            try:
                                # Update latest code
                                latest_code = extract_code_part_of_task(next_turn['TURN']['CODE ENTRIES'][len(['CODE ENTRIES'])-1]['CODE'],task_instruction_folder) 
                                latest_instructions = extract_task_instructions(next_turn['TURN']['CODE ENTRIES'][len(['CODE ENTRIES'])-1]['CODE'], task_instruction_folder)
                            except IndexError as errorcito:
                                pass
                                speaker = next_turn['TURN']['DIARIZATION']['SPEAKER']
                            qp_list.append({
                                    'speaker': speaker,
                                    'transcript': next_turn['TURN']['TRANSCRIPT'],
                                    'timestamp start': next_turn['TURN']['TIME']['START'],
                                    'timestamp_end': next_turn['TURN']['TIME']['END'],
                                    'latest_code': latest_code,
                                    'latest_instructions': latest_instructions
                            })
                            latest_valid_turn_index_before_next =  next_turn_index
                            next_turn_index += 1
                            continue
            except KeyError: # Silent turn --> not significant, but skippable
                    next_turn_index += 1
                    continue # Updates value of next turn to check and goes straight to next while iteration to check it
        else: #If end of json
            break    

    if len(qp_list) == (context_window+1): # When we reach the end of the QP, we need to extract next-turn ground truth
        # Prevent error: next_turn_index+1 is out of range
        if (next_turn_index+1) < len(data['SESSION']['TURNS'])-1:
            ground_truth_turn = data['SESSION']['TURNS'][next_turn_index+1]
            ground_turth_turn_ID = ground_truth_turn['TURN_ID']
            # Ensure that ground truth response is different speaker:
            try: # Prevent error: 'DIARIZATION' not in ground_truth_turn['TURN']
                if next_turn['TURN']['DIARIZATION']['SPEAKER'] != ground_truth_turn['TURN']['DIARIZATION']['SPEAKER']:
                    code_changed_in_GT = False
                    try:
                        # Update latest code
                        ground_truth_code = extract_code_part_of_task(next_turn['TURN']['CODE ENTRIES'][len(['CODE ENTRIES'])-1]['CODE'],task_instruction_folder) 
                        ground_truth_instructions = extract_task_instructions(next_turn['TURN']['CODE ENTRIES'][len(['CODE ENTRIES'])-1]['CODE'], task_instruction_folder)
                        code_changed_in_GT = True
                    except IndexError:
                        pass
                    if code_changed_in_GT:
                        qp_list.append({
                                        'GT speaker': speaker,
                                        'GT transcript': "TURN ID-" + str(ground_turth_turn_ID) + "-" + ground_truth_turn['TURN']['TRANSCRIPT'],
                                        'GT timestamp start': ground_truth_turn['TURN']['TIME']['START'],
                                        'GT timestamp_end': ground_truth_turn['TURN']['TIME']['END'],
                                        'GT latest_code': ground_truth_code,
                                        'latest_instructions': ground_truth_instructions
                                    })
                    else:
                        qp_list.append({
                                        'GT speaker': speaker,
                                        'GT transcript': "TURN ID-" + str(ground_turth_turn_ID) + "-" + ground_truth_turn['TURN']['TRANSCRIPT'],
                                        'GT timestamp start': ground_truth_turn['TURN']['TIME']['START'],
                                        'GT timestamp_end': ground_truth_turn['TURN']['TIME']['END'],
                                        'GT latest_code': latest_code,
                                        'latest_instructions': latest_instructions
                                    })
                    # If the ground truth turn is silent, we need to check the next turn
            except KeyError:# Prevent error: 'DIARIZATION' not in ground_truth_turn['TURN']
                try:# Prevent error: next_turn_index+2 is out of range
                    ground_truth_turn = data['SESSION']['TURNS'][next_turn_index+2]
                    # Ensure that ground truth response is different speaker:
                    try:# Prevent error: 'DIARIZATION' not in ground_truth_turn['TURN']
                        if next_turn['TURN']['DIARIZATION']['SPEAKER'] != ground_truth_turn['TURN']['DIARIZATION']['SPEAKER']:
                            code_changed_in_GT = False
                            try:
                                # Update latest code
                                ground_truth_code = extract_code_part_of_task(next_turn['TURN']['CODE ENTRIES'][len(['CODE ENTRIES'])-1]['CODE'],task_instruction_folder) 
                                ground_truth_instructions = extract_task_instructions(next_turn['TURN']['CODE ENTRIES'][len(['CODE ENTRIES'])-1]['CODE'], task_instruction_folder)
                                code_changed_in_GT = True
                            except IndexError:
                                pass
                            if code_changed_in_GT:
                                qp_list.append({
                                                'GT speaker': speaker,
                                                'GT transcript': "TURN ID-" + str(ground_turth_turn_ID) + "-" + ground_truth_turn['TURN']['TRANSCRIPT'],
                                                'GT timestamp start': ground_truth_turn['TURN']['TIME']['START'],
                                                'GT timestamp_end': ground_truth_turn['TURN']['TIME']['END'],
                                                'GT latest_code': ground_truth_code,
                                                'latest_instructions': ground_truth_instructions
                                            })
                            else:
                                qp_list.append({
                                                'GT speaker': speaker,
                                                'GT transcript': "TURN ID-" + str(ground_turth_turn_ID) + "-" + ground_truth_turn['TURN']['TRANSCRIPT'],
                                                'GT timestamp start': ground_truth_turn['TURN']['TIME']['START'],
                                                'GT timestamp_end': ground_truth_turn['TURN']['TIME']['END'],
                                                'GT latest_code': latest_code,
                                                'latest_instructions': latest_instructions
                                            })
                    except KeyError:# Prevent error: 'DIARIZATION' not in ground_truth_turn['TURN']
                        pass
                except IndexError: # Prevent error: next_turn_index+2 is out of range
                    pass              
    return qp_list
    
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# MAIN FUNCTION TO EXTRACT QPs
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def main(dialogue_json_path, output_folder, task_instruction_folder, context_window):
	# Load json data
	with open(dialogue_json_path, 'r') as f:
		data = json.load(f)

	# Get the dialogue number for the output filenames
	file_basename = os.path.basename(f.name)
	match = re.findall(r'\d{3}', str(file_basename)) # Returns list
	dialogue_number = str(match[0])+"x"+str(match[1])
	print(dialogue_number)

	# Create global variables
	latest_code = None
	latest_instructions = None
	big_list_qps = []  # List of all QP groups

	# Iterate through json turns
	for i in range(len(data['SESSION']['TURNS'])):
		# Locate current turn
		turn = data['SESSION']['TURNS'][i]
		if 'DIARIZATION' not in turn['TURN']:  # Skip turns without a speaker
			continue
		# Obtain turn info
		speaker = turn['TURN']['DIARIZATION']['SPEAKER']
		transcript = turn['TURN']['TRANSCRIPT']
		timestamp_start = turn['TURN']['TIME']['START']
		timestamp_end = turn['TURN']['TIME']['END']
		try:
			latest_code = extract_code_part_of_task(turn['TURN']['CODE ENTRIES'][len(['CODE ENTRIES'])-1]['CODE'],task_instruction_folder)  # Store latest code (if it exists)
			latest_instructions = extract_task_instructions(turn['TURN']['CODE ENTRIES'][len(['CODE ENTRIES'])-1]['CODE'], task_instruction_folder)
		except IndexError:
			pass
			
		# Create a list for one QP
		qp_list = [{'speaker': speaker, 'transcript': transcript, 'timestamp start':timestamp_start, 'timestamp_end':timestamp_end, 'latest_code':latest_code}]
		
		# Check next turn(s) till QP is complete
		next_turn_index = i + 1
		if next_turn_index <= (len(data['SESSION']['TURNS'])-context_window):
		# There have to be at least context_window turns left after current
			is_next_turn_significant(next_turn_index)

		# Store the QP list in the big list if it reaches enough turns (context window + 2) (e.g., 9 = 8+1) Context + prompt + ground truth
		if len(qp_list) == (context_window + 2): #CHANGED FROM +1 to +2 TO ACCOUNT FOR GT
			big_list_qps.append(qp_list)
		
	print("iterated through json")

	# Add task instructions to each QP. Use enumerate to add instructions from next if current has no code
	for index, qp_list in enumerate(big_list_qps):
			latest_instructions_in_qp = qp_list[len(qp_list)-1]['latest_instructions']
			next_qp_to_find_instructions = index + 1 # Before while loop to avoid getting stuck; this is to find next QP that has code
			while latest_instructions_in_qp is None or latest_instructions_in_qp == "" or latest_instructions_in_qp == "\n" or latest_instructions_in_qp == "\n\n":   
				latest_instructions_in_qp = big_list_qps[next_qp_to_find_instructions][len(big_list_qps[next_qp_to_find_instructions])-1]['latest_instructions']
				next_qp_to_find_instructions += 1
				if next_qp_to_find_instructions > 40:
					print("Stuck in while loop")
			#print(f'Length of latest_code_in_qp {len(latest_instructions_in_qp)} and content: {latest_instructions_in_qp}')
			qp_list. append(latest_instructions_in_qp)


	# Generate txt files with query points
	for idx, qp in enumerate(big_list_qps):
		if not os.path.exists(os.path.join(output_folder, f'{dialogue_number}-CONTEXT{context_window}-with GT')):
			os.makedirs(os.path.join(output_folder, f'{dialogue_number}-CONTEXT{context_window}-with GT'))
		with open(os.path.join(output_folder, f'{dialogue_number}-CONTEXT{context_window}-with GT', f'{dialogue_number}-QP-CONTEXT{context_window}-with GT_{idx}.txt'), 'w+') as f:
			for qp_index, turno in enumerate(qp):
				if qp_index != len(qp)-1: # If it's not the last index; that one would have no response in GT, so we won't use it to prompt
					# Separate ground truth response
					if 'GT transcript' in str(turno):
						GT_transcript = turno["GT transcript"].replace('\\', '\\\\')
						GT_transcript = GT_transcript.replace('"', '\\"')
						GT_transcript = GT_transcript.replace("\n", '\\n')
						GT_transcript = GT_transcript.replace('\t', '\\t')
						GT_transcript = GT_transcript.replace('\r', '\\r')
						GT_transcript = GT_transcript.replace('%', '%%')
						GT_latest_code = turno["GT latest_code"]
						if GT_latest_code is not None and GT_latest_code != "" and GT_latest_code != "\n" and GT_latest_code != "\n\n":
							GT_latest_code = GT_latest_code.replace('\\', '\\\\')
							GT_latest_code = GT_latest_code.replace("\n", '\\n')
							GT_latest_code = GT_latest_code.replace('"', '\\"')
							GT_latest_code = GT_latest_code.replace('\t', '\\t')
							GT_latest_code = GT_latest_code.replace('\r', '\\r')
							GT_latest_code = GT_latest_code.replace('%', '%%')
							gt_content = f'{{"role": "GROUND TRUTH", "content": "{GT_transcript} CODE STATE: {GT_latest_code}"}}\n'
							f.write(gt_content)
						if GT_latest_code is None or GT_latest_code == "" or GT_latest_code == "\n" or GT_latest_code == "\n\n":
							gt_content = f'{{"role": "GROUND TRUTH", "content": "{GT_transcript}"}}\n'
							f.write(gt_content)
					else:
						# Alternate between 'user' and 'assistant' based on the index of the turn
						role = 'user' if qp_index % 2 == 0 else 'assistant'
						# Escape all the fishy characters that might appear in the transcript or code
						transcript = turno["transcript"].replace('\\', '\\\\')
						transcript = transcript.replace('"', '\\"')
						transcript = transcript.replace("\n", '\\n')
						transcript = transcript.replace('\t', '\\t')
						transcript = transcript.replace('\r', '\\r')
						transcript = transcript.replace('%', '%%')
						latest_code = turno["latest_code"]

						if latest_code is not None and latest_code != "" and latest_code != "\n" and latest_code != "\n\n":
							latest_code = latest_code.replace('\\', '\\\\')
							latest_code = latest_code.replace("\n", '\\n')
							latest_code = latest_code.replace('"', '\\"')
							latest_code = latest_code.replace('\t', '\\t')
							latest_code = latest_code.replace('\r', '\\r')
							latest_code = latest_code.replace('%', '%%')
							content = f'{{"role": "{role}", "content": "{transcript} CODE STATE: {latest_code}"}}\n'
							f.write(content)

						if latest_code is None or latest_code == "" or latest_code == "\n" or latest_code == "\n\n":
							content = f'{{"role": "{role}", "content": "{transcript}"}}\n'
							f.write(content)

				if qp_index == len(qp)-1:
					turno = turno.replace('\\', '\\\\')
					turno = turno.replace("\n", '\\n')
					turno = turno.replace('"', '\\"')
					turno = turno.replace('\t', '\\t')
					turno = turno.replace('\r', '\\r')
					turno = turno.replace('%', '%%')
					content = f'{{"task_instructions": "{turno}"}}'
					f.write(content)
	print("finished")


if __name__ == "__main__":
	task_instruction_folder = 'folder/with/txt/files/with/instructions'
	context_window = 50 # Replace with desired context window
	dialogue_json_path = 'path/to/dialogue/json' # Replace with path to json for the dialogue being used
	output_folder = 'path/to/output/folder'
	main(dialogue_json_path, output_folder, task_instruction_folder, context_window)