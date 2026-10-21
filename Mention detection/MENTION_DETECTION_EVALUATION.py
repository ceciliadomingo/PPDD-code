# Mention detection evaluation

def extract_mentions_from_tagged_text(tagged_string, turn_ID):
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
        end_index_of_mention = index_without_tags + len(mention)
        tagged_chunks_list.append((mention, int(turn_ID), index_without_tags, end_index_of_mention))

        # Now we update the indexes for the next mention
        index_including_tags = match.end()
        index_without_tags += len(mention)
    #if len(tagged_chunks_list) == 0:
        #print(f"Warning: No mentions found in tagged string for turn ID {turn_ID}. Tagged string: {tagged_string}")
    return tagged_chunks_list

def evaluate_mention_detection(list_of_GT_files,output_json_file):

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

    # Load one output json file and extract mentions --> all positives
    with open(output_json_file, 'r', encoding='utf-8') as f:
        output_data = json.load(f)
    for dialogue in output_data:
        mentions_in_this_dialogue = []
        for turn_ID in output_data[dialogue]:
            turns_included_in_evaluation[dialogue].append(int(turn_ID))  # Keep track of the turns included in the evaluation for this dialogue
            tagged_string = output_data[dialogue][turn_ID]
            mentions = extract_mentions_from_tagged_text(tagged_string, turn_ID)
            all_positives += len(mentions)
            mentions_in_this_dialogue.extend(mentions)
        all_positives_with_indexes[dialogue] = mentions_in_this_dialogue

    # Now we compare against GT --> true positives, false positives
    for file_pair in GT_annotations:
        # The first file is the json
        with open(file_pair[0], 'r', encoding='utf-8') as f:
            GT_data = json.load(f)
        dialogue_number_regex = re.compile(r'(\d{3})[xX&](\d{3})')  # Assuming dialogue numbers are in the format '035x013'
        GT_dialogue_number = re.search(dialogue_number_regex, file_pair[0]).group(0)  # Extract the dialogue number from the file name
        # Iterate through all mentions dictionary
        for dialogue_in_all_positives_dict in all_positives_with_indexes:
            false_positives_of_this_dialogue_list = []
            # Find the dialogue number that matches, obviating the linking symbol [xX&]
            if dialogue_in_all_positives_dict[0:3] == GT_dialogue_number[0:3] and dialogue_in_all_positives_dict[4:7] == GT_dialogue_number[4:7]:
                # Go through each output mention
                for mention_in_all_positives, turn_ID, start_index, end_index in all_positives_with_indexes[dialogue]:
                    # Check if the mention exists in the GT data
                    found_in_GT = False
                    # Check if it's in the speaker mentions
                    for speaker in GT_data['CHAINS']['LINKED MENTIONS']['SPEAKER MENTIONS']:
                        if found_in_GT == False:
                            for mention in GT_data['CHAINS']['LINKED MENTIONS']['SPEAKER MENTIONS'][speaker]:
                                if mention['Turn ID'] == turn_ID and mention['Mention start'] == start_index and mention['Mention end'] == end_index:
                                    true_positives += 1
                                    true_positives_ids[GT_dialogue_number].append(mention['Row ID'])
                                    found_in_GT = True
                                    break # Found a match, no need to check other GT mentions
                    # Check if it's in the task mentions
                    if found_in_GT == False:
                        for index, chain in enumerate(GT_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS']):
                            if found_in_GT == False:
                                for mention in GT_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS'][index]['MENTIONS']:                                
                                    if mention['TURN ID'] == turn_ID and mention['SPAN']['START'] == start_index and mention['SPAN']['END'] == end_index:
                                        true_positives += 1
                                        true_positives_ids[GT_dialogue_number].append(mention['MENTION ID'])
                                        found_in_GT = True
                                        break # Found a match, no need to check other GT mentions
                    # Check if it's in the single mentions
                    if found_in_GT == False:
                        for mention in GT_data['CHAINS']['SINGLE MENTIONS']:
                            if mention['TURN ID'] == turn_ID and mention['SPAN']['START'] == start_index and mention['SPAN']['END'] == end_index:
                                true_positives += 1
                                true_positives_ids[GT_dialogue_number].append(mention['MENTION ID'])
                                found_in_GT = True
                                break
                    # If the mention was not found in GT, it's a false positive
                    if found_in_GT == False:
                        false_positives += 1
                        false_positives_of_this_dialogue_list.append((mention_in_all_positives, turn_ID, start_index, end_index))
                # After going through all the mentions in the output, we store the false positives for this dialogue 
                # (inside the if loop not to have blank lists for not-matching dialogues)
                false_positives_with_indexes[GT_dialogue_number] = false_positives_of_this_dialogue_list
                    
    # Now use the IDs of the true positives to find the false negatives
    for file_pair in GT_annotations:
        # The second file is the Excel
        GT_data = pd.read_excel(file_pair[1])
        dialogue_number_regex = re.compile(r'(\d{3})[xX&](\d{3})')  # Assuming dialogue numbers are in the format '035x013'
        GT_dialogue_number = re.search(dialogue_number_regex, file_pair[1]).group(0)  # Extract the dialogue number from the file name
        all_output_mention_IDs_for_this_dialogue = set()
        for mention_ID in true_positives_ids[GT_dialogue_number]:
            all_output_mention_IDs_for_this_dialogue.add(mention_ID)
        # Extract all the values of GT_data['Row ID'] into a set as long as GT_data['Turn ID'] is in the turns included in the evaluation
        # In case there are format differences in the dialogue numbers, find the dialogue in turns_included_in_evaluation matching the GT_dialogue_number
        for key in turns_included_in_evaluation:
            if key[0:3] == GT_dialogue_number[0:3] and key[4:7] == GT_dialogue_number[4:7]:
                GT_dialogue_number = key
                break
        GT_data_used_for_evaluation = GT_data[GT_data['Turn ID'].isin(turns_included_in_evaluation[GT_dialogue_number])] # New df of only the turns included in the evaluation
        GT_mention_IDs_for_this_dialogue = set(GT_data_used_for_evaluation['Row ID'].tolist()) # Extract all the mention IDs from the GT data included in the evaluation
        # Find the false negatives by checking which GT mention IDs are not in the output mention IDs
        false_negatives_for_this_dialogue = []
        for mention_ID in GT_mention_IDs_for_this_dialogue:
            if mention_ID not in all_output_mention_IDs_for_this_dialogue:
                false_negatives += 1
                false_negatives_for_this_dialogue.append(mention_ID)
        false_negatives_ids[GT_dialogue_number] = false_negatives_for_this_dialogue


    precision = true_positives / all_positives if all_positives > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = (2 * (precision * recall)) / (precision + recall) if (precision + recall) > 0 else 0
    #print(f'Turns included in evaluation: {len(turns_included_in_evaluation)}')
    #print(f'They are: {turns_included_in_evaluation}')
    return precision, recall, f1_score, true_positives_ids, false_positives_with_indexes, false_negatives_ids, turns_included_in_evaluation, all_positives_with_indexes

