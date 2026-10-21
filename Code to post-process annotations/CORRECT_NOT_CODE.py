# Correct instances where the Code Type label says NOT code but there is a code referent
# These annotations were carried out by different annotators, so some disagreements are to be expected.
# We however want some consistency, so we take the work of the final annotator as reference.
def correct_not_code(chain_json,dialogue_number):
    # Load the JSON data
    with open(chain_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Iterate through json 
    for chain in data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS']:
        for mention in chain['MENTIONS']:
            if mention['CODE TYPE'] == 'NOT code' and pd.notna(mention['CODE REFERENT']['FILE']):
                # Change the CODE TYPE to 'code'
                mention['CODE TYPE'] = 'CODE N.O.S.'
            if mention['CODE TYPE'] != 'NOT code' and mention['CODE TYPE'] != 'CODE N.O.S.' and pd.isna(mention['CODE REFERENT']['FILE']):
                # Change the CODE TYPE to 'NOT code'
                mention['CODE TYPE'] = 'NOT code'
    # Save the modified JSON data back to the file
    output_json = os.path.join(os.path.dirname(chain_json), f"{dialogue_number}_13_checked_NOTCODE.json")
    with open(output_json, 'w') as f:
        json.dump(data, f, indent=4)
    return data