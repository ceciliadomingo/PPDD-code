

# -------------------------------------------------------
# AUXILIARY FUNCTIONS
# -------------------------------------------------------
# Function to convert floats to integers, as excel may parse some numbers as floats
# We need this to process the referent spans
def convert_to_int_if_float(value):
    import pandas as pd
    # If it's a float (and not nans, those are detected as floats)
    # If it's a float #and it is convertible to integer
    if isinstance(value, float) and not pd.isna(value):# and value.is_integer():
        return int(value)
    else:
        return value
    
# Function to order mentions in a chain to extract first mentions
def reorder_mentions_in_chain(chain_json, dialogue_number, output_log):

    # Load the chain JSON file
    with open(chain_json, 'r', encoding='utf-8') as f:
        chain_data = json.load(f)

    # Create a reference to the location of the linked chains
    chains_list = chain_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS']
    print(len(chains_list), "chains found in the JSON file.")
    for chain in chains_list:
        print(f"Chain ID: {chain['CHAIN ID']}, Number of Mentions: {len(chain['MENTIONS'])}", file=open(output_log, 'a+'))
    
    # Check the type of mention id
    for chain in chains_list:
        for mention in chain['MENTIONS']:
            if not isinstance(mention['MENTION ID'], int):
                raise ValueError(f"MENTION ID should be an integer, found {mention['MENTION ID']} of type {type(mention['MENTION ID'])}", file=open(output_log, 'a+'))
            
    # Check if the chains are already sorted
    for chain in chains_list:
        mention_ids = [int(mention['MENTION ID']) for mention in chain['MENTIONS']]
        if mention_ids != sorted(mention_ids):
            raise ValueError(f"Chain {chain['CHAIN ID']} is not presorted by MENTION ID.")

    # Iterate over each chain with its index
    for chain in chains_list:
        chain['MENTIONS'] = sorted(chain['MENTIONS'], key=lambda x: int(x['MENTION ID']))

    # Check that the chains are sorted
    for chain in chains_list:
        mention_ids = [int(mention['MENTION ID']) for mention in chain['MENTIONS']]
        if mention_ids != sorted(mention_ids):
            raise ValueError(f"Chain {chain['CHAIN ID']} is not sorted correctly by MENTION ID.")

    # Save the updated chain JSON
    output_chain_json = os.path.join(os.path.dirname(chain_json), f"{dialogue_number}_10_reordered_chains.json")
    with open(output_chain_json, 'w', encoding='utf-8') as f:
        json.dump(chain_data, f, indent=4)

    return output_chain_json


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# TWO MAIN FUNCTIONS: check_first_mention AND check_cataphora
# -------------------------------------------------------
# FIRST MENTION
#-------------------------------------------------------
# Function to check if a mention is the first mention in the chain (the one that cannot be linked ot any previous mention)
def check_first_mention(ordered_chains, excel_file, dialogue_number):

    # Load the ordered chains JSON file
    with open(ordered_chains, 'r', encoding='utf-8') as f:
        chains_data = json.load(f)
    # Load the Excel file to see the referents
    excel_df = pd.read_excel(excel_file, engine='openpyxl')
    # Create a list to store the mentions where first mention should be False
    NOT_first_mentions_id = []
    # Create a list for the special cases where the referent does not exist as a mention
    special_cases = []
    # Go through each mention in the linked mentions
    for chain in chains_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS']:
        for mention in chain['MENTIONS']:
            # Check if the mention is the first mention
            mention_ID = mention['MENTION ID']
            # Use the mention ID to find the corresponding row in the Excel file
            mention_row = excel_df[excel_df['Row ID'] == mention_ID]
            # Locate the referent in the row (Referent Turn ID, Referent Turn Span Start, Referent Turn Span End)
            if pd.notna(mention_row['Referent Turn ID'].iloc[0]):
                referent_turn_ID = mention_row['Referent Turn ID'].iloc[0]
                referent_start = mention_row['Referent Turn Span Start'].iloc[0]
                referent_end = mention_row['Referent Turn Span End'].iloc[0]
                # See if there is a different row where the mention info equals our referent info
                referent_row = excel_df[(excel_df['Turn ID'] == referent_turn_ID) & 
                                        (excel_df['Mention start'] == referent_start) & 
                                        (excel_df['Mention end'] == referent_end)]
                if not referent_row.empty: # If there is a referent row, it means the mention is NOT the first mention
                    NOT_first_mentions_id.append(mention_ID)
                else:
                    # There is a referent, but it does not exist as a mention in the Excel file
                    special_cases.append((mention_ID, f"Referent is Turn {convert_to_int_if_float(referent_turn_ID)} + Start index {convert_to_int_if_float(referent_start)} +  End index {convert_to_int_if_float(referent_end)}, but it was not annotated as a mention."))
    # Locate the mentions with the id in the NOT_first_mentions_id list and change the value of 'First mention' to False
    for chain in chains_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS']:
        for mention in chain['MENTIONS']:
            if int(mention['MENTION ID']) in NOT_first_mentions_id:
                mention['FIRST MENTION'] = False
            else:
                mention['FIRST MENTION'] = True
    # Locate the mentions with the id in the special_cases list and change the value of 'First mention' to the info in the list
    for chain in chains_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS']:
        for mention in chain['MENTIONS']:
            if int(mention['MENTION ID']) in [case[0] for case in special_cases]:
                # Find the case info
                mention['FIRST MENTION'] = next(case[1] for case in special_cases if case[0] == int(mention['MENTION ID']))
    # Save the updated chains JSON with first mentions checked
    output_chain_json = os.path.join(os.path.dirname(ordered_chains), f"{dialogue_number}_11_checked_first_mentions.json")
    with open(output_chain_json, 'w', encoding='utf-8') as f:
        json.dump(chains_data, f, indent=4)
    return output_chain_json

# -------------------------------------------------------
# CATAPHORA
# -------------------------------------------------------
# Function to check for cataphora in the chains JSON
# We consider cataphora when the mention identified as first mention (not linked to any previous mention) is not chronologically the first mention in the chain
def check_cataphora(chains_with_first_mention, dialogue_number, output_log):

    # Load the chains JSON file with first mentions checked
    with open(chains_with_first_mention, 'r', encoding='utf-8') as f:
        chains_data = json.load(f)
    
    # Create a list to store the mentions where cataphora should be True
    cataphora_mentions = []
    
    # Go through each mention in the linked mentions
    for chain in chains_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS']:
        for index, mention in enumerate(chain['MENTIONS']):
            # Check if the mention is a cataphora
            # If it's chronologically not the first mention but has 'FIRST MENTION' set to True (because it has no referent), it is a cataphora
            # NOTE: There might be cases of intra-turn cataphora, but if an entity was mentioned in a previous turn,
            # we linked the cataphoric-looking mention to aprevious turn, thus not counting it as a cataphora
            if mention.get('FIRST MENTION', True) and index > 0:
                cataphora_mentions.append(mention['MENTION ID'])
    # Update the mentions to include the cataphora information
    for chain in chains_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS']:
        for mention in chain['MENTIONS']:
            if int(mention['MENTION ID']) in cataphora_mentions:
                mention['CATAPHORA'] = True
            else:
                mention['CATAPHORA'] = False

    # Log the cataphora mentions
    print(f"Found {len(cataphora_mentions)} cataphora mentions in the dialogue {dialogue_number}.", file=open(output_log, 'a+'))            
    
    # Save the updated chains JSON with cataphora checked
    output_chain_json = os.path.join(os.path.dirname(chains_with_first_mention), f"{dialogue_number}_12_checked_cataphora.json")
    with open(output_chain_json, 'w', encoding='utf-8') as f:
        json.dump(chains_data, f, indent=4)    
    return output_chain_json

