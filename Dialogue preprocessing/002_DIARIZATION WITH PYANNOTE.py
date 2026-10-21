#From: https://huggingface.co/pyannote/speaker-diarization
from pyannote.audio import Pipeline
import re
def diarise_audio(wav_file, huggingface_token):
	pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization@2.1",
										use_auth_token=huggingface_token)

	diarization = pipeline(wav_file)

	dialogue_number_regex = re.compile(r'(\d{3})[xX&](\d{3}).+')
	speaker_a = dialogue_number_regex.match(wav_file).group(1)
	speaker_b = dialogue_number_regex.match(wav_file).group(2)

	# Save the output using RTTM format
	dialogue_code = f"{speaker_a}x{speaker_b}"
	with open(f"{dialogue_code}.rttm", "w") as rttm:
		diarization.write_rttm(rttm)

if __name__ == "__main__":
	wav_file = 'path/to/your/audio/file.wav' #Replace with your audio file path
	huggingface_token = 'your_huggingface_token' #Replace with your Hugging Face token
	diarise_audio(wav_file, huggingface_token)