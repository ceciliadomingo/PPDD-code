# Function to go hrough the json report on mentions labelled as INCOMPLETE
# and add a field 'Multi-speaker' set to True if the mention was completed by different speakers
def add_multispeaker_to_incomplete_json(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    for completeobj in data:
        list_of_speakers = []
        for item in completeobj['Items']:
            list_of_speakers.append(completeobj['Items'][item]['Speaker'])
        # Convert list to a set
        list_of_speakers = set(list_of_speakers)
        if len(list_of_speakers) > 1:
            completeobj['Multi-speaker'] = True
        elif len(list_of_speakers) == 1:
            completeobj['Multi-speaker'] = False
        # Save the modified JSON back to the file
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
    return json_path
