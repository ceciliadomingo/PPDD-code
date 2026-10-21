# Scripts to clean output
import re
import ast
import json

def remove_space_beginning(text):
    return text.lstrip()

def remove_arrows(text):
    return text.replace("--> ", "").replace("-->", "")

def remove_text_to_parse(text):
    return text.replace("TEXT TO PARSE:", "").replace("TEXT TO PARSE", "")

def change_mention_tags(text):
    return text.replace("<MENTION>", "<M>").replace("</MENTION>", "</M>").replace("<mention>", "<M>").replace("</mention>", "</M>")

def separate_contracted_verbs(text):
    import re
    contracted_verbs = ["'m", "'re", "'ve", "'ll", "'d","'s"]
    for verb in contracted_verbs:
        text = text.replace(verb + "</M>", "</M>" + verb)
    # Special treatment for "let's" to undo the previous step (easier to undo than to prevent)
    text = re.sub(r"Let<M></M>'s(?!</M>)", "Let<M>'s</M>", text) #if output is like "Let<M></M>'s go"
    text = re.sub(r"let<M></M>'s(?!</M>)", "let<M>'s</M>", text) #if output is like "let<M></M>'s go"
    text = re.sub(r"<M>let</M>'s(?!</M>)", "let<M>'s</M>", text) #if output is like "<M>Let</M>'s go"
    text = re.sub(r"<M>Let</M>'s(?!</M>)", "Let<M>'s</M>", text) #if output is like "<M>Let</M>'s go"
    return text

def find_original_transcript(file_of_all_files, dialogue_number, turn_id):
    turn_id = int(turn_id)  # Ensure turn_id is an integer
    with open(file_of_all_files, 'r') as file:
        content = file.read()
    list_of_excels_and_dialoguejsons = ast.literal_eval(content)
    # Find the right dialogue json for this dialogue number
    dialogue_number_pattern = re.compile(r'(\d\d\d)[&xX_](\d\d\d)')
    # Extract the dialogue number from the dialogue_number variable
    match_dialogue_number = dialogue_number_pattern.search(dialogue_number)
    dialogue_number_speaker_A = match_dialogue_number.group(1)
    dialogue_number_speaker_B = match_dialogue_number.group(2)
    for excel, dialogue_json in list_of_excels_and_dialoguejsons:
        habemus_dialogue_number_dialogue_json = re.search(r'(\d\d\d)[&xX_](\d\d\d)', dialogue_json)
        if habemus_dialogue_number_dialogue_json and habemus_dialogue_number_dialogue_json.group(1) == dialogue_number_speaker_A and habemus_dialogue_number_dialogue_json.group(2) == dialogue_number_speaker_B:
            # Read the dialogue JSON file
            with open(dialogue_json, 'r', encoding='utf-8') as file:
                dialogue_data = json.load(file)
            # Find the turn with the given turn_ID
            for turn in dialogue_data['SESSION']['TURNS']:
                if turn['TURN_ID'] == turn_id:
                    # Extract the transcript
                    input_text = turn['TURN']['TRANSCRIPT']
                    break # Do not continue the loop after finding a match
    return input_text
    
def find_hallucinations(file_of_all_files,dialogue_number, turn_id, output_text):
    import difflib
    input_text = find_original_transcript(file_of_all_files,dialogue_number, turn_id)
    # Remove mention tags from output to compare it to the oriignal input
    output_text_notags = output_text.replace("</M>","").replace("<M>", "")
    # Remove extra \n at the end of input_text and output_text_notags
    input_text = input_text.rstrip("\n")
    output_text_notags = output_text_notags.rstrip("\n")
    similarity = difflib.SequenceMatcher(None, input_text, output_text_notags).ratio()
    return similarity

def fix_double_determiners(text):
    import re
    # determiner, [hesitation], determiner
    doubledet_pattern = re.compile(r'<M>((?:the|a|my|our|your))</M>(,)? ?((?:uh|um|uh um|uh, um|um uh|um, uh))?(, )?<M>((?:the|a|my|our|your)) ')
    fixed_doubledet_string = r'<M>\1\2 \3\4\5 '
    text_fixeddoubledets = re.sub(doubledet_pattern, fixed_doubledet_string,text)
    return text_fixeddoubledets



#------------------------------------------------------------------------------------------
# Main function toa pply all cleaning scripts to a single output file, and to create a cleaning report for that file
def clean_output_file(file_of_all_files, file_path):
    import json
    # Create general counters for cases where output covers several dialogues
    counter_spaces = 0
    counter_arrows = 0
    counter_text_to_parse = 0
    counter_wrong_tags = 0
    counter_contracted_verbs = 0
    counter_dets_fixed = 0
    counter_blank_responses = 0
    counter_all_turns = 0
    counter_hallucinations = 0
    cleaned_file_path = file_path.replace(".json", "_CLEANED.json")
    dictionary_of_cleaned_outputs = {}
    report_file_path = file_path.replace(".json", "_CLEANING-REPORT.json")
    dictionary_of_cleaning_reports = {}
    with open(file_path, 'r') as file:
        data = json.load(file)
    for key in data.keys(): # For each dialogue in the output
        # Key is dialogue number, value is dictionary with turn ID and output string
        dictionary_of_cleaned_outputs_for_this_dialogue = {}
        list_of_spaces = []
        list_of_arrows = []
        list_of_text_to_parse = []
        list_of_wrong_tags = []
        list_of_contracted_verbs = []
        list_of_detsfixed = []
        list_of_blank_responses = []
        list_of_similarities = []
        for turn_id, output_string in data[key].items():
            counter_all_turns += 1
            if output_string != "":
                os_withoutspaces = remove_space_beginning(output_string)
                if os_withoutspaces != output_string:
                    list_of_spaces.append(turn_id)               
                os_withoutarrows = remove_arrows(os_withoutspaces)
                if os_withoutarrows != os_withoutspaces:
                    list_of_arrows.append(turn_id)
                os_withouttexttoparse = remove_text_to_parse(os_withoutarrows)
                if os_withouttexttoparse != os_withoutarrows:
                    list_of_text_to_parse.append(turn_id)
                os_with_correct_tags = change_mention_tags(os_withouttexttoparse)
                if os_with_correct_tags != os_withouttexttoparse:
                    list_of_wrong_tags.append(turn_id)
                os_without_contracted_verbs = separate_contracted_verbs(os_with_correct_tags)
                if os_without_contracted_verbs != os_with_correct_tags:
                    list_of_contracted_verbs.append(turn_id)
                os_with_dets_fixed = fix_double_determiners(os_without_contracted_verbs)
                if os_with_dets_fixed != os_without_contracted_verbs:
                    list_of_detsfixed.append(turn_id)
                dictionary_of_cleaned_outputs_for_this_dialogue[turn_id] = os_with_dets_fixed
                output_string = os_with_dets_fixed # To use it later for hallucination detection, but allowing for the case of blank responses
            else:
                list_of_blank_responses.append(turn_id)
                dictionary_of_cleaned_outputs_for_this_dialogue[turn_id] = output_string
            # Check for hallucinations
            similarity = find_hallucinations(file_of_all_files, key, turn_id, output_string)
            list_of_similarities.append((turn_id, similarity))
        # Update the general counters
        counter_spaces += len(list_of_spaces)
        counter_arrows += len(list_of_arrows)
        counter_text_to_parse += len(list_of_text_to_parse)
        counter_wrong_tags += len(list_of_wrong_tags)
        counter_contracted_verbs += len(list_of_contracted_verbs)
        counter_dets_fixed += len(list_of_detsfixed)
        counter_blank_responses += len(list_of_blank_responses)
        # Also update the counter for hallucinations
        for index, similarity_tuple in enumerate(list_of_similarities):
            if similarity_tuple[1] < 1.0:  # If similarity is less than 1, it means there is a difference
                counter_hallucinations += 1
        # Create the contents of the cleaning report for this dialogue
        cleaning_report_contents = {
            "Turns with spaces removed": {
                "count": len(list_of_spaces),
                "turns": list_of_spaces
            },
            "Turns with arrows removed": {
                "count": len(list_of_arrows),
                "turns": list_of_arrows
            },
            "Turns with text to parse removed": {
                "count": len(list_of_text_to_parse),
                "turns": list_of_text_to_parse
            },
            "Turnds with mention tags fixed": {
                "count": len(list_of_wrong_tags),
                "turns": list_of_wrong_tags
            },
            "Turns with contracted verbs removed from mention": {
                "count": len(list_of_contracted_verbs),
                "turns": list_of_contracted_verbs
            },
            "Turns with tags fixed on double determiners": {
                "count": len(list_of_detsfixed),
                "turns": list_of_detsfixed
            },
            "Turns with blank responses": {
                "count": len(list_of_blank_responses),
                "turns": list_of_blank_responses
            },
            "Similarities with the original input": {
                "count of hallucinations": sum(1 for similarity_tuple in list_of_similarities if similarity_tuple[1] < 1.0),
                "turns": list_of_similarities
            }
        }

        # Update the cleaned output dicitonary with the data from this dialogue
        dictionary_of_cleaned_outputs[key] = dictionary_of_cleaned_outputs_for_this_dialogue
        # Update the cleaning report with the data for this dialogue
        dictionary_of_cleaning_reports[key] = cleaning_report_contents
    # After going through all the dialogue, add the general counters to the cleaning report
    cleaning_report_contents_alldialogues = {
        "Total turns": counter_all_turns,
        "Turns with spaces removed": counter_spaces,
        "Percentage of turns with spaces removed": ((counter_spaces / counter_all_turns) * 100),
        "Turns with arrows removed": counter_arrows,
        "Percentage of turns with arrows removed": ((counter_arrows / counter_all_turns) * 100),
        "Turns with text to parse removed": counter_text_to_parse,
        "Percentage of turns with text to parse removed": ((counter_text_to_parse / counter_all_turns) * 100),
        "Turns with tags fixed": counter_wrong_tags,
        "Percentage of turns with tags fixed": ((counter_wrong_tags / counter_all_turns) * 100),
        "Turns with contracted verbs removed from mention": counter_contracted_verbs,
        "Percentage of turns with contracted verbs removed from mention": ((counter_contracted_verbs / counter_all_turns) * 100),
        "Turns with tags fixed for double determiners": counter_dets_fixed,
        "Percentage of turns with tags with double determiners fixed": ((counter_dets_fixed / counter_all_turns) * 100),
        "Turns with blank responses": counter_blank_responses,
        "Percentage of turns with blank responses": ((counter_blank_responses / counter_all_turns) * 100),
        "Turns with hallucinations": counter_hallucinations,
        "Percentage of turns with hallucinations": ((counter_hallucinations / counter_all_turns) * 100)
    }
    dictionary_of_cleaning_reports["ALL DIALOGUES IN THIS EXPERIMENT"] = cleaning_report_contents_alldialogues
    # Write the cleaned output to a new file
    with open(cleaned_file_path, 'w') as cleaned_file:
        json.dump(dictionary_of_cleaned_outputs, cleaned_file, indent=4)
    # Write the cleaning report to a new file
    with open(report_file_path, 'w') as report_file:
        json.dump(dictionary_of_cleaning_reports, report_file, indent=4)




#------------------------------------------------------------------------------------------
# Function toa pply scripts to whole folder of outputs, and to create a cleaning report for each file and overall
def clean_whole_folder(file_of_all_files,folder_path):
    import os
    list_of_files_to_clean = []
    list_of_cleaned_files = []
    list_of_cleaning_reports = []
    for file_name in os.listdir(folder_path):
        # Check that the file does not have a matching _CLEANED.json or _CLEANING-REPORT.json file
        if file_name.endswith("_CLEANED.json"):
            list_of_cleaned_files.append(file_name.replace("_CLEANED",""))
        if file_name.endswith("_CLEANING-REPORT.json"):
            list_of_cleaning_reports.append(file_name.replace("_CLEANING-REPORT",""))
    for file_name in os.listdir(folder_path): 
        if file_name.endswith(".json") and not file_name.endswith("_CLEANED.json") and not file_name.endswith("_CLEANING-REPORT.json") and not file_name in list_of_cleaned_files:
            file_path = os.path.join(folder_path, file_name)
            list_of_files_to_clean.append(file_path)
            #print(f"About to clean {file_path}")
            clean_output_file(file_path)
    return list_of_files_to_clean


if __name__ == "__main__":
	file_of_all_files = 'path/to/list_with_all_dialogue_excel_and_json_files.txt' # Replace with the path to the txt file containing tuples of (excel, dialogue json) for all dialogues
	folder_path = 'path/of/outputs_to_clean' # Replace with the path to the folder containing the output files to clean
	cleaned_files = clean_whole_folder(file_of_all_files,folder_path)