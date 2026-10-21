# Mention detection with AWS
# Input: dialogue turn from dialogue json + few-shot examples
# Alternative: IDEAL few-shot example instead of random

from CONVERT_TURN_TO_FEW_SHOT_FOR_MD_SIMBASED_EVAL import select_dialoguebased_few_shot_turn_and_evaluation_split_eval
from CALL_GPT import mention_detection_with_gpt
from CALL_BEDROCK import mention_detection_with_aws
from MENTION_DETECTION_EVALUATION import evaluate_mention_detection
from collections import defaultdict
from CONVERT_DEFAULTDICT import convert_to_regular_dict
from EVALUATE_MD_WITH_MIN import evaluate_whole_experiment
import ast
import os
from datetime import datetime
import time
from openai import OpenAI
import boto3
from botocore.exceptions import ClientError
import json
from collections import defaultdict
import random
import re
import pandas as pd
import spacy
nlp = spacy.load('en_use_lg')
import spacy
import re
import os
import pandas as pd
from collections import Counter
model_for_span_changing = spacy.load("en_core_web_sm")


#  ----------------------------------------------
# Extract turns with transcripts in the dev set, to be used for few-shot example retrieval
def extract_turns_with_transcript_for_all_dialogues(list_of_excels_and_dialoguejsons):
    dictionary_of_dev_turns_with_transcript = {}
    for excel, dialoguejson in list_of_excels_and_dialoguejsons:
        with open(dialoguejson, 'r', encoding='utf-8') as file:
            data_of_this_dialogue = json.load(file)
        dialogue_number = data_of_this_dialogue["SESSION"]["sessionID"]
        # Iterate through the turns to get all possible turns with transcript (no silent turns with just typing)
        turns_with_transcript_list = []
        for turn in data_of_this_dialogue["SESSION"]["TURNS"]:
            try:
                turn["TURN"]["TRANSCRIPT"]
                turn_ID = turn["TURN_ID"]
                turns_with_transcript_list.append(turn_ID)
            except:
                pass
        dictionary_of_dev_turns_with_transcript[dialogue_number] = turns_with_transcript_list
    return dictionary_of_dev_turns_with_transcript
# Extract query points and few-shot examples from the dialogue jsons and excel files
def extract_folds(file_of_dev_files, file_of_eval_files, number_of_few_shot_examples,dictionary_of_dev_turns_with_transcript):
	list_of_excels_and_dialoguejsons_eval = file_of_eval_files
	with open(list_of_excels_and_dialoguejsons_eval, 'r') as file:
		content_eval = file.read()
	list_of_excels_and_dialoguejsons_eval = ast.literal_eval(content_eval)

	list_of_excels_and_dialoguejsons_dev = file_of_dev_files
	with open(list_of_excels_and_dialoguejsons_dev, 'r') as file:
		content_dev = file.read()
	list_of_excels_and_dialoguejsons_dev = ast.literal_eval(content_dev)
	# Compile the few-shot examples and evaluation turns for each fold.
	if dev_or_test == "test":
		folds = select_dialoguebased_few_shot_turn_and_evaluation_split_eval(doing_mention_head_detection, model_for_span_changing, list_of_excels_and_dialoguejsons_dev, list_of_excels_and_dialoguejsons_eval, number_of_few_shot_examples,dictionary_of_dev_turns_with_transcript)
		print(f"Number of folds is {len(folds)}")
		return folds


# ----------------------------------------------
# Main function
# ----------------------------------------------
# Set evaluation_or_whole_pipeline = to 'evaluation' to only evaluate existing outputs, or 'whole' to run the whole inference-evaluation pipeline
def md_pipeline(evaluation_or_whole_pipeline):
	folds = extract_folds(file_of_dev_files, file_of_eval_files, number_of_few_shot_examples,turns_with_transcript_in_dev_json)
	# -----------------------------------------
	if evaluation_or_whole_pipeline == 'whole':
		# Load the system prompt file
		with open(system_prompt_file, 'r', encoding='utf-8') as file:
			content = file.read()
		system_prompt_content = ast.literal_eval(content)
		# Obtain the output
		dictionary_of_fs_selected = {}
		for index, fold in enumerate(folds):
			name_of_fold = fold[0][0] # Check the first turn in the fold, and check its first field to find the dialogue number
			name_of_fold = name_of_fold.replace("-","x").replace("_","x").replace("&","x").replace("X","x") # Make format consisstent and avoid -/_ lest it messes with future regex
			output_dictionary = defaultdict(dict)
			print(f"Processing fold {name_of_fold}...")
			output_filename = f'{approach_shorthand}-{model_shorthand}_{name_of_fold}-in-{number_of_folds}-FOLDS_{evaluation_split_percentage}-SPLIT_{number_of_few_shot_examples}_FS_{run_no}.json'
			output_filepath = os.path.join(output_folder, output_filename)
			# Initialise coutners about model performance and usage
			fold_inference_time = 0
			fold_input_tokens = 0
			fold_output_tokens = 0
			fold_total_tokens = 0
			for ev_turn in fold:
				#time.sleep(3)
				input_dialogue_number = ev_turn[0]
				input_turn_id = ev_turn[1]
				input_transcript = ev_turn[2]
				fs_examples = ev_turn[3]
				dictionary_of_fs_selected[input_turn_id] = fs_examples
				print(f"Processing evaluation turn: Dialogue {input_dialogue_number}, Turn ID {input_turn_id}")
				if 'gpt' in model_id.lower():
					model_output, turn_inference_time, input_tokens, output_tokens,total_tokens = mention_detection_with_gpt(key_path, input_transcript, fs_examples, model_id, system_prompt_content, temperature, top_p,max_tokens)
				else:
					model_output, turn_inference_time, input_tokens, output_tokens = mention_detection_with_aws(input_transcript, fs_examples, model_id,system_prompt_content, temperature, top_p,max_tokens)
				fold_inference_time += turn_inference_time  # Accumulate inference time for the fold
				fold_input_tokens += input_tokens  # Accumulate input tokens for the fold
				fold_output_tokens += output_tokens  # Accumulate output tokens for the fold
				fold_total_tokens += total_tokens  # Accumulate total tokens for the fold
				output_dictionary[input_dialogue_number][input_turn_id] = model_output
			print(f"Fold {index + 1} processed. Inference time: {fold_inference_time:.2f} seconds, Input tokens: {fold_input_tokens}, Output tokens: {fold_output_tokens}, Total tokens: {fold_total_tokens}")
			# Save this fold to a file
			with open(output_filepath, 'w', encoding='utf-8') as output_file:
				json.dump(convert_to_regular_dict(output_dictionary), output_file, ensure_ascii=False, indent=4)
			# Save the FS example data
			fs_filepath_name = f'FS EXAMPLES - {approach_shorthand}-{model_shorthand}_{index+1}-in-{number_of_folds}-FOLDS_{evaluation_split_percentage}-SPLIT_{number_of_few_shot_examples}_FS_{run_no}.json' 
			fs_filepath = os.path.join(fs_filepath_folder,fs_filepath_name)
			with open(fs_filepath, 'w', encoding='utf-8') as fs_file:
				json.dump(dictionary_of_fs_selected, fs_file, ensure_ascii=False, indent=4)
			# Save the metadata about the fold
			output_metadata_filename = f'METADATA - {approach_shorthand}-{model_shorthand}_{index+1}-in-{number_of_folds}-FOLDS_{evaluation_split_percentage}-SPLIT_{number_of_few_shot_examples}_FS_{run_no}.json'    

			output_metadata_filepath = os.path.join(metadata_folder, output_metadata_filename)
			metadata_dictionary = {
				'model_id': model_id,
				'temperature': temperature,
				'top_p': top_p,
				'max_tokens': max_tokens,
				'model_shorthand': model_shorthand,
				'approach_shorthand': approach_shorthand,
				'system_prompt_content': system_prompt_content,
				'number_of_folds': number_of_folds,
				'current_fold': index + 1,
				'evaluation_split_percentage': evaluation_split_percentage,
				'number_of_few_shot_examples': number_of_few_shot_examples,
				'fold_inference_time': fold_inference_time,
				'fold_input_tokens': fold_input_tokens,
				'fold_output_tokens': fold_output_tokens,
				'fold_total_tokens': fold_total_tokens,
				'fold_total_turns': len(fold),
				'fold_turns_used': set((ev_turn[0], ev_turn[1]) for ev_turn in fold)
			}

			with open(output_metadata_filepath, 'w', encoding='utf-8') as metadata_file:
				json.dump(convert_to_regular_dict(metadata_dictionary), metadata_file, ensure_ascii=False, indent=4)
	# --------------------------------------------------------------------------------------------------------------

	# Evaluate each output JSON file
	dictionary_of_evaluations = defaultdict(dict)
	file_beginning = f'{approach_shorthand}-{model_shorthand}'
	file_end = f'-in-{number_of_folds}-FOLDS_{evaluation_split_percentage}-SPLIT_{number_of_few_shot_examples}_FS_{run_no}.json'
	for output_file in os.listdir(output_folder):
		if output_file.endswith(file_end) and output_file.startswith(file_beginning):
			output_json_file = os.path.join(output_folder, output_file)
			print(f"Evaluating {output_json_file}...")
			# Evaluate the mention detection results
			precision, recall, f1_score, true_positives_ids, false_positives_with_indexes, false_negatives_ids, turns_included_in_evaluation, all_positives_with_indexes = evaluate_mention_detection(list_of_GT_files,output_json_file)
			#print(f"The turns included in evaluation, as extracted in the pipeline code are: {turns_included_in_evaluation}")
			dictionary_of_evaluations[output_file] = {
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
	evaluation_report_filename = f'{approach_shorthand}-{model_shorthand}_{number_of_folds}-FOLDS_{evaluation_split_percentage}-SPLIT_{number_of_few_shot_examples}_FS_evaluation_report_FIXED_{run_no}.json'
	evaluation_report_filepath = os.path.join(evaluation_folder, evaluation_report_filename)
	with open(evaluation_report_filepath, 'w', encoding='utf-8') as eval_file:
		json.dump(convert_to_regular_dict(dictionary_of_evaluations), eval_file, indent=4)
	
	# Evaluate the whole experiment with minimum spans
	evaluate_whole_experiment(output_folder, model_shorthand, approach_shorthand, evaluation_folder, model_for_span_changing, list_of_GT_files)

if __name__ == "__main__":
	# -------------------------------------------------------------------------------------
	# PARAMETERS
	# -------------------------------------------------------------------------------------
	key_path = 'path/to/API_key.txt' # Path to txt file containing the Open AI API key for the model being used; Bedrock does not require the key directly as it is set up with AWS credentials
	dev_or_test = 'test'  # Set to 'dev' for development files, 'test' for test files
	file_of_eval_files = 'path/to/eval_files.txt' # Path to txt file containing tuples of (excel file path, dialogue json path) for the evaluation dialogues
	file_of_dev_files = 'path/to/dev_files.txt' # Path to txt file containing tuples of (excel file path, dialogue json path) for the development dialogues. Will be used to few-shot examples
	list_of_GT_files = 'path/to/ground_truth_mentions.txt' # Path to txt file containing tuples of (excel file path, mention json path) with the ground-truth annotations, to be used for evaluation
	system_prompt_file = 'path/to/system_prompt.txt' # Path to the system prompt file, which should be a text file containing a dictionary with the system prompt content
	turns_with_transcript_in_dev_json = r'TURNS WITH TRANSCRIPTS-DEV.json' # Turns in the dev set that have transcripts

	# Define the output folders
	output_folder = 'path/to/output_folder'  # Update this to your desired output folder path
	evaluation_folder = 'path/to/evaluation_folder'  # Update this to your desired evaluation report folder path
	metadata_folder = 'path/to/metadata_folder'  # Update this to your desired metadata folder path
	fs_filepath_folder = 'path/to/fs_examples_folder' # Update this to your desired few-shot examples folder path

	# Model parameters
	run_no = "RUN1" # Replace this with a unique identifier for the run
	model_id= "gpt-4.1" # Replace this with official API model ID
	model_shorthand = "GPT4point1FULL" # Replace this with a shorthand for the model, to be used in file names and reports (so avoice dots and spaces that might mess with file names)
	temperature = 0
	temperature_shorthand = "00"
	top_p = 0.5
	max_tokens = 512

	# Approach parameters
	number_of_few_shot_examples = 3  
	approach_shorthand = 'sim_based_fs'  # Shorthand for the approach, to be used in file names and reports
	doing_mention_head_detection = False # Set to True if doing mention-head detection, False if doing mention detection. 
	# This will affect the format of the few-shot examples that are retrieved (tagged transcripts for mention detection, vs tagged heads for mention-head detection)
	# It will however not affect the evaluation, which is set for metnion detection. The mention-head detection evaluation script will need to be run separately after.

	# Data split. Replace with 'dialogues' when splitting by dev/eval dialogues instead of by turns
	evaluation_split_percentage = "25"  # Percentage of turns to be used for evaluation
	number_of_folds = "5"

	evaluation_or_whole_pipeline='whole'# Set to 'evaluation' to only evaluate existing outputs, or 'whole' to run the whole inference-evaluation pipeline
	# -------------------------------------------------------------------------------------

	md_pipeline(evaluation_or_whole_pipeline)
