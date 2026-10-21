# Function to link mentions to persons into coreference chains
# These mentions (e.g., "I", "you", "(BLEEP)", "Cecilia") were not fully annotated, to save time during annotation, as they are not the main focus of the study
# We can however extract the coreference chains with good accuracy through simple rules
# We however distinguish between certain and ambiguous cases; where perfect accuracy is not important, the otuputs of both cases can be merged
# (e.g., "I" said by participant A is certainly participant A; "you" said by participant A is likely participant B, but could also be the researcher)
def add_speaker_references(excel_file, dialogue_json, dialogue_number, chains_json):
    # Read the Excel file into a DataFrame
    df = pd.read_excel(excel_file)

    # Locate rows where mention is "you", "we", "us", "'s", "I/i" [without discourse or code referent], "Cecilia", "Ceci", "she", "her", "(BLEEP)", "he", "him"
    df_persons = df[df['Mention'].str.lower().isin(["you", "we", "us", "i", "me", "'s", "cecilia", "ceci", "she", "her", "(bleep)", "he", "him"])]
    # Remove rows with "I/i" that have a discourse or code referent
    df_persons = df_persons[~df_persons['Mention'].str.contains(r'\bi\b|\bI\b', na=False) | ~df_persons['Referent Turn ID'].notna() | ~df_persons['Code File'].notna()]
    
    #Extract speaker numbers from the dialogue number
    speaker_pattern = r'(\d{3})[xX&](\d{3})'
    match = re.match(speaker_pattern, dialogue_number)
    speaker_A = match.group(1)
    speaker_B = match.group(2)
    # Create a dictionary to hold the speaker references
    speaker_references = defaultdict(list)
    #speaker_references = {speaker_A: [], speaker_B: [], 'BOTH PARTICIPANTS':[], 'RESEARCHER':[], 'AMBIGUOUS PERSON': []}

    #Add Speaker column to DataFrame
    df_persons['Speaker'] = None
    # Iterate through the DataFrame to assign speakers based on the Turn ID and the dialogue json
    with open(dialogue_json, 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    for index, row in df_persons.iterrows():
        turn_id = row['Turn ID']
        # Find the speaker in the dialogue data
        for entry in dialogue_data['SESSION']['TURNS']:
            if entry['TURN_ID'] == turn_id:
                speaker = entry['TURN']['DIARIZATION']['SPEAKER']
                df_persons.at[index, 'Speaker'] = speaker
    
    # Iterate through the DataFrame to extract speaker references
    # REFERENT A (A saying “I”, B saying “you”, B saying “(BLEEP)” [we have to exclude cases of researcher saying (BLEEP), as we can only disambiguate that manually].)
    # LIKELY REFERENT A (B saying “you”) [In English, "you" can also be plural, so we can't be 100% sure; occassionally, they may refer to researcher]
    # REFERENT B () B saying “I”, A saying “you”, A saying “(BLEEP)” [we have to exclude cases of researcher saying (BLEEP), as we can only disambiguate that manually].)
    # LIKELY REFERENT B (A saying “you”) [In English, "you" can also be plural, so we can't be 100% sure; occassionally, they may refer to researcher]
    # RESEARCHER: any mention of “Cecilia”, “Ceci”; researcher saying “I”.
    # AMBIGUOUS PERSON: any mention of “she", "her" (could be researcher or participant), researcher saying "he", "him", you", "(BLEEP)" (could be either participant)
    for index, row in df_persons.iterrows():
        mention = row['Mention']
        speaker = row['Speaker']
        likely_A_string = f'Likely referent {speaker_A}'
        likely_B_string = f'Likely referent {speaker_B}'
        if mention.lower() in ["i", "me"] and speaker == speaker_A:
            speaker_references[speaker_A].append(row.to_dict())
        elif mention == "(BLEEP)" and speaker == speaker_B:
            speaker_references[speaker_A].append(row.to_dict())
        elif mention.lower() == "you" and speaker == speaker_B:
            speaker_references[likely_A_string].append(row.to_dict())
        elif mention.lower() in ["he", "him"] and speaker == speaker_B:
            speaker_references[speaker_A].append(row.to_dict())

        elif mention.lower() in ["i", "me"] and speaker == speaker_B:
            speaker_references[speaker_B].append(row.to_dict())
        elif mention == "(BLEEP)" and speaker == speaker_A:
            speaker_references[speaker_B].append(row.to_dict())
        elif mention.lower() == "you" and speaker == speaker_A:
            speaker_references[likely_B_string].append(row.to_dict())
        elif mention.lower() in ["he", "him"] and speaker == speaker_A:
            speaker_references[speaker_B].append(row.to_dict())
        
        elif mention.lower() in ["cecilia", "ceci"]:
            speaker_references['RESEARCHER'].append(row.to_dict())
        elif mention.lower() in ["i", "me"] and speaker == 'RESEARCHER':
            speaker_references['RESEARCHER'].append(row.to_dict())

        elif mention.lower() in ["he", "him", "she", "her", "you", "(bleep)"] and speaker == 'RESEARCHER':
            speaker_references['AMBIGUOUS PERSON'].append(row.to_dict())
        elif mention.lower() in ["she", "her"] and speaker in [speaker_A, speaker_B]: # The researcher is female, so we don't know if "she" is the researcher or one of the participants
            speaker_references['AMBIGUOUS PERSON'].append(row.to_dict())

        elif mention.lower() in ["we", "us", "'s"] and speaker in [speaker_A, speaker_B]:
            speaker_references['BOTH PARTICIPANTS'].append(row.to_dict())
    # Save the speaker references to a JSON file
    output_file = f'{dialogue_number}_07_speaker_references.json'
    speaker_references_json_output_filepath = os.path.join(os.path.dirname(excel_file), output_file)
    json_structure = {'dialogue_number': dialogue_number, 'speaker_references': speaker_references}
    with open(speaker_references_json_output_filepath, 'w', encoding='utf-8') as f:
        json.dump(json_structure, f, indent=4)

    # Create a copy of the chains json to add the speaker references
    # First load the chains json
    with open(chains_json, 'r', encoding='utf-8') as f:
        chains_json_data = json.load(f)
    # Add the speaker references to the chains json
    chains_json_data['CHAINS']['LINKED MENTIONS'] = {'SPEAKER MENTIONS': speaker_references}

    # Iterate through row IDs in the speaker mentions to remove the corresponding entries from the single mentions object of the chains json
    row_IDs_to_remove = set()
    for speaker, mentions in speaker_references.items():
        for mention in mentions:
            row_IDs_to_remove.add(mention['Row ID'])

    # Remove the entries from the single mentions object
    chains_json_data['CHAINS']['SINGLE MENTIONS'] = [
    mention for mention in chains_json_data['CHAINS']['SINGLE MENTIONS']
    if int(mention['MENTION ID']) not in row_IDs_to_remove]

    # Save the updated chains json to a new file
    chains_json_output_file = f'{dialogue_number}_08_chains_with_speaker_references.json'
    chains_json_with_speaker_references_filepath = os.path.join(os.path.dirname(excel_file), chains_json_output_file)
    with open(chains_json_with_speaker_references_filepath, 'w', encoding='utf-8') as f:
        json.dump(chains_json_data, f, indent=4)
    return speaker_references_json_output_filepath, chains_json_with_speaker_references_filepath
