

# Function to convert dialogue turn into few-shot example for mention detection
def convert_turn_to_few_shot_for_md(dialogue_number,turn_ID, list_of_excels_and_dialoguejsons):
    #print("Entered the convert_turn_to_few_shot_for_md function")
    # Make sure turn_ID is an integer
    turn_ID = int(turn_ID)

    # Find the right Excel for the mentions and the right dialogue json for the transcript
    dialogue_number_pattern = re.compile(r'(\d\d\d)[&xX](\d\d\d)')
    # Extract the dialogue number from the dialogue_number variable
    match_dialogue_number = dialogue_number_pattern.search(dialogue_number)
    dialogue_number_speaker_A = match_dialogue_number.group(1)
    dialogue_number_speaker_B = match_dialogue_number.group(2)
    for excel, dialogue_json in list_of_excels_and_dialoguejsons:
        # Variables to confirm that the correct files have been found
        habemus_dialogue_number_excel = re.search(r'(\d\d\d)[&xX](\d\d\d)', excel)
        habemus_dialogue_number_dialogue_json = re.search(r'(\d\d\d)[&xX](\d\d\d)', dialogue_json)
        if habemus_dialogue_number_excel.group(1) == dialogue_number_speaker_A and habemus_dialogue_number_excel.group(2) == dialogue_number_speaker_B:
            # Read the Excel file
            df = pd.read_excel(excel)
            # Find the rows for the turn_ID
            rows = df[df['Turn ID'] == turn_ID]
            if not rows.empty:
                # Extract the mention spans
                mention_starts = rows['Mention start'].tolist()
                mention_ends = rows['Mention end'].tolist()
        if habemus_dialogue_number_dialogue_json.group(1) == dialogue_number_speaker_A and habemus_dialogue_number_dialogue_json.group(2) == dialogue_number_speaker_B:
            # Read the dialogue JSON file
            with open(dialogue_json, 'r', encoding='utf-8') as file:
                dialogue_data = json.load(file)
            # Find the turn with the given turn_ID
            for turn in dialogue_data['SESSION']['TURNS']:
                if turn['TURN_ID'] == turn_ID:
                    # Extract the transcript
                    transcript_of_the_turn_for_ev = turn['TURN']['TRANSCRIPT']
                    break
    # Check that this turn has mentions:
    # I'll keep a copy of the original transcript
    original_transcript = transcript_of_the_turn_for_ev
    if turn_ID in rows['Turn ID'].values:
        # Now use the mentions starts and ends to add <M> and </M> tags to the transcript
        # I will add the stags starting from the end of the transcript to avoid messing up the indices
        # We need to take into account that there might be nested mentions, so we should start from the very end and move backwards,
        # Maybe adding two end tags in a row in case of nested mentions
        # So we need to add a "S" value to the values of the mention_starts list, and a "E" value to the values of the mention_ends list,
        # Turning the lists into lists of tuples
        for start in mention_starts:
            mention_starts[mention_starts.index(start)] = (start, 'S')
        for end in mention_ends:
            mention_ends[mention_ends.index(end)] = (end, 'E')
        #print(f"mention_starts: {mention_starts}")
        #print(f"mention_ends: {mention_ends}")
        # Combine the two lists into one list of tuples, with the type of the mention (start or end) as the second element
        combined_mention_indexes = mention_starts + mention_ends
        # Sort the combined list by the index (the first element of the tuple), from last to first
        combined_mention_indexes.sort(key=lambda x: x[0], reverse=True)
        #print(f"combined_mentions: {combined_mention_indexes}")
        # Now we can iterate over the combined list and add the tags to the transcript
        for index, mention_type in combined_mention_indexes:
            if mention_type == 'S':
                # Add the opening tag
                transcript_of_the_turn_for_ev = transcript_of_the_turn_for_ev[:index] + '<M>' + transcript_of_the_turn_for_ev[index:]
            elif mention_type == 'E':
                # Add the closing tag
                transcript_of_the_turn_for_ev = transcript_of_the_turn_for_ev[:index] + '</M>' + transcript_of_the_turn_for_ev[index:]
        tagged_transcript = transcript_of_the_turn_for_ev
    # If the turn has no mentions, the tagged text is the same as the original
    else:
        tagged_transcript = original_transcript
    return original_transcript, tagged_transcript


# Function to select a random few-shot turn and a random evaluation split
def select_dialoguebased_few_shot_turn_and_evaluation_split_eval(doing_mention_head_detection,model_for_span_changing,list_of_excels_and_dialoguejsons_dev, list_of_excels_and_dialoguejsons_eval, number_of_few_shot_examples,dictionary_of_dev_turns_with_transcript):
    # Extract pool for retrieval of FS examples
    pool_for_retrieval_of_fs = [] 
    for dialogue in dictionary_of_dev_turns_with_transcript:
        json_dialogue_number = dialogue
        for turn in dictionary_of_dev_turns_with_transcript[dialogue]:
            pool_fs_turn_ID = turn
            # Extract transcript and tagged transcript
            pool_fs_transcript, pool_fs_tagged_transcript = convert_turn_to_few_shot_for_md(json_dialogue_number, pool_fs_turn_ID, list_of_excels_and_dialoguejsons_dev)
            pool_for_retrieval_of_fs.append((json_dialogue_number, pool_fs_turn_ID, pool_fs_transcript, pool_fs_tagged_transcript))        

    # List of evaluation turns. It will contain (ev_dialogue_number, ev_turn_ID, ev_transcript, ev_fs_examples_list) tuples
    # ev_fs_examples_list contains [(fs_dialogue_number, fs_turn_ID,fs_transcript, fs_tagged_trasncript), ...]
    folds = []
    # We first need to process the total number of turns in all the dialogues in the list
    # We will use the dialogue jsons to include transcripts without mentions
    # Though we must bear in mind that some turns have no transcripts, so we will skip those
    eval_turns = {} # Here we'll add tuples of (dialogue_number, turn_ID) for turns that have transcripts
    # We will exclude the turns in our fs example retrieval pool
    # The dialogue numbers in the pool come from the sessionID field, so we don't need to worry about format conversion
    for file_pair in list_of_excels_and_dialoguejsons_eval:
        dialogue_json = file_pair[1]
        with open(dialogue_json, 'r', encoding='utf-8') as file:
            dialogue_data = json.load(file)
        dialogue_number_of_this_json = dialogue_data['SESSION']['sessionID']
        turns_of_this_dialogue = []
        for turn in dialogue_data['SESSION']['TURNS']:
            if 'TRANSCRIPT' in turn['TURN']:
                transcript_of_this_turn = turn['TURN']['TRANSCRIPT']
                is_this_turn_in_pool = False
                for pool_fs_example in pool_for_retrieval_of_fs:
                    if pool_fs_example[0] == dialogue_number_of_this_json and pool_fs_example[1] == turn['TURN_ID']:
                        is_this_turn_in_pool == True
                        break
                if is_this_turn_in_pool == False:
                    turns_of_this_dialogue.append((dialogue_number_of_this_json, turn['TURN_ID'], transcript_of_this_turn))
        eval_turns[dialogue_number_of_this_json] = turns_of_this_dialogue
    # Now we add the FS to each eval turn
    for dialogue in eval_turns:
        current_fold = []
        for turn in eval_turns[dialogue]:
            ev_dialogue_number, ev_turn_ID, ev_transcript = turn
            # Retrieve the best FS examples
            # Encode the ev transcript
            ev_transcript_encoded = nlp(ev_transcript)
            list_of_fs_similarities = []
            for possible_fs in pool_for_retrieval_of_fs:
                possible_fs_encoded = nlp(possible_fs[2])
                similarity = ev_transcript_encoded.similarity(possible_fs_encoded)
                possible_fs = possible_fs + (similarity,)
                list_of_fs_similarities.append(possible_fs)
            # Now I order the list from top similarity
            ordered_fs_similarities = sorted(list_of_fs_similarities, key=lambda x: x[-1], reverse=True)
            # Build the fs_examples list as a slice of the top candidates from ordered_fs_similarities (up to the number_of_few_shot_examples)
            fs_examples = ordered_fs_similarities[:number_of_few_shot_examples]
            # If doing meantion-head detection, I need to convert the tagged transcripts in the fs examples to tagged heads
            if doing_mention_head_detection == True:
                fs_examples = convert_fs_example_list_to_two_prompt_fs_examples(fs_examples,model_for_span_changing)
            # Add the evaluation turn to the list
            current_fold.append((ev_dialogue_number, ev_turn_ID, ev_transcript, fs_examples))
        folds.append(current_fold)
    return folds
