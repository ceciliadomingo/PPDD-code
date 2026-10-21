import json
import spacy
import os

#Import mention extractor and metadata creator
from SPACY_MENTION_EXTRACTOR import spacy_mention_extractor
from TURN_ANNOTATION_METADATA_CREATOR import turn_annotation_metadata_creator

#Load spacy language model
lang_model = spacy.load("en_core_web_lg")
print("model loaded")

# Function to convert a dialogue json into a LabelStudio-compatible json of pre-annotated mentions
# The log of used IDs is a txt file where previously used IDs are stored to avoid duplicates
def convert_dialogue_to_ls_preannotated(json_file, output_directory, log_of_used_IDs):
	json_file_basename = os.path.basename(json_file)
	with open(json_file) as f:
		session_data = json.load(f)
	# List of dictionaries where each dictionary is the annotation metadata for a turn
	whole_annotation_list =[]
	# Define counter of turns with mentions for metadata
	annotation_number = 0
	# Define general project metadata
	task_number = 496
	project_number = 3
	person_ID = 1
	# GENERATE ANNOTATIONS FOR MENTIONS
	for turn_obj in session_data['SESSION']['TURNS']:
		# We use try because some turns may not have transcripts (silent typing)
		try:
			transcript = turn_obj['TURN']['TRANSCRIPT']
			turn_ID = turn_obj['TURN_ID']
			if len(transcript) > 0:
				#Increase counter of turns with mentions
				annotation_number += 1
				#Extract mentions from transcript
				turn_mentions = spacy_mention_extractor(transcript,lang_model,turn_ID, log_of_used_IDs)
				# Create general TURN annotation metadata, which contains results
				turn_annotation_metadata = turn_annotation_metadata_creator(annotation_number, turn_mentions, task_number, project_number, person_ID,json_file_basename, transcript, turn_ID)
				whole_annotation_list.append(turn_annotation_metadata)
		except:
			pass   
	output_filename = os.path.splitext(json_file_basename)[0] + "_preannotated.json"
	print(json.dumps(whole_annotation_list, indent=4), file=open(os.path.join(output_directory, output_filename), "w"))