import json
from SPACY_SPAN_EXPANDER import convert_tagged_heads_to_mentions
from MENTION_DETECTION_EVALUATION import evaluate_mention_detection
from CONVERT_DEFAULTDICT import convert_to_regular_dict
from EVALUATE_CLEANED_FILES import compare_evaluations, convert_json_to_excel, evaluate_cleaned_files
from CLEAN_OUTPUT import clean_output_file
from collections import defaultdict
from datetime import datetime
import os
import re
import ast
import spacy
import re

loaded_model = spacy.load("en_core_web_sm") 



def process_intermediary_output(list_of_intermediary_files, loaded_model):
    # I need to store the files in a list to then also apply the cleaning post-processing
    list_of_dirty_spacyed_files = []

    #----------------------------------------------------------------------
    # CONVERTING HEADS TO SPANS
    for file in list_of_intermediary_files:
        # Create dictionary for storing processed data
        processed_data = {}
        # Load the json file
        with open(file, 'r') as f:
            intermediary_data = json.load(f)
        # Process each turn
        for dialogue in intermediary_data:
            processed_data[dialogue] = {}
            for turn in intermediary_data[dialogue]:
                # Convert the contents of the turn
                converted_text = convert_tagged_heads_to_mentions(intermediary_data[dialogue][turn], loaded_model)
                # Store the converted text in the processed data dictionary
                processed_data[dialogue][turn] = converted_text
        # Save the processed data to a new json file with indentation
        # Get the approach shorthand to add SPACYED to it
        approach_shorthand_pattern = re.compile(r'.+\\(.+?)-(?:(?:GPT)|(?:L3))')
        approach_shorthand = re.search(approach_shorthand_pattern,file).group(1) 
        new_approach_shorthand = approach_shorthand + "SPACYED"
        output_file = file.replace(approach_shorthand, new_approach_shorthand)
        with open(output_file, 'w') as f:
            json.dump(processed_data, f, indent=4)
        list_of_dirty_spacyed_files.append(output_file)
    return list_of_dirty_spacyed_files

def evaluate_spacyed_files(list_of_dirty_spacyed_files, evaluation_folder):
    for file in list_of_dirty_spacyed_files:
        #----------------------------------------------------------------------
        # EVALUATING OUTPUT
        dictionary_of_evaluations = defaultdict(dict)
        # Extract experiment parameters from filename
        # --> approach_shorthand
        approach_shorthand_pattern = re.compile(r'.+\\(.+?)-(?:(?:GPT)|(?:L3))')
        approach_shorthand = re.search(approach_shorthand_pattern,file).group(1)   
        # --> model_shorthand
        model_shorthand_pattern = re.compile(r'(((L3)|(GPT)).+?)_') #with lazy quantifer +?
        model_shorthand = re.search(model_shorthand_pattern,file).group(1)  
        # --> number_of_folds    
        number_of_folds_pattern = re.compile(r'\d+-in-(\d+)-FOLDS')
        number_of_folds = re.search(number_of_folds_pattern,file).group(1)
        # --> evaluation_split_percentage
        evaluation_split_percentage_pattern = re.compile(r'_(\d+)-SPLIT')
        evaluation_split_percentage = re.search(evaluation_split_percentage_pattern,file).group(1) 
        # --> number_of_few_shot_examples
        number_of_few_shot_examples_pattern = re.compile(r'_(\d+)_FS')
        number_of_few_shot_examples = re.search(number_of_few_shot_examples_pattern,file).group(1)

        print(f"Evaluating {file}...")
        # Evaluate the mention detection results
        precision, recall, f1_score, true_positives_ids, false_positives_with_indexes, false_negatives_ids, turns_included_in_evaluation, all_positives_with_indexes = evaluate_mention_detection(file)
        #print(f"The turns included in evaluation, as extracted in the pipeline code are: {turns_included_in_evaluation}")
        output_file_basename = os.path.basename(file)
        dictionary_of_evaluations[output_file_basename] = {
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "true_positives_ids": true_positives_ids,
            "false_positives_with_indexes": false_positives_with_indexes,
            "false_negatives_ids": false_negatives_ids,
            "turns_included_in_evaluation": turns_included_in_evaluation,
            "all_positives_with_indexes": all_positives_with_indexes
            }
        # Save the evaluation results to a JSON file
        evaluation_report_filename = f'{approach_shorthand}-{model_shorthand}_{number_of_folds}-FOLDS_{evaluation_split_percentage}-SPLIT_{number_of_few_shot_examples}_FS_evaluation_report.json'
        evaluation_report_filepath = os.path.join(evaluation_folder, evaluation_report_filename)
        # If the file already exists because another fold has been evaluated, append the new results
        evaluation_report_filepath = os.path.join(evaluation_folder, evaluation_report_filename)
        if os.path.exists(evaluation_report_filepath):
            with open(evaluation_report_filepath, 'r', encoding='utf-8') as eval_file:
                existing_evaluations = json.load(eval_file)
            existing_evaluations.update(convert_to_regular_dict(dictionary_of_evaluations))
            dictionary_of_evaluations = existing_evaluations
        with open(evaluation_report_filepath, 'w', encoding='utf-8') as eval_file:
            json.dump(convert_to_regular_dict(dictionary_of_evaluations), eval_file, indent=4)
    return list_of_dirty_spacyed_files

def main(md_output_folder, evaluation_folder):
	# FILES TO PROCESS
	list_of_intermediary_files = []
	for file in os.listdir(md_output_folder):
		list_of_intermediary_files.append(os.path.join(md_output_folder, file))

	# PROCESS FILES
	list_of_dirty_spacyed_files = process_intermediary_output(list_of_intermediary_files, loaded_model)

	# EVALUATE FILES
	list_of_dirty_spacyed_files_after_evaluation = evaluate_spacyed_files(list_of_dirty_spacyed_files, evaluation_folder)

	# CLEAN FILES
	# Now I need to clean the output and re-evaluate
	for file in list_of_dirty_spacyed_files_after_evaluation:
		clean_output_file(file)

	# EVALUATE CLEANED FILES
	set_of_cleaned_evaluation_reports = evaluate_cleaned_files(list_of_dirty_spacyed_files_after_evaluation)

	# COMPARE EVALUATIONS
	comparison_json_path = compare_evaluations(set_of_cleaned_evaluation_reports)
	convert_json_to_excel(comparison_json_path)
     
if __name__ == "__main__":
	evaluation_folder = 'path/to/evaluation_folder' # Replace this with the path to the folder where you want to store the evaluation reports
	md_output_folder = 'path/to/md_outputs' # Repalce this with the path to the folder where the mention detection outputs are stored in an experiment doing mention-head detection
	main(md_output_folder, evaluation_folder)