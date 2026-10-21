import os
import requests
from pydub import AudioSegment
from pydub.utils import mediainfo
from tqdm import tqdm
import json
import re



# -----------------------------------------------------------------
# FUNCTION TO GET THE LIST OF VOICES AVAILABLE
def get_available_voices(API_KEY, output_path):
	url = "https://api.elevenlabs.io/v1/voices"

	headers = {"xi-api-key": API_KEY}

	response = requests.get(url, headers=headers)
	print(response.status_code)
	# Pretty-print JSON
	data = response.json()
	with open(r'ELEVENLABS available voices.txt', "w", encoding="utf-8") as f:
	    json.dump(data, f, indent=4)

# -----------------------------------------------------------------
# FUNCTION TO MERGE CHUNKS AFTER VOICE CONVERSION
def merge_chunks(converted_chunks, OUTPUT_FOLDER, dialogue_number):
	final_audio = AudioSegment.empty()
	for conv in converted_chunks:
		info = mediainfo(conv)
		real_format = info['format_name']
		final_audio += AudioSegment.from_file(conv, format=real_format)
		output_path = os.path.join(OUTPUT_FOLDER, f"{dialogue_number}_anonymised.wav")
	final_audio.export(output_path, format="wav")

	print("Anonymised saved as", output_path)

# -----------------------------------------------------------------
# FUNCTION TO SPLIT AUDIO INTO CHUNKS
def split_audio(INPUT_FILE,TMP_FOLDER, dialogue_number):
	audio = AudioSegment.from_wav(INPUT_FILE)
	chunk_length_ms = 30 * 1000  # 30s
	chunk_paths = []
	for i in range(0, len(audio), chunk_length_ms):
		chunk = audio[i:i + chunk_length_ms]
		path = os.path.join(TMP_FOLDER, f"{dialogue_number}_chunk_{i // chunk_length_ms}.wav")
		chunk.export(path, format="wav")
		chunk_paths.append(path)
	return chunk_paths

# -----------------------------------------------------------------
# FUNCTION TO CONVERT AUDIO CHUNKS USING ELEVENLABS API
def convert_voice_chunks(chunk_paths, VOICE_ID, API_KEY, MODEL_ID, SEED, dialogue_number):
	converted_chunks = []
	for path in tqdm(chunk_paths, desc="Converting chunks"):
		if dialogue_number in path: # The paths should already be filtered by dialogue number, but just in case
			url = f"https://api.elevenlabs.io/v1/speech-to-speech/{VOICE_ID}"
			headers = {
				"xi-api-key": API_KEY,
				"Accept": "audio/mpeg"
			}
			files = {
				"audio": open(path, "rb")
			}
			data = {
				"model_id": MODEL_ID,
				"seed": SEED,
			}

			resp = requests.post(url, headers=headers, files=files, data=data, stream=True)
			print(resp.status_code)
			if not (200 <= resp.status_code < 300): # Codes in the 200s indicate success.
				print(resp.text)
			resp.raise_for_status()

			# Save temp output
			out_path = path.replace(".wav", "_conv.wav")
			with open(out_path, "wb") as f:
				for chunk in resp.iter_content(chunk_size=8192):
					if chunk:
						f.write(chunk)
			converted_chunks.append(out_path)
	return converted_chunks

# -----------------------------------------------------------------
# MAIN FUNCTION
# -----------------------------------------------------------------
def main(INPUT_FOLDER, TMP_FOLDER, VOICE_ID, token_file, MODEL_ID, SEED, OUTPUT_FOLDER):
	with open(token_file, 'r') as file:
		token = file.read().strip()
	API_KEY = token
	os.makedirs(TMP_FOLDER, exist_ok=True)
	list_of_chunked_dialogues = []
	list_of_converted_dialogues = []
	list_of_merged_dialogues = []
	# Check if output folder already contains anonymised dialogues and skip processing if so
	for file in os.listdir(OUTPUT_FOLDER):
		if file.endswith(".wav"):
			dialogue_id = re.search(r"\d+x\d+", file).group(0)
			if dialogue_id not in list_of_merged_dialogues:
				list_of_merged_dialogues.append(dialogue_id)
	# Iterate through audio files in input folder
	for file in os.listdir(INPUT_FOLDER):
		if file.endswith(".wav"):
			dialogue_id = re.search(r"\d+&\d+", file).group(0)
			dialogue_number = dialogue_id.replace("&", "x")
			if dialogue_number in list_of_merged_dialogues:
				print(f"Dialogue {dialogue_number} already processed, skipping.")
				continue
			print("Processing", dialogue_number)
			input_path = os.path.join(INPUT_FOLDER, file)

			# Split audio into chunks
			# Check that chunks for this dialogue haven't already been created (in case of interruption)
			already_chunked = False
			for file in os.listdir(TMP_FOLDER):
				if file.endswith(".wav") and dialogue_number in file:
					print(f"Chunks for dialogue {dialogue_number} already exist, skipping splitting.")
					chunk_paths = [os.path.join(TMP_FOLDER, f) for f in os.listdir(TMP_FOLDER) if f.endswith(".wav") and dialogue_number in f and "conv" not in f] # Get paths of chunks for this dialogue, excluding converted ones
					already_chunked = True
					break
			if already_chunked == False:
				print("Splitting audio into chunks...")
				chunk_paths = split_audio(input_path,TMP_FOLDER, dialogue_number)
			list_of_chunked_dialogues.append(dialogue_number)

			# Convert chunks using ElevenLabs API
			if dialogue_number not in list_of_converted_dialogues:
				print("Converting audio chunks using ElevenLabs API...")
				# Check if any chunk in chunk paths has already been converted (in case of interruption)
				pending_conversion = []
				for chunk_file in chunk_paths:
					conv_file = chunk_file.replace(".wav", "_conv.wav")
					if os.path.exists(conv_file):
						print(f"Chunk {chunk_file} already converted, skipping.")
					else:
						pending_conversion.append(chunk_file)
				converted_chunks = convert_voice_chunks(pending_conversion, VOICE_ID, API_KEY, MODEL_ID, SEED, dialogue_number)
			list_of_converted_dialogues.append(dialogue_number)

			# Merge converted chunks
			print("Merging converted chunks...")
			merge_chunks(converted_chunks, OUTPUT_FOLDER, dialogue_number)
			list_of_merged_dialogues.append(dialogue_number)

if __name__ == "__main__":
	main(INPUT_FOLDER, TMP_FOLDER, VOICE_ID, token_file, MODEL_ID, SEED, OUTPUT_FOLDER)