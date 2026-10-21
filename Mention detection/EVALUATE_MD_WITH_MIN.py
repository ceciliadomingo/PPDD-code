

# Mention detection evaluation using minimum spans
def remove_duplicates_preserve_order(seq):
    seen = set()
    result = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

def obtain_nucleus(mention, model_for_min_spans):
	if type(mention) == int:
		nucleus = str(mention)
	elif mention == "" or mention == " ":
		nucleus = ""
	else:
		mention_doc = model_for_min_spans(mention)
		try:	
			nucleus = mention_doc[:].root
		except Exception as e:
			print(f"Error processing mention '{mention}': {e}")
	return nucleus


def extract_mins_from_tagged_text(tagged_string, turn_ID, model_for_min_spans):
	import re
	mention_tag_pattern = re.compile(r'<M>(.*?)</M>') # Using .*? for non-greedy matching to get only one mention at a time
	tagged_chunks_list = []
	index_including_tags = 0
	index_without_tags = 0
	# Iterate through all the tagged-string indexes looking for mentions 
	while index_including_tags < len(tagged_string):
		# Start at the current value of teh index at look for the closest mention
		match = mention_tag_pattern.search(tagged_string, index_including_tags) # Searching starting at the latest value of index i, 
		# though it looks at the whole string and returns the first match
		if not match:
			break
		text_before_match = tagged_string[index_including_tags:match.start()]
		# Extract the start index by checking the length of the text before the match after removing the </?M> tags
		index_without_tags += len(re.sub(fr"<\/?M>", "",text_before_match)) # Regex with ? to match closing / or no /
		mention = match.group(1)
		mention = mention.replace("<M>","").replace("</M>","") # To deal with nested mentions
		min_span = obtain_nucleus(mention, model_for_min_spans)
		# Find the index where the min_span begins and add that to index_without_tags
		mins_span_pattern = re.compile(re.escape(str(min_span)))
		match_inside_mention = mins_span_pattern.search(mention) # Find where the nucleus is in the mention
		text_before_min = mention[:match_inside_mention.start()]
		start_index_of_min = index_without_tags + len(text_before_min)
		end_index_of_min = start_index_of_min + len(min_span)
		tagged_chunks_list.append((min_span, int(turn_ID), start_index_of_min, end_index_of_min))

		# Now we update the indexes for the next mention
		index_including_tags = match.end()
		index_without_tags += len(mention)
	#if len(tagged_chunks_list) == 0:
		#print(f"Warning: No mentions found in tagged string for turn ID {turn_ID}. Tagged string: {tagged_string}")
	return tagged_chunks_list

def convert_gt_to_min(gt_mention_json_data):
	dict_of_speaker_mins = {}
	list_of_task_mins = []
	list_of_single_mins = []
	for speaker in gt_mention_json_data['CHAINS']['LINKED MENTIONS']['SPEAKER MENTIONS']:
		list_for_this_speaker = []
		for mention in gt_mention_json_data['CHAINS']['LINKED MENTIONS']['SPEAKER MENTIONS'][speaker]:
			# Convert mention to min
			min_span = obtain_nucleus(mention["Mention"])
			mins_span_pattern = re.compile(str(min_span))
			if type(mention["Mention"]) != str:
				match_inside_mention = mins_span_pattern.search(str(mention["Mention"])) # Find where the nucleus is in the mention
				text_before_min = str(mention["Mention"])[:match_inside_mention.start()]
			else:
				match_inside_mention = mins_span_pattern.search(mention["Mention"]) # Find where the nucleus is in the mention
				text_before_min = mention["Mention"][:match_inside_mention.start()]
			start_index_of_min = mention["Mention start"] + len(text_before_min)
			end_index_of_min = start_index_of_min + len(min_span)
			dict_for_this_mention = {"Turn ID": mention["Turn ID"],
						"Mention": min_span,
						"Mention start": start_index_of_min ,
						"Mention end": end_index_of_min,
						"Row ID": mention["Row ID"]}
			list_for_this_speaker.append(dict_for_this_mention)
		dict_of_speaker_mins[speaker] = list_for_this_speaker
	for index, chain in enumerate(gt_mention_json_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS']):
		list_of_mentions_in_this_chain = []
		for mention in gt_mention_json_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS'][index]['MENTIONS']: 
			min_span = obtain_nucleus(mention["MENTION"])
			mins_span_pattern = re.compile(str(min_span))
			if type(mention["MENTION"]) != str:
				match_inside_mention = mins_span_pattern.search(str(mention["MENTION"]))
				text_before_min = str(mention["MENTION"])[:match_inside_mention.start()]
			else:
				match_inside_mention = mins_span_pattern.search(mention["MENTION"]) # Find where the nucleus is in the mention
				text_before_min = mention["MENTION"][:match_inside_mention.start()]
			start_index_of_min = mention["SPAN"]["START"] + len(text_before_min)
			end_index_of_min = start_index_of_min + len(min_span)                               
			dict_of_this_mention = {"MENTION": mention["MENTION"],
							"TURN ID": mention["TURN ID"],
							"SPAN": {
								"START": start_index_of_min,
								"END": end_index_of_min
								},
							"MENTION ID": mention["MENTION ID"]
							}
			list_of_mentions_in_this_chain.append(dict_of_this_mention)
		dict_of_this_chain = {"CHAIN ID": chain["CHAIN ID"],
								"MENTIONS": list_of_mentions_in_this_chain
							}
		list_of_task_mins.append(dict_of_this_chain)
	for singleton in gt_mention_json_data['CHAINS']['SINGLE MENTIONS']:
		min_span = obtain_nucleus(singleton["MENTION"])
		mins_span_pattern = re.compile(str(min_span))
		if type(mention["MENTION"]) != str:
			match_inside_mention = mins_span_pattern.search(str(singleton["MENTION"]))
			text_before_min = str(mention["MENTION"])[:match_inside_mention.start()]
		else:
			match_inside_mention = mins_span_pattern.search(singleton["MENTION"]) # Find where the nucleus is in the mention
			if match_inside_mention == None:
				print(f"Mention: {singleton["MENTION"]}, MIN: {min_span}")
			text_before_min = singleton["MENTION"][:match_inside_mention.start()]
		start_index_of_min = singleton["SPAN"]["START"] + len(text_before_min)
		end_index_of_min = start_index_of_min + len(min_span)                               
		dict_of_this_mention = {"MENTION": singleton["MENTION"],
							"TURN ID": singleton["TURN ID"],
							"SPAN": {
								"START": start_index_of_min,
								"END": end_index_of_min
								},
							"MENTION ID": singleton["MENTION ID"]
							}
		list_of_single_mins.append(dict_of_this_mention)
	gt_min_dict = {"CHAINS": 
					{"LINKED MENTIONS": {
						"SPEAKER MENTIONS": dict_of_speaker_mins,
						"TASK MENTIONS": list_of_task_mins
					},
					"SINGLE MENTIONS": list_of_single_mins
					}
					}
	return gt_min_dict


def evaluate_mention_detection_with_min(output_json_file, dialogue_number, model_for_min_spans, list_of_GT_files):
	print(f"Evaluating dialogue {dialogue_number} in file {output_json_file}")

	# Input dialogue files
	with open(list_of_GT_files, 'r', encoding='utf-8') as file:
		content = file.read()
	GT_annotations = ast.literal_eval(content)  # Load the list of GT files as a list of tuples

	# Necessary values for metrics
	true_positives = 0
	true_positives_ids = defaultdict(list) # Using defaultdict to store lists of IDs for each dialogue
	false_positives = 0
	false_positives_with_indexes = defaultdict(dict)
	all_positives = 0 # :)
	all_positives_with_indexes = defaultdict(dict) # :)
	false_negatives = 0
	false_negatives_ids = defaultdict(list) # Using defaultdict to store lists of IDs for each dialogue
	turns_included_in_evaluation = defaultdict(list) # To keep track of turns included in the evaluation for each dialogue, if we don't use whole dialogues

	# Load the output json file and extract MINs --> all positives
	with open(output_json_file, 'r', encoding='utf-8') as f:
		output_data = json.load(f)
	for dialogue in output_data:
		mins_in_this_dialogue = []
		for turn_ID in output_data[dialogue]:
			turns_included_in_evaluation[dialogue].append(int(turn_ID))  # Keep track of the turns included in the evaluation for this dialogue
			tagged_string = output_data[dialogue][turn_ID]
			mins = extract_mins_from_tagged_text(tagged_string, turn_ID, model_for_min_spans)
			all_positives += len(mins)
			mins_in_this_dialogue.extend(mins)
		dialogue_with_x = dialogue.replace('&', 'x').replace('X', 'x').replace('_', 'x') # To match the format in the GT files
		all_positives_with_indexes[dialogue_with_x] = mins_in_this_dialogue

	# Now we compare against GT --> true positives, false positives
	for file_pair in GT_annotations:
		# The first file is the json
		# We only look at the GT file that matches the dialogue number of the output file
		if dialogue_number[0:3] in file_pair[0] and dialogue_number[4:] in file_pair[0]:
			with open(file_pair[0], 'r', encoding='utf-8') as f:
				GT_data = json.load(f)
			# Convert the GT data to min
			gt_min_data = convert_gt_to_min(GT_data)
			dialogue_number_regex = re.compile(r'(\d{3})[xX&](\d{3})')  # Assuming dialogue numbers are in the format '035x013'
			GT_dialogue_number = re.search(dialogue_number_regex, file_pair[0]).group(0)  # Extract the dialogue number from the file name
			# Iterate through all mentions dictionary
			for dialogue_in_all_positives_dict in all_positives_with_indexes:
				false_positives_of_this_dialogue_list = []
				# Find the dialogue number that matches, obviating the linking symbol [xX&] --> in this case there's only one, it will match
				if dialogue_in_all_positives_dict[0:3] == GT_dialogue_number[0:3] and dialogue_in_all_positives_dict[4:7] == GT_dialogue_number[4:7]:
					# Go through each output mention
					for mention_in_all_positives, turn_ID, start_index, end_index in all_positives_with_indexes[dialogue_with_x]:
						# Check if the mention exists in the GT data
						found_in_GT = False
						# Check if it's in the speaker mentions
						for speaker in gt_min_data['CHAINS']['LINKED MENTIONS']['SPEAKER MENTIONS']:
							if found_in_GT == False:
								for mention in gt_min_data['CHAINS']['LINKED MENTIONS']['SPEAKER MENTIONS'][speaker]:
									if mention['Turn ID'] == turn_ID and mention['Mention start'] == start_index and mention['Mention end'] == end_index:
										true_positives += 1
										true_positives_ids[dialogue_with_x].append(mention['Row ID'])
										found_in_GT = True
										break # Found a match, no need to check other GT mentions
						# Check if it's in the task mentions
						if found_in_GT == False:
							for index, chain in enumerate(gt_min_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS']):
								if found_in_GT == False:
									for mention in gt_min_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS'][index]['MENTIONS']:                                
										if mention['TURN ID'] == turn_ID and mention['SPAN']['START'] == start_index and mention['SPAN']['END'] == end_index:
											true_positives += 1
											true_positives_ids[dialogue_with_x].append(mention['MENTION ID'])
											found_in_GT = True
											break # Found a match, no need to check other GT mentions
						# Check if it's in the single mentions
						if found_in_GT == False:
							for mention in gt_min_data['CHAINS']['SINGLE MENTIONS']:
								if mention['TURN ID'] == turn_ID and mention['SPAN']['START'] == start_index and mention['SPAN']['END'] == end_index:
									true_positives += 1
									true_positives_ids[dialogue_with_x].append(mention['MENTION ID'])
									found_in_GT = True
									break
						# If the mention was not found in GT, it's a false positive
						if found_in_GT == False:
							false_positives += 1
							false_positives_of_this_dialogue_list.append((mention_in_all_positives, turn_ID, start_index, end_index))
					# After going through all the mentions in the output, we store the false positives for this dialogue 
					# (inside the if loop not to have blank lists for not-matching dialogues)
					false_positives_with_indexes[dialogue_with_x] = false_positives_of_this_dialogue_list
		
			# Now we look for false negatives
			# Now I convert the GT min data to a set for easier comparison with the PRED data  
			list_of_all_gt_mins = []      
			for speaker in gt_min_data['CHAINS']['LINKED MENTIONS']['SPEAKER MENTIONS']:
				for min_span in gt_min_data['CHAINS']['LINKED MENTIONS']['SPEAKER MENTIONS'][speaker]:
					list_of_all_gt_mins.append((min_span["Mention"], min_span['Turn ID'], min_span['Mention start'], min_span['Mention end']))
				for index, chain in enumerate(gt_min_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS']):
					for min_span in gt_min_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS'][index]['MENTIONS']:
						list_of_all_gt_mins.append((min_span["MENTION"], min_span['TURN ID'], min_span['SPAN']['START'], min_span['SPAN']['END'])) 
				for min_span in gt_min_data['CHAINS']['SINGLE MENTIONS']:
					list_of_all_gt_mins.append((min_span["MENTION"], min_span['TURN ID'], min_span['SPAN']['START'], min_span['SPAN']['END']))
			# Now I compare the intersection between GT and PRED. Anything in GT and not in PRED is FN
			unique_gt_mins = remove_duplicates_preserve_order(list_of_all_gt_mins)
			false_negatives_ids[dialogue_with_x] = list(set(unique_gt_mins) - set(all_positives_with_indexes[dialogue_with_x])) 
			false_negatives = len(false_negatives_ids[dialogue_with_x])              

			precision = true_positives / all_positives if all_positives > 0 else 0
			recall = true_positives / len(set(unique_gt_mins))#(true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
			print(f"Precision: {precision}, Recall: {recall}")
			f1_score = (2 * (precision * recall)) / (precision + recall) if (precision + recall) > 0 else 0
			return precision, recall, f1_score

def evaluate_whole_experiment(folder, model_shorthand, approach_shorthand, evaluation_folder, model_for_min_spans, list_of_GT_files):
	approach = f"{approach_shorthand}-{model_shorthand}"
	# Create df to store results
	results_df = pd.DataFrame(columns=["Approach", "Dialogue", "Precision", "Recall", "F1 Score"])
	dialogue_number_regex = re.compile(r'(\d{3})[xX&](\d{3})')  # Assuming dialogue numbers are in the format '035x013'
	for file in os.listdir(folder):
		if approach in file and "CLEANED" in file and "_3_FS" in file:
			dialogue_number = re.search(dialogue_number_regex, file).group(0)  # Extract the dialogue number from the file name
			precision, recall, f1_score = evaluate_mention_detection_with_min(os.path.join(folder, file), dialogue_number, model_for_min_spans, list_of_GT_files)
			# Append results to df
			results_df.loc[len(results_df)] = {"Approach": approach, "Dialogue": dialogue_number, "Precision": precision, "Recall": recall, "F1 Score": f1_score}
	# Save the df to Excel
	results_df.to_excel(os.path.join(evaluation_folder, f'MD_with_heads_as_MIN_{approach}_3FS_CLEANED.xlsx'), index=False)
	return print(f"Results saved to {os.path.join(evaluation_folder, f'MD_with_heads_as_MIN_{approach}_3FS_CLEANED.xlsx')}")
