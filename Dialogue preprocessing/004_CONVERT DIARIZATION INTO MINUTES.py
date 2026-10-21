import os

# Function to convert seconds to MM:SS format
def convert_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"


# Function to read RTTM file and convert the timestamps into minutes and seconds
def convert_rttm_to_mins(rttm_file):
	with open(rttm_file, "r") as file:
		for line in file:
			parts = line.strip().split()
			start_time = float(parts[3])
			end_time = start_time + float(parts[4])
			speaker_code = parts[7]

			formatted_start = convert_time(start_time)
			formatted_end = convert_time(end_time)

			output_filepath = os.path.join(os.path.dirname(rttm_file), "converted_" + os.path.basename(rttm_file))

			print(f"Start: {formatted_start}, End: {formatted_end}, Speaker: {speaker_code}", file=open(output_filepath, "a"))

if __name__ == "__main__":
	rttm_file = "path/to/your/file.rttm"  # Replace with your RTTM file path
	convert_rttm_to_mins(rttm_file)