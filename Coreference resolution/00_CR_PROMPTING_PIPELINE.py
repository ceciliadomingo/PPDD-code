# Promting pipeline
# It needs the QP extraction functions
# After each QP is created, it's stored and fed to the LLM
# The LLM output is stored, and another function adapts the outupt to feed the next QP
# So we use a running json file with the predicted chains so far that keeps getting updated



# EXPERIMENT PARAMETERS
# Context window size: how many previous turns to include in the context (10-30-55-100), COST-BENEFIT
# Model: gpt-4o-mini, gpt-4o, gpt-4.1, gpt_4.1-mini, gpt-5, gpt-5-mini, Llama 8B, Llama 70B COST-BENEFIT
# Multimodality: no keylog records, only text keylog, only screenshot-based info, both keylog and screenshot info, only actual image COST-BENEFIT



from CR_QP_EXTRACTION import cursor_color_extractor, code_and_keylog_retriever, get_cursor_tagged_code, mentions_extractor_from_annotations, dialogue_history_extractor, mention_tag_extractor
from SCREENSHOT_PROCESSING import convert_timestamp_to_seconds, find_resolution
from EVALUATION_CONLL import locate_annotator_json, extract_dict_of_GT_clusters, ceaf_precision_hungarian, ceaf_recall_hungarian, b3_precision, b3_recall, muc_precision, muc_recall, f1
from CLEANING_SCRIPTS import clean_cr_output
import json
import os
import re
import pandas as pd
import regex # for recursive expressions
from openai import OpenAI
import boto3
from botocore.exceptions import ClientError
from time import time
dialogue_number_regex = re.compile(r'\d\d\d[xX-_&]\d\d\d')	

############################################################################################################
# PARAMETERS
# make sure jsons are before excels in tuples
list_of_dialogue_jsons_and_excels = [('example_dialogue.json', 'example_annotation.xlsx')] # Replace with dialogue files
# Location of multimodal data
cursor_color_registry = r'Cursor_colors.xlsx'
folder_trimmed_keylog_and_code = 'path/to/trimmed_keylog_and_code' # where the trimmed keylog and code files are stored
folder_tagged_code_states = 'path/to/tagged_code_states' # where the output of the screenshot processing pipeline is stored, i.e. the code states with cursor tags extracted from the screenshots
annotations_folder = 'path/to/annotations_folder' # where the ground-truth annotations are stored
# Output folders
cr_output_folder = 'path/to/cr_outputs' # where the raw outputs of the model will be stored
cr_results_folder = 'path/to/cr_results' # where the evaluation scores will be stored
qp_folder = 'path/to/qp_folder' # where the query points will be stored
folder_chains = 'path/to/chains_folder' # where the coreference chains so far will be stored after each turn
report_folder = 'path/to/report_folder' # where the cleaning reports will be stored
cleaned_output_folder = 'path/to/cleaned_outputs' # where the cleaned outputs will be stored
# Experiment parameters
context_window = 10
model_id = "gpt-4.1-nano" # Replace with API model ID
temperature = 0
top_p = 0.5
max_tokens = 500
multimodality_setting = "N" #  Multimodality: no keylog records(N), only text keylog(K), only screenshot-based info(S), both keylog and screenshot info(KS)
dialogue_history_setting = "sim" # Dialogue history: simple, only transcripts (sim), detailed (det)
model_shorthand = model_id.replace(".","").replace("-","")
system_prompt = 'DEFINE YOUR SYSTEM PROMPT'
whole_or_eval_only = "whole" # Set to "whole" for whole pipeline or "eval" to evaluate existing outputs
# Compiling the parameters into an approach name for file naming purposes
approach = f"{model_shorthand}_CW{context_window}_DH-{dialogue_history_setting}_MU-{multimodality_setting}_T{temperature}_{str(top_p).replace(".", "")}_MT{max_tokens}"



############################################################################################################
############################################################################################################
############################################ FUNCTIONS #####################################################
############################################################################################################
############################################################################################################

def prompt_gpt_cr(key_path, system_prompt, user_prompt, model_id, temperature, top_p,max_tokens):
    start_time = time()  # Start the timer for inference time measurement
	 # Initialize OpenAI client
    with open(key_path, 'r') as file: #Path to where your API key is stored as a .txt file
        key = file.read().strip()
    client = OpenAI(api_key=key)
    
	# Embed the prompt in GPT's instruction format and obtain a response
    response = client.chat.completions.create(model=model_id,
        messages=[
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": str(user_prompt)}
      ], temperature=temperature, max_completion_tokens=max_tokens)#top_p=top_p, max_completion_tokens=max_tokens) # GPT5 does not allow op_p
    response_text = response.choices[0].message.content
    # Extract token usage
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    total_tokens = response.usage.total_tokens
    reasoning_tokens = response.usage.completion_tokens_details.reasoning_tokens
    end_time = time()  # End the timer
    turn_inference_time = end_time - start_time  # Calculate inference time
    model_signature = response.model
    #whole_response = response
    return response_text, turn_inference_time, input_tokens, output_tokens, total_tokens, reasoning_tokens, model_signature

def prompt_llama_cr(system_prompt, user_prompt, model_id, temperature, top_p,max_tokens):
	start_time = time()  # Start the timer for inference time measurement
	# Create a Bedrock Runtime client in the specified AWS Region.
	client = boto3.client("bedrock-runtime", region_name="eu-west-2")
	# Embed the prompt in Llama 3's instruction format.
	formatted_prompt = f"""
	<|begin_of_text|><|start_header_id|>system<|end_header_id|>
	{system_prompt}
	<|eot_id|>
	<|start_header_id|>user<|end_header_id|>
	{user_prompt}
	<|eot_id|>
	<|start_header_id|>assistant<|end_header_id|>
	"""

	# Format the request payload using the model's native structure.
	native_request = {
		"prompt": formatted_prompt,
		"max_gen_len": max_tokens,
		"temperature": temperature,
		"top_p": top_p
	}
	# Convert the native request to JSON.
	request = json.dumps(native_request)
	try:
		# Invoke the model with the request.
		response = client.invoke_model(modelId=model_id, body=request)
	except (ClientError, Exception) as e:
		print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
		exit(1)
    # Decode the response body.
	model_response = json.loads(response["body"].read())
	# Extract the token information from the response.
	headers = response['ResponseMetadata']['HTTPHeaders']
	input_tokens = int(headers.get('x-amzn-bedrock-input-token-count', 0))
	output_tokens = int(headers.get('x-amzn-bedrock-output-token-count', 0))
	total_tokens = input_tokens + output_tokens
	reasoning_tokens = 0
	# Extract and print the response text.
	response_text = model_response["generation"]
	end_time = time()  # End the timer
	turn_inference_time = end_time - start_time  # Calculate inference time
	model_signature = model_id
	return response_text, turn_inference_time, input_tokens, output_tokens, total_tokens, reasoning_tokens, model_signature



def chain_updater(chains_so_far, response_text, original_tagged, turn_id, speaker):
	cleaned_response, cleaning_report = clean_cr_output(response_text, original_tagged, dialogue_number_in_files, approach, turn_id, report_folder)
	list_of_tuples_mentions_this_turn = [] # Here I store the mentions returned by the model with all their details
	chain_regex = regex.compile(r"<M>(?:[^<]+|<(?!/?M|C\d+/M>)|(?R))*</C\d+M>")
	chains_found = chain_regex.findall(cleaned_response, overlapped=True) # Overlapped allows (?R) to capture the nested structures with recursion
	chain_number_pattern = re.compile(r'<\/C(\d+)M>')
	response_cleaned_of_C = re.sub(chain_number_pattern, "", cleaned_response)
	response_no_m = response_cleaned_of_C.replace("</M>", "").replace("<M>", "")
	for chain_found in chains_found:
		chain_numbers_found = chain_number_pattern.findall(chain_found)
		number_broader_chain = chain_numbers_found[-1] # I start fromt he end to get the number of the broader chain in case of nested chains 
		# (e..g, 3 in 'I said <M>Take <M>my bag of <M>rocks</C2M></C1M>, my dear</C3M>')
		mention_cleaned_of_C = re.sub(chain_number_pattern, "", chain_found)
		mention_cleaned = mention_cleaned_of_C.replace("</M>", "").replace("<M>", "")
		span_start = response_no_m.find(mention_cleaned)
		span_end = span_start + len(mention_cleaned)
		list_of_tuples_mentions_this_turn.append((int(number_broader_chain), turn_id, mention_cleaned, span_start, span_end, speaker))
	# Now I use the tuples to update the chains file. I check if a chain exists and if so update it. If not, I create a new one.
	chain_numbers_existing = [chain["CHAIN ID"] for chain in chains_so_far]
	for mention_tuple in list_of_tuples_mentions_this_turn:
		chain_number = mention_tuple[0]
		if chain_number in chain_numbers_existing:
			for chain in chains_so_far:
				if chain["CHAIN ID"] == chain_number:
					chain["MENTIONS"].append({
						"TURN ID": mention_tuple[1],
						"MENTION": mention_tuple[2],
						"MENTION START": mention_tuple[3],
						"MENTION END": mention_tuple[4],
						"SPEAKER": mention_tuple[5]
					})
					break
		else:
			new_chain = {
				"CHAIN ID": chain_number,
				"MENTIONS": [{
					"TURN ID": mention_tuple[1],
					"MENTION": mention_tuple[2],
					"MENTION START": mention_tuple[3],
					"MENTION END": mention_tuple[4],
					"SPEAKER": mention_tuple[5]
				}]
			}
			chains_so_far.append(new_chain)
	return chains_so_far, cleaned_response

def CR_prompter(dialogue_number):
	# Check if dict of qps exists, otherwise create it
	if f'QPs_{dialogue_number}_{approach}.json' in os.listdir(qp_folder):
		with open(os.path.join(qp_folder, f'QPs_{dialogue_number}_{approach}.json'), 'r') as f:
			dict_of_qps = json.load(f)
	else:
		dict_of_qps = {}
	# Check if dict of outputs exists, otherwise create it
	if f'Outputs_{dialogue_number}_{approach}.json' in os.listdir(cr_output_folder):
		with open(os.path.join(cr_output_folder, f'Outputs_{dialogue_number}_{approach}.json'), 'r') as f:
			dict_of_outputs = json.load(f)
	else:
		dict_of_outputs = {}
	for dialogue_json, annotation_excel in list_of_dialogue_jsons_and_excels:
		# Initialize counters
		total_inference_time = 0
		total_input_tokens = 0
		total_output_tokens = 0
		total_reasoning_tokens = 0
		# Initialise file of cleaned outputs 
		clean_outputs = {}
		dialogue_number_match = re.search(dialogue_number_regex, dialogue_json)
		dialogue_number_in_files = dialogue_number_match.group().replace("X","x").replace("-","x").replace("_","x").replace("&","x")
		if dialogue_number_in_files == dialogue_number:
			cursor_colours = cursor_color_extractor(dialogue_number, cursor_color_registry) # color A, color B
			speaker_a, speaker_b = dialogue_number.split("x")
			with open(dialogue_json, 'r') as f:
				dialogue_json_data = json.load(f)
			# Initialise chains for this dialogue
			chains_so_far = []
			for turn in dialogue_json_data["SESSION"]["TURNS"]:
				# TURN ID
				turn_id = turn["TURN_ID"] # int
				print(f"Processing dialogue {dialogue_number}, turn {turn_id}")
				# TRANSCRIPT
				try:
					transcript = turn["TURN"]["TRANSCRIPT"]
				except KeyError:
					print(f"Turn {turn_id} has no transcript")
					continue # Skip to the next turn if no transcript
				# SPEAKER DETAILS
				speaker = turn["TURN"]["DIARIZATION"]["SPEAKER"]
				if speaker == speaker_a:
					current_cursor_color = cursor_colours[0]
				if speaker == speaker_b:
					current_cursor_color = cursor_colours[1]
				# TIME
				time_start = turn["TURN"]["TIME"]["START"]
				time_end = turn["TURN"]["TIME"]["END"]
				# KEYLOG
				code_state, keylog_record = code_and_keylog_retriever(dialogue_number, turn_id, folder_trimmed_keylog_and_code,time_start,time_end) # str
				# SCREEN
				screen_resolution_a, screen_resolution_b = find_resolution(speaker_a, speaker_b) #int tuple
				if speaker == speaker_a:
					speaker_matched_resolution = screen_resolution_a
				if speaker == speaker_b:
					speaker_matched_resolution = screen_resolution_b
				screenshot_data = get_cursor_tagged_code(dialogue_number, time_start, time_end, folder_tagged_code_states) #str
				# MULTIMODALITY
				if multimodality_setting == "N":
					multimodality = {"Code state": code_state}
				elif multimodality_setting == "K":
					multimodality= {"Code state": code_state, "Keylog record": keylog_record}
				elif multimodality_setting == "KS" or multimodality_setting == "SK":
					multimodality = {"Speaker's cursor colour": current_cursor_color,
					"Screen resolution": speaker_matched_resolution,
					"Current state of code, with cursor tags": screenshot_data,
					"Keylog record": keylog_record}
				# MENTIONS
				mentions_json = mentions_extractor_from_annotations(dialogue_number, turn_id, annotations_folder) # trimmed df with only the columns: Turn ID, Mention, Mention start, Mention end, Row ID
				mention_tagged_transcript = mention_tag_extractor(mentions_json, transcript) # str
				# DIALOGUE HISTORY
				dialogue_history_det, dialogue_history_only_transcripts = dialogue_history_extractor(dialogue_json_data, turn_id, context_window) # list of strings
				if dialogue_history_setting == "sim":
					dialogue_history_selected = dialogue_history_only_transcripts
				if dialogue_history_setting == "det":
					dialogue_history_selected == dialogue_history_det
				user_prompt = {"Dialogue history": dialogue_history_selected,
				"Speaker": speaker,
				"Multimodal data": multimodality,
				"Coreference chains until this turn": chains_so_far,
				"Transcript tagged with mentions": mention_tagged_transcript  
				}
				dict_of_qps[turn_id] = {
					"System prompt": system_prompt,
					"User prompt": user_prompt
				}

				# PROMPT THE MODEL
				if "gpt" in approach:
					response_text, turn_inference_time, input_tokens, output_tokens, total_tokens, reasoning_tokens, model_signature = prompt_gpt_cr(key_path, system_prompt, user_prompt, model_id, temperature, top_p,max_tokens)
				if "llama" in approach:
					response_text, turn_inference_time, input_tokens, output_tokens, total_tokens, reasoning_tokens, model_signature = prompt_llama_cr(system_prompt, user_prompt, model_id, temperature, top_p,max_tokens)
				# SAVE THE OUTPUT TO OUTPUT FILE
				dict_of_outputs[turn_id] = {"response_text":response_text,
								"turn_inference_time": turn_inference_time,
								"input_tokens": input_tokens,
								"output_tokens": output_tokens,
								"total_tokens": total_tokens,
								"reasoning_tokens": reasoning_tokens,
								"model_signature": model_signature}
				# UPDATE COUNTERS
				total_inference_time += turn_inference_time
				total_input_tokens += input_tokens
				total_output_tokens += output_tokens
				total_reasoning_tokens += reasoning_tokens
				# Save the dict of outputs to f'QPs_{dialogue_number}_{approach}.json'
				outputs_filename = f'Outputs_{dialogue_number}_{approach}.json'
				with open(os.path.join(cr_output_folder, outputs_filename), 'w') as f:
					json.dump(dict_of_outputs, f, indent=4)
				# UPDATE THE CHAINS SO FAR FILE
				# Save a copy of the keys to txt first for QA
				#print(f"TURN ID: {turn_id} -- CHAINS: {chains_so_far}")
				chains_so_far, cleaned_response = chain_updater(chains_so_far, response_text, mention_tagged_transcript, turn_id, speaker)
				print(f"Transcript: {transcript}") # xxx
				print(f"Response: {response_text}") # xxx
				print(f"Cleaned Response: {cleaned_response}") # xxx
				clean_outputs[turn_id] = cleaned_response
				print(f"Updated chains so far now has {len(chains_so_far)} chains")
				total_mentions = sum(len(chain["MENTIONS"]) for chain in chains_so_far)
				print(f"Total mentions so far: {total_mentions}")
				# Save the updated chains dict
				chains_filename = f"CHAINSsofar_{dialogue_number}_{approach}.json"
				with open(os.path.join(folder_chains, chains_filename), "w") as f:
					json.dump(chains_so_far, f, indent=4)
				# Save the dict of QPs as a json file
				filename = f'QPs_{dialogue_number}_{approach}.json'
				with open(os.path.join(qp_folder, filename), 'w') as f:
					json.dump(dict_of_qps, f, indent=4)
			# Save cleaned outputs to a new file
		cleaned_filename = f'Cleaned_Outputs_{dialogue_number_in_files}_{approach}.json'
		with open(os.path.join(cleaned_output_folder, cleaned_filename), 'w+') as f:
			json.dump(clean_outputs, f, indent=4)
	return total_inference_time, total_input_tokens, total_output_tokens, total_reasoning_tokens

def CR_evaluator(dialogue_number, total_inference_time, total_input_tokens, total_output_tokens, total_reasoning_tokens):
	# Gotta convert model output chains to format dict_of_GT_clusters[current_key] = [(turn_ID, mention_text, span_start, span_end)]
	# where current_key is the chain ID
	dict_of_pred_clusters = {}
	for file in os.listdir(folder_chains):
		if approach in file and f'CHAINSsofar_{dialogue_number}_' in file:
			print("found file")
			with open(os.path.join(folder_chains, file), 'r') as f:
				dict_of_output_chains = json.load(f)
			for chain in dict_of_output_chains:
				current_key = chain["CHAIN ID"]
				dict_of_pred_clusters[current_key] = []
				for mention in chain["MENTIONS"]:
					dict_of_pred_clusters[current_key].append((mention["TURN ID"], mention["MENTION"], mention["MENTION START"], mention["MENTION END"]))
	annotator_json = locate_annotator_json(dialogue_number)
	dict_of_GT_clusters = extract_dict_of_GT_clusters(annotator_json)
	ceaf_p = ceaf_precision_hungarian(dict_of_GT_clusters, dict_of_pred_clusters)
	ceaf_r = ceaf_recall_hungarian(dict_of_GT_clusters, dict_of_pred_clusters)
	ceaf_f1 = f1(ceaf_p, ceaf_r)
	b3_p = b3_precision(dict_of_GT_clusters, dict_of_pred_clusters)
	b3_r = b3_recall(dict_of_GT_clusters, dict_of_pred_clusters)
	b3_f1 = f1(b3_p, b3_r)
	muc_p = muc_precision(dict_of_GT_clusters, dict_of_pred_clusters)
	muc_r = muc_recall(dict_of_GT_clusters, dict_of_pred_clusters)
	muc_f1 = f1(muc_p, muc_r)
	# Save results to Excel
	# Open the results Excel file or create a new one if it doesn't exist
	results_excel_path = os.path.join(cr_results_folder, f'CR_Evaluation_Results_{approach}.xlsx')
	if os.path.exists(results_excel_path):
		from openpyxl import load_workbook
		workbook = load_workbook(results_excel_path)
	else:
		from openpyxl import Workbook
		workbook = Workbook()
	# The columns will be:
	# Dialogue Number | CEAF Precision | CEAF Recall | CEAF F1 | B3 Precision | B3 Recall | B3 F1 | MUC Precision | MUC Recall | MUC F1 | Inference time | Input tokens | Output tokens | Reasoning tokens
	sheet_name = 'Results'
	if sheet_name in workbook.sheetnames:
		sheet = workbook[sheet_name]
	else:
		sheet = workbook.create_sheet(sheet_name)
	if sheet.max_row == 1 and sheet.max_column == 1 and sheet['A1'].value is None:
		sheet.append(["Dialogue Number", "CEAF Precision", "CEAF Recall", "CEAF F1", "B3 Precision", "B3 Recall", "B3 F1", "MUC Precision", "MUC Recall", "MUC F1", "Inference time", "Input tokens", "Output tokens", "Reasoning tokens", "Clean CEAF Precision", "Clean CEAF Recall", "Clean CEAF F1", "Clean B3 Precision", "Clean B3 Recall", "Clean B3 F1", "Clean MUC Precision", "Clean MUC Recall", "Clean MUC F1"])
	# Check if the dialogue number already exists in the first column
	dialogue_exists = False
	for row in sheet.iter_rows(min_row=2, max_col=1):
		if row[0].value == dialogue_number:
			dialogue_exists = True
			break
	if not dialogue_exists:
		sheet.append([dialogue_number, ceaf_p, ceaf_r, ceaf_f1, b3_p, b3_r, b3_f1, muc_p, muc_r, muc_f1, total_inference_time, total_input_tokens, total_output_tokens, total_reasoning_tokens, "", "", "", "", "", "", "", "", ""])
		workbook.save(results_excel_path)
		print(f"Results for dialogue {dialogue_number} saved to {results_excel_path}")
	# Save the dictionaries for quality assurance
	pred_filename = f"PRED-DICT_{dialogue_number}_{approach}.json"
	with open(os.path.join(cr_results_folder, pred_filename), 'w') as f:
		json.dump(dict_of_pred_clusters, f, indent=4)
	gt_filename = f"GT-DICT_{dialogue_number}.json"
	with open(os.path.join(cr_results_folder, gt_filename), 'w') as f:
		json.dump(dict_of_GT_clusters, f, indent=4)
	return print(f"Dialogue {dialogue_number} evaluation complete.")

def clean_and_reevaluate(dialogue_number_in_files):
	# Open outputs file
	for file in os.listdir(cr_output_folder):
		if approach in file and f'Outputs_{dialogue_number_in_files}_' in file:
			with open(os.path.join(cr_output_folder, file), 'r') as f:
				dict_of_outputs = json.load(f)
	clean_outputs = {}
	# Load tagged originals from QP file
	for file in os.listdir(qp_folder):
		if approach in file and f'QPs_{dialogue_number_in_files}_' in file:
			with open(os.path.join(qp_folder, file), 'r') as f:
				dict_of_qps = json.load(f)
	# Iterate through outputs and clean them
	for turn_id in dict_of_outputs:
		response_text = dict_of_outputs[turn_id]["response_text"]
		original_tagged = dict_of_qps[turn_id]["User prompt"]["Transcript tagged with mentions"]
		cleaned_text, cleaning_report = clean_cr_output(response_text, original_tagged, dialogue_number_in_files, approach, turn_id, report_folder)
		clean_outputs[turn_id] = cleaned_text
	# Save cleaned outputs to a new file
	cleaned_filename = f'Cleaned_Outputs_{dialogue_number_in_files}_{approach}.json'
	with open(os.path.join(cleaned_output_folder, cleaned_filename), 'w') as f:
		json.dump(clean_outputs, f, indent=4)
	# Recreate chains from cleaned outputs
	dict_of_pred_clusters = {}
	chains_so_far = []
	for turn_id in clean_outputs:
		response_text = clean_outputs[turn_id]
		# Load speaker from QP file
		speaker = dict_of_qps[turn_id]["User prompt"]["Speaker"]
		chains_so_far = chain_updater(chains_so_far, response_text, int(turn_id), speaker)
	for chain in chains_so_far:
		current_key = chain["CHAIN ID"]
		dict_of_pred_clusters[current_key] = []
		for mention in chain["MENTIONS"]:
			dict_of_pred_clusters[current_key].append((mention["TURN ID"], mention["MENTION"], mention["MENTION START"], mention["MENTION END"]))		
	# Get the GT
	annotator_json = locate_annotator_json(dialogue_number_in_files)
	dict_of_GT_clusters = extract_dict_of_GT_clusters(annotator_json)
	# Evaluate
	clean_ceaf_p = ceaf_precision_hungarian(dict_of_GT_clusters, dict_of_pred_clusters)
	clean_ceaf_r = ceaf_recall_hungarian(dict_of_GT_clusters, dict_of_pred_clusters)
	clean_ceaf_f1 = f1(clean_ceaf_p, clean_ceaf_r)
	clean_b3_p = b3_precision_redo(dict_of_GT_clusters, dict_of_pred_clusters)
	clean_b3_r = b3_recall_redo_gt_perspective(dict_of_GT_clusters, dict_of_pred_clusters)
	clean_b3_f1 = f1(clean_b3_p, clean_b3_r)
	clean_muc_p = muc_precision(dict_of_GT_clusters, dict_of_pred_clusters)
	clean_muc_r = muc_recall(dict_of_GT_clusters, dict_of_pred_clusters)
	clean_muc_f1 = f1(clean_muc_p, clean_muc_r)
	# Save results to Excel
	# Open the results Excel file or create a new one if it doesn't exist
	results_excel_path = os.path.join(cr_results_folder, f'CR_Evaluation_Results_{approach}.xlsx')
	if os.path.exists(results_excel_path):
		from openpyxl import load_workbook
		workbook = load_workbook(results_excel_path)
	else:
		from openpyxl import Workbook
		workbook = Workbook()
	# The columns will be:
	# Dialogue Number | CEAF Precision | CEAF Recall | CEAF F1 | B3 Precision | B3 Recall | B3 F1 | MUC Precision | MUC Recall | MUC F1 | Inference time | Input tokens | Output tokens | Reasoning tokens | Clean CEAF Precision | Clean CEAF Recall | Clean CEAF F1 | Clean B3 Precision | Clean B3 Recall | Clean B3 F1 | Clean MUC Precision | Clean MUC Recall | Clean MUC F1
	# Check if the sheet exists
	sheet_name = 'Results'
	if sheet_name in workbook.sheetnames:
		sheet = workbook[sheet_name]
	else:
		sheet = workbook.create_sheet(sheet_name)
	# Check if the dialogue number already exists in the first column
	for row in sheet.iter_rows(min_row=2):
		if row[0].value == dialogue_number_in_files:
			# Update the row with cleaned results
			row[14].value = clean_ceaf_p
			row[15].value = clean_ceaf_r
			row[16].value = clean_ceaf_f1
			row[17].value = clean_b3_p
			row[18].value = clean_b3_r
			row[19].value = clean_b3_f1
			row[20].value = clean_muc_p
			row[21].value = clean_muc_r
			row[22].value = clean_muc_f1
			workbook.save(results_excel_path)
			print(f"Cleaned results for dialogue {dialogue_number_in_files} updated in {results_excel_path}")
			break
		# If the dialogue number doesn't exist, append a new row
	else:
		sheet.append([dialogue_number_in_files, "", "", "", "", "", "", "", "", "", "", "", "", "", clean_ceaf_p, clean_ceaf_r, clean_ceaf_f1, clean_b3_p, clean_b3_r, clean_b3_f1, clean_muc_p, clean_muc_r, clean_muc_f1])
	return print(f"Cleaned results for dialogue {dialogue_number_in_files} saved to {results_excel_path}")


if __name__ == "__main__":
	if whole_or_eval_only == "whole":
		for dialogue_json, annotation_excel in list_of_dialogue_jsons_and_excels:
			dialogue_number_match = re.search(dialogue_number_regex, dialogue_json)
			dialogue_number_in_files = dialogue_number_match.group().replace("X","x").replace("-","x").replace("_","x").replace("&","x")
			total_inference_time, total_input_tokens, total_output_tokens, total_reasoning_tokens = CR_prompter(dialogue_number_in_files)
			CR_evaluator(dialogue_number_in_files, total_inference_time, total_input_tokens, total_output_tokens, total_reasoning_tokens)
			clean_and_reevaluate(dialogue_number_in_files)
	if whole_or_eval_only == "eval":
		for dialogue_json, annotation_excel in list_of_dialogue_jsons_and_excels:
			dialogue_number_match = re.search(dialogue_number_regex, dialogue_json)
			dialogue_number_in_files = dialogue_number_match.group().replace("X","x").replace("-","x").replace("_","x").replace("&","x")
			total_inference_time = 0
			total_input_tokens = 0
			total_output_tokens = 0
			total_reasoning_tokens = 0
			# Obtain the totals from the Outputs_ file
			for file in os.listdir(cr_output_folder):
				if approach in file and f'Outputs_{dialogue_number_in_files}_' in file:
					with open(os.path.join(cr_output_folder, file), 'r') as f:
						dict_of_outputs = json.load(f)
					for turn_id in dict_of_outputs:
						total_inference_time += dict_of_outputs[turn_id]["turn_inference_time"]
						total_input_tokens += dict_of_outputs[turn_id]["input_tokens"]
						total_output_tokens += dict_of_outputs[turn_id]["output_tokens"]
						total_reasoning_tokens += dict_of_outputs[turn_id]["reasoning_tokens"]
			CR_evaluator(dialogue_number_in_files, total_inference_time, total_input_tokens, total_output_tokens, total_reasoning_tokens)
			clean_and_reevaluate(dialogue_number_in_files)