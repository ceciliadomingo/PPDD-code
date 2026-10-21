import json
from collections import defaultdict
from MENTION_DETECTION_EVALUATION import evaluate_mention_detection
from CONVERT_DEFAULTDICT import convert_to_regular_dict
import os
from datetime import datetime
import re
import statistics
import pandas as pd
import ast

def evaluate_cleaned_files(folder_with_cleaned_files, evaluation_folder):
	set_of_cleaned_evaluation_reports = set() # Set to store the report filepahts to use in later functions
	for file in os.listdir(folder_with_cleaned_files):
		if 'CLEANED' in file:
			dictionary_of_evaluations = defaultdict(dict)
			# Define the filename of the evaluation report
			# --> approach_shorthand
			approach_shorthand_pattern = re.compile(r'.+\\(.+?)-(?:(?:GPT)|(?:L3))')
			approach_shorthand = re.search(approach_shorthand_pattern,file).group(1)   
			#print(f"Approach shorthand: {approach_shorthand}")
			# --> model_shorthand
			model_shorthand_pattern = re.compile(r'(((L3)|(GPT)).+?)_') #with lazy quantifer +? not to get the full file name
			model_shorthand = re.search(model_shorthand_pattern,file).group(1)  
			#print(f"Model shorthand: {model_shorthand}")
			# --> number_of_folds    
			number_of_folds_pattern = re.compile(r'_.+-in-(.+)-FOLDS')
			number_of_folds = re.search(number_of_folds_pattern,file).group(1)
			#print(f"Number of folds: {number_of_folds}")
			# --> evaluation_split_percentage
			evaluation_split_percentage_pattern = re.compile(r'.+_(.+?)-SPLIT')#with lazy quantifer +? not to get the full file name
			evaluation_split_percentage = re.search(evaluation_split_percentage_pattern,file).group(1)
			#print(f"Evaluation split percentage: {evaluation_split_percentage}")
			# --> number_of_few_shot_examples
			number_of_few_shot_examples_pattern = re.compile(r'.+_(.+?)_FS')#with lazy quantifer +? not to get the full file name
			number_of_few_shot_examples = re.search(number_of_few_shot_examples_pattern,file).group(1)
			#print(f"Number of few-shot examples: {number_of_few_shot_examples}")
			# Perform evaluation
			print(f"Evaluating {file}...")
			precision, recall, f1_score, true_positives_ids, false_positives_with_indexes, false_negatives_ids, turns_included_in_evaluation, all_positives_with_indexes = evaluate_mention_detection(file)
			filename_without_path = os.path.basename(file)
			dictionary_of_evaluations[filename_without_path] = {
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
			evaluation_report_filename = f'{approach_shorthand}-{model_shorthand}_{number_of_folds}-FOLDS_{evaluation_split_percentage}-SPLIT_{number_of_few_shot_examples}_FS_evaluation_report_CLEANED.json'
			# If the file already exists because another fold has been evaluated, append the new results
			evaluation_report_filepath = os.path.join(evaluation_folder, evaluation_report_filename)
			if os.path.exists(evaluation_report_filepath):
				with open(evaluation_report_filepath, 'r', encoding='utf-8') as eval_file:
					existing_evaluations = json.load(eval_file)
				existing_evaluations.update(convert_to_regular_dict(dictionary_of_evaluations))
				dictionary_of_evaluations = existing_evaluations
			with open(evaluation_report_filepath, 'w', encoding='utf-8') as eval_file:
				json.dump(convert_to_regular_dict(dictionary_of_evaluations), eval_file, indent=4)
			set_of_cleaned_evaluation_reports.add(evaluation_report_filepath)
	return set_of_cleaned_evaluation_reports




#------------------------------------------------------------------------------------------
# COMPARISON OF EVALUATIONS
def extract_data_from_eval_report(eval_report_path):
    # Data extracted from filename:
    # --> Model
    model_shorthand_pattern = re.compile(r'(((L3)|(GPT)).+?)_') #with lazy quantifer +?
    model_shorthand = re.search(model_shorthand_pattern,eval_report_path).group(1)  
    # --> Approach
    approach_shorthand_pattern = re.compile(r'.+\\(.+?)-(?:(?:GPT)|(?:L3))')
    approach_shorthand = re.search(approach_shorthand_pattern,eval_report_path).group(1) 
    # --> Total folds
    number_of_folds_pattern = re.compile(r'_(.+)-FOLDS')
    number_of_folds = re.search(number_of_folds_pattern,eval_report_path).group(1)
    # --> Eval split
    evaluation_split_percentage_pattern = re.compile(r'_(.+)-SPLIT')
    evaluation_split_percentage = re.search(evaluation_split_percentage_pattern,eval_report_path).group(1) 
    # --> No FS
    number_of_few_shot_examples_pattern = re.compile(r'_(\d+)_FS')
    number_of_few_shot_examples = re.search(number_of_few_shot_examples_pattern,eval_report_path).group(1)

    with open(eval_report_path, 'r', encoding='utf-8') as eval_file:
        evaluation_data = json.load(eval_file)
    list_of_precisions_by_fold = []
    list_of_recalls_by_fold = []
    list_of_f1s_by_fold = []
    for fold in evaluation_data:
        list_of_precisions_by_fold.append(evaluation_data[fold]["precision"])
        list_of_recalls_by_fold.append(evaluation_data[fold]["recall"])
        list_of_f1s_by_fold.append(evaluation_data[fold]["f1_score"])
    approach_avg_precision = statistics.mean(list_of_precisions_by_fold)
    approach_avg_recall = statistics.mean(list_of_recalls_by_fold)
    approach_avg_f1 = statistics.mean(list_of_f1s_by_fold)
    # Make sure that there are at least two folds to calculate standard deviation
    # Convert number_of_folds to an integer
    if number_of_folds.isdigit():
        number_of_folds_int = int(number_of_folds)
        if number_of_folds_int < 2:
            approach_std_precision = "NA"
            approach_std_recall = "NA"
            approach_std_f1 = "NA"
        else:
            # I did confirm that stdev works even if all the values are 0
            approach_std_precision = statistics.stdev(list_of_precisions_by_fold)
            approach_std_recall = statistics.stdev(list_of_recalls_by_fold)
            approach_std_f1 = statistics.stdev(list_of_f1s_by_fold)
    else: # If we're in eval phase and number of folds is "dialogues"
        # I did confirm that stdev works even if all the values are 0
        approach_std_precision = statistics.stdev(list_of_precisions_by_fold)
        approach_std_recall = statistics.stdev(list_of_recalls_by_fold)
        approach_std_f1 = statistics.stdev(list_of_f1s_by_fold)
    return model_shorthand, approach_shorthand, number_of_folds, evaluation_split_percentage, number_of_few_shot_examples, approach_avg_precision, approach_avg_recall, approach_avg_f1, approach_std_precision, approach_std_recall, approach_std_f1


def compare_evaluations(set_of_cleaned_evaluation_reports,output_comparison_report_path):
    # Check if comparison json already exists
    if os.path.exists(output_comparison_report_path):
        with open(output_comparison_report_path, 'r', encoding='utf-8') as file:
          data = json.load(file)
        print(f'Comparison file {output_comparison_report_path} already exists. It will be rewritten.')
        print(f"Its current size is {os.path.getsize(output_comparison_report_path)} bytes.")
    else:
        data = {}  
    list_of_dirty_and_clean_reports = []
    for clean_eval_report_path in set_of_cleaned_evaluation_reports:
        clean_eval_report_basename = os.path.basename(clean_eval_report_path)
        beginning_of_filename_pattern = re.compile(r'(.+)_CLEANED')
        #print(f'Looking for dirty report corresponding to {clean_eval_report_basename}')
        beginning_of_filename = re.search(beginning_of_filename_pattern,clean_eval_report_basename).group(1)
        #folder_of_dirty_reports = os.path.dirname(os.path.dirname(clean_eval_report_path)) # I get the folder of the folder of the clean file to get to the dirty folder, the parent folder
        for file in os.listdir(os.path.dirname(clean_eval_report_path)):#os.listdir(folder_of_dirty_reports):
            if file.startswith(beginning_of_filename) and not file.endswith('_CLEANED.json'):
                dirty_eval_report = file
                dirty_eval_report_path = os.path.join(os.path.dirname(clean_eval_report_path), dirty_eval_report)
                break
        list_of_dirty_and_clean_reports.append((dirty_eval_report_path,clean_eval_report_path))
    #print(list_of_dirty_and_clean_reports)
    print(f'Found {len(list_of_dirty_and_clean_reports)} pairs of dirty and clean evaluation reports to compare.')
    for item in list_of_dirty_and_clean_reports:
        dirty_basename = os.path.basename(item[0])
        print(f'Comparing {dirty_basename}')
        model_shorthand, approach_shorthand, number_of_folds, evaluation_split_percentage, number_of_few_shot_examples, approach_avg_precision_dirty, approach_avg_recall_dirty, approach_avg_f1_dirty, approach_std_precision_dirty, approach_std_recall_dirty, approach_std_f1_dirty = extract_data_from_eval_report(item[0])
        model_shorthand, approach_shorthand, number_of_folds, evaluation_split_percentage, number_of_few_shot_examples, approach_avg_precision_clean, approach_avg_recall_clean, approach_avg_f1_clean, approach_std_precision_clean, approach_std_recall_clean, approach_std_f1_clean = extract_data_from_eval_report(item[1])

        # Add data to the json
        data[dirty_basename] = {
            'Model': model_shorthand,
            'Approach': approach_shorthand,
            'Folds': number_of_folds,
            'Eval Split %': evaluation_split_percentage,
            'Few-shot Examples': number_of_few_shot_examples,
            'Avg Precision Dirty': approach_avg_precision_dirty,
            'SD Precision Dirty': approach_std_precision_dirty,
            'Avg Recall Dirty': approach_avg_recall_dirty,
            'SD Recall Dirty': approach_std_recall_dirty,
            'Avg F1 Dirty': approach_avg_f1_dirty,
            'SD F1 Dirty': approach_std_f1_dirty,
            'Avg Precision Clean': approach_avg_precision_clean,
            'SD Precision Clean': approach_std_precision_clean,
            'Avg Recall Clean': approach_avg_recall_clean,
            'SD Recall Clean': approach_std_recall_clean,
            'Avg F1 Clean': approach_avg_f1_clean,
            'SD F1 Clean': approach_std_f1_clean,
            'Change in Precision': (approach_avg_precision_clean - approach_avg_precision_dirty),
            'Change in Recall': (approach_avg_recall_clean - approach_avg_recall_dirty),
            'Change in F1': (approach_avg_f1_clean - approach_avg_f1_dirty)
        }
    # Write the comparison data to a JSON file or rewrite the existing one
    with open(output_comparison_report_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)
    return output_comparison_report_path



# Convert the json to an Excel file
def convert_json_to_excel(json_path):
    # Read the JSON file
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    # Convert the JSON data to a DataFrame
    df = pd.DataFrame.from_dict(data, orient='index')
    # Define the Excel file path
    excel_file_path = json_path.replace('.json', '.xlsx')
    # Save the DataFrame to an Excel file
    df.to_excel(excel_file_path, index=True)
    print(f"Excel file saved at {excel_file_path}")
    return excel_file_path

# ------------------------------------------------------------------------------------------
# Main function to evaluate cleaned files and compare with dirty files, then convert the comparison to Excel
def main(folder_with_cleaned_files, evaluation_folder):
	set_of_cleaned_evaluation_reports = evaluate_cleaned_files(folder_with_cleaned_files, evaluation_folder)
	comparison_json_path = compare_evaluations(set_of_cleaned_evaluation_reports)
	convert_json_to_excel(comparison_json_path)
    
if __name__ == "__main__":
	folder_with_cleaned_files = r'path\to\folder\with\cleaned\files' # Folder where the cleaned evaluation reports are located
	evaluation_folder = r'path\to\evaluation\reports\folder' # Folder where the evaluation reports (both dirty and clean) are located
	main(folder_with_cleaned_files, evaluation_folder)
