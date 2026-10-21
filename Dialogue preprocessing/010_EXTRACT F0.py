import librosa
import numpy as np
import matplotlib.pyplot as plt

# Function to convert seconds to minutes and seconds
def convert_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

def extract_f0_with_timestamps(audio_path, output_csv):
	# Read the wav file
	y, sr = librosa.load(audio_path)

	# Extract the harmonic component of the audio
	harmonic, percussive = librosa.effects.hpss(y)

	# Compute the F0 contour from the harmonic component
	f0, voiced_flag, voiced_probs = librosa.pyin(harmonic, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'))

	# Compute the frame duration
	hop_length = 512  # You can adjust this value as needed
	frame_duration = hop_length / sr

	# Create timestamps
	timestamps = np.arange(0, len(f0)) * frame_duration

	# Combine timestamps and F0 values
	f0_with_timestamps = list(zip(timestamps, f0))

	# Print the timestamped F0 values
	for timestamp, f0_value in f0_with_timestamps:
		#Convert timestampts to minutes and seconds
		formatted_time = convert_time(timestamp)
		print(f'Timestamp: {timestamp:.2f}, Formatted time: {formatted_time}, F0: {f0_value:.2f} Hz', file=open(output_csv, "a"))

if __name__ == "__main__":
	audio_path = 'path/to/your/audio/file.wav'  # Replace with your audio file path
	output_csv = 'path/to/output/f0_with_timestamps.csv'  # Replace with your desired output CSV file path
	extract_f0_with_timestamps(audio_path, output_csv)
