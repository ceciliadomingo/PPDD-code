# Dealing with incompletes
# After dealing with punctuation, and before extracting links, go through Excel and locate rows labelled as INCOMPLETE. 
# This means that the mention int hat row was not finished in that turn, and may continue in the next turn(s).
# We thus have some duplicate rows in the Excel, the first one with the grammatical category label, and then the same mention with the INCOMPLETE label in the Mention form column.
# So we look at row and row+1.
# If row+2 is also an incomplete mention, we understand it to be the continuation of the previous incomplete mention.
# So we go to that row until the mention is complete (row+2 != incomplete). 
# Through this process, we also generate a json report. Each object in the json will be a completed mention with the fields:
#	Complete form: extract it by adding each string in the iteration
#	Items
#	    Row ID
#	    Incomplete form
#	    Speaker
# Using this json, we can later add the field “multispeaker” by looking at whether there is more than one speaker in the items object.
# After extracting all the incompletes, we can remove all rows that say INCOMPLETE, as they are duplicates. 
# We can then add a column to the Excel called Incomplete, populated by default as false. If a row ID is in the incomplete json, we change that to true.


# Function to extract the speaker of each mention using the Turn ID
def extract_speaker(excel_file, row_id, dialogue_json):
    # Read the Excel file into a DataFrame
    df = pd.read_excel(excel_file)
    # Find the row with the specified Row ID
    row = df[df['Row ID'] == row_id]
    # Find the turn ID of the row
    turn_id = row['Turn ID'].values[0]
    # Use the turnd ID to locate the speaker in the dialogue JSON
    with open(dialogue_json, 'r') as f:
        dialogue_json = json.load(f)
    for turnobj in dialogue_json['SESSION']['TURNS']:
        if turnobj['TURN_ID'] == turn_id:
            # Extract the speaker from the JSON
            speaker = turnobj['TURN']['DIARIZATION']['SPEAKER']
            return speaker

# Function to check the next rows for more incomplete parts
def next_row_checker(indexchecked,df,incomplete_bits,indexes_already_added):
    # Check if the next row is incomplete
    # df is 0-indexed. Len would be 1 more than the last index
    # First trim the df to start from the indexchecked
    df_trimmed = df.iloc[indexchecked:]
    for index, row in df_trimmed.iterrows():
        # Incomplete labels normally appear in alternate rows, but algorithm must be flexible for few cases were rows are contiguous or separated by an extra row
        if index + 1 < len(df) and "INCOMPLETE" in df.iloc[index + 1]['Mention form']:
            index_of_row_to_add = index + 1
            bit_tuple = (df.iloc[index_of_row_to_add]['Mention'], df.iloc[index_of_row_to_add]['Row ID'])
            incomplete_bits.append(bit_tuple)
            indexes_already_added.append(index_of_row_to_add)
        elif index + 2 < len(df) and "INCOMPLETE" in df.iloc[index + 2]['Mention form']:
            index_of_row_to_add = index + 2
            bit_tuple = (df.iloc[index_of_row_to_add]['Mention'], df.iloc[index_of_row_to_add]['Row ID'])
            incomplete_bits.append(bit_tuple)
            indexes_already_added.append(index_of_row_to_add)
        elif index + 3 < len(df) and "INCOMPLETE" in df.iloc[index + 3]['Mention form']:
            index_of_row_to_add = index + 3
            bit_tuple = (df.iloc[index_of_row_to_add]['Mention'], df.iloc[index_of_row_to_add]['Row ID'])
            incomplete_bits.append(bit_tuple)
            indexes_already_added.append(index_of_row_to_add)
        elif index + 4 < len(df) and "INCOMPLETE" in df.iloc[index + 4]['Mention form']:
            index_of_row_to_add = index + 4
            bit_tuple = (df.iloc[index_of_row_to_add]['Mention'], df.iloc[index_of_row_to_add]['Row ID'])
            incomplete_bits.append(bit_tuple)
            indexes_already_added.append(index_of_row_to_add)
        return incomplete_bits,indexes_already_added

# Main function to extract incompletes from the Excel file and create the incomplete JSON
def extract_incompletes(excel_file, dialogue_json, dialogue_number, output_log):
    print(f"Processing incompletes for {dialogue_number}.", file=(open(output_log, 'a+')))

    # Read the Excel file
    df = pd.read_excel(excel_file)
    # Initialize the incomplete JSON structure
    incomplete_json = []
    # Initialise a list of incomplete components of a complete mention
    incomplete_bits = []


    # Create list of indexes already added to the incomplete JSON
    indexes_already_added = []
    # Iterate through the DataFrame to find incompletes
    for index, row in df.iterrows():
        if index in indexes_already_added:
            # Skip this index as it has already been added to the incomplete JSON through the look-forward function
            print(f"Skipping index {index} as it has already been added", file=(open(output_log, 'a+')))
            continue
        if "INCOMPLETE" in row['Mention form']:
            indexes_already_added.append(index)
            print(f"Adding index {index} to the incomplete JSON", file=(open(output_log, 'a+')))
            # Collect the incomplete bits
            beginning_tuple = (row['Mention'], row['Row ID'])
            incomplete_bits.append(beginning_tuple)
            # Check if there are more elements to this incomplete
            incomplete_bits,indexes_already_added = next_row_checker(index,df,incomplete_bits,indexes_already_added)
            # We reached the end of this incomplete. Let's extract the infor and create the JSON
            complete_mention_str = ''
            if len(incomplete_bits) > 1:
                for tuple in incomplete_bits:
                    complete_mention_str += tuple[0] + ' '
                # Remove the last space
                complete_mention_str = complete_mention_str.strip()
            else:
                # If there is only one incomplete bit, specify that there's no complete
                complete_mention_str = False
            # Create the JSON object
            # Create the Items dictionary with the data from each item of the incomplete_bit list
            items_dict_of_dicts = {
                int(item[1]): {
                'Incomplete form': item[0],
                'Speaker': extract_speaker(excel_file,item[1], dialogue_json)
                }
                for item in incomplete_bits
                }
            complete_mention = {
                'Complete form': complete_mention_str,
                'Items': items_dict_of_dicts
                }
                    
            incomplete_json.append(complete_mention)
            # Reset list for next incomplete
            incomplete_bits = []

    # Write the incomplete JSON to a file
    excel_folder = os.path.dirname(excel_file)
    incomplete_json_filename = excel_folder + '\\' + dialogue_number  + '_incomplete.json'
    print(f"Writing incomplete JSON to {incomplete_json_filename}", file=(open(output_log, 'a+')))
    with open(incomplete_json_filename, 'w') as f:
        json.dump(incomplete_json, f, indent=4)
    return incomplete_json_filename

