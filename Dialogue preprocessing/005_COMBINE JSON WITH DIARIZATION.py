# This script combines the JSON file with the diarization file, by adding the timestamps from the diarization file to the JSON file.
# The diarization file is in RTTM format, which is different from the transcription's SRT format, which is what the JSON contains.

# TIMESTAMP FORMATS
    #RTTM
    #Start: 00:04, End: 00:10, Speaker: 004
    #Start: 00:11, End: 00:11, Speaker: OTHER (noise or researcher)
    #SRT
    #00:00:02,156 --> 00:00:03,929


import json
import re 
from datetime import datetime, timedelta 


# FUNCTION TO CONVERT RTTM TIMESTAMPS INTO SRT TIMESTAMP FORMAT STRINGS
def convert_rttm_timestamps_to_srt_timestamps(rttm_timestamp):
    # Parse the input timestamp to get minutes and seconds
    minutes, seconds = map(int, rttm_timestamp.split(":"))

    # Create a timedelta representing the given minutes and seconds
    time_delta = timedelta(minutes=minutes, seconds=seconds)

    # Create a reference datetime with zero hours
    reference_time = datetime.strptime("00:00:00", "%H:%M:%S")

    # Add the timedelta to the reference time to get the new time
    new_time = reference_time + time_delta

    # Format the new time as "hours:minutes:seconds,milliseconds"
    formatted_new_time = new_time.strftime("%H:%M:%S,%f")[:-3]  # Truncate to milliseconds
    return formatted_new_time


# FUNCTION TO CONVERT TIMESTAMP STRINGS INTO DATETIME OBJECTS
def convert_timestamp_string_to_datetime(timestamp_string):
    #Convert timestamp string into datetime object
    timestamp_datetime = datetime.strptime(timestamp_string, '%H:%M:%S,%f')
    return timestamp_datetime



# FUNCTION TO EXTRACT TIMESTAMPS FROM RTTM FILE
# It excludes the records with speaker OTHER (just noise)
def extract_rttm_timestamps(rttmfilename):
    rttm_timestamps_list = [] #List of lists with start and end timestamps and speaker
    with open(rttmfilename, 'r') as rttm_file:
        for line in rttm_file:
            #Regexes to find start and end timestamps and speaker in each line
            start_match = re.search('Start: (\d\d:\d\d)', line)
            end_match = re.search('End: (\d\d:\d\d)', line)
            speaker_match = re.search('Speaker: (.*)', line)

            #If the regex works, extract results
            if start_match and end_match and speaker_match:
                start = start_match.group(1)
                end = end_match.group(1)
                speaker = speaker_match.group(1)

                #Select the lines with a recognized speaker (not OTHER) to add them to the list
                if speaker != 'OTHER':
                    #Convert timestamps into srt format (as string)
                    start_formatted_string = convert_rttm_timestamps_to_srt_timestamps(start)
                    end_formatted_string = convert_rttm_timestamps_to_srt_timestamps(end)
                    rttm_timestamps_list.append([start_formatted_string,end_formatted_string,speaker])
    return rttm_timestamps_list


# FUNCTION TO FIND CLOSEST RTTM TIMESTAMP TO SRT TIMESTAMP
def find_closest_rttm_timestamp(srt_startORend_time_datetime, rttm_timestamps_list,startORendLABEL):
    # If startORendLABEL is 'start', then index is 0, if it's 'end', then index is 1
    # Because rttm_timestamps_list is a list of lists, and each list contains start and end timestamps
    # (start_formatted_string,end_formatted_string,speaker)
    if startORendLABEL == 'start':
        index = 0
    elif startORendLABEL == 'end':
        index = 1

    # Initialize variables to keep track of the two closest datetimes and their time differences
    closest_datetimes = [None, None]
    min_time_differences = [timedelta.max, timedelta.max]
    for rttm_timestamp in rttm_timestamps_list:
        # Compare rttm timestamp with srt timestamp
        rttm_datetime = datetime.strptime(rttm_timestamp[index], '%H:%M:%S,%f')
        time_difference = abs(srt_startORend_time_datetime - rttm_datetime)

        # If the difference is smaller than the smallest difference so far, update the closest datetimes
        # If it's smaller than the smallest difference so far
        if time_difference < min_time_differences[0]:
            # Now second smallest difference has values of previous smallest difference
            min_time_differences[1] = min_time_differences[0]
            # And second best rttm timestamp has value of previous best rttm timestamp
            closest_datetimes[1] = closest_datetimes[0]
                
            # And now the smallest difference has the value of the new smallest difference
            min_time_differences[0] = time_difference
            # And the best rttm timestamp has the value of the new best rttm timestamp
            closest_datetimes[0] = rttm_timestamp

        # If it's not smallest, but second smallest
        elif time_difference < min_time_differences[1]:
            # Now second smallest difference has value of new second smallest difference
            min_time_differences[1] = time_difference
            # And second best rttm timestamp has value of new second best rttm timestamp
            closest_datetimes[1] = rttm_timestamp

    # Return the two closest datetimes
    return closest_datetimes


#----------------------------------------------
# MAIN FUNCTION TO COMBINE JSON AND DIARIZATION
#----------------------------------------------
def json_and_diarization_combiner(jsonfilename, rttmfilename):
    # Read and load the JSON file
    with open(jsonfilename, 'r') as json_file:
        data = json.load(json_file)
    
    # Iterate through json file
    for turn in data['SESSION']['TURNS']:
        # Extract timestamps from JSON file (srt format)
        srt_start_time = turn['TURN']['TIME']['START']
        srt_end_time = turn['TURN']['TIME']['END']
        # Convert srt timestamp to datetime object
        srt_start_time_datetime = datetime.strptime(srt_start_time, '%H:%M:%S,%f')
        srt_end_time_datetime = datetime.strptime(srt_end_time, '%H:%M:%S,%f')

        # Iterate through rttm timestamps
        rttm_timestamps_list = extract_rttm_timestamps(rttmfilename) #Function that returns list of timestamps


        # These functions each return a list with two rttm timestamps (rttm is list containing start, end and speaker)
        closest_start_datetimes = find_closest_rttm_timestamp(srt_start_time_datetime, rttm_timestamps_list,startORendLABEL='start')
        closest_end_datetimes = find_closest_rttm_timestamp(srt_end_time_datetime, rttm_timestamps_list,startORendLABEL='end')
        
        # Find best rttm timestamp from up to four candidates
        # If the start and end timestamps are the same, then there's only one candidate
        if closest_start_datetimes[0] == closest_end_datetimes[0]:
            best_rttm_timestamp = closest_start_datetimes[0]
        # Otherwise, we need to calculate combined time difference for each candidate
        else:
            # Calculate time difference for each candidate
            # That is, the time difference between the srt start and end timestamps and the rttm start and end timestamps
            time_difference_candidate1 = abs(srt_start_time_datetime - convert_timestamp_string_to_datetime(closest_start_datetimes[0][0])) + abs(srt_end_time_datetime - convert_timestamp_string_to_datetime(closest_start_datetimes[0][1]))
            time_difference_candidate2 = abs(srt_start_time_datetime - convert_timestamp_string_to_datetime(closest_start_datetimes[1][0])) + abs(srt_end_time_datetime - convert_timestamp_string_to_datetime(closest_start_datetimes[1][1]))
            time_difference_candidate3 = abs(srt_start_time_datetime - convert_timestamp_string_to_datetime(closest_end_datetimes[0][0])) + abs(srt_end_time_datetime - convert_timestamp_string_to_datetime(closest_end_datetimes[0][1]))
            time_difference_candidate4 = abs(srt_start_time_datetime - convert_timestamp_string_to_datetime(closest_end_datetimes[1][0])) + abs(srt_end_time_datetime - convert_timestamp_string_to_datetime(closest_end_datetimes[1][1]))

            # Find the smallest time difference
            smallest_time_difference = min(time_difference_candidate1, time_difference_candidate2, time_difference_candidate3, time_difference_candidate4)

            # Find the best rttm timestamp
            if smallest_time_difference == time_difference_candidate1:
                best_rttm_timestamp = closest_start_datetimes[0]
            elif smallest_time_difference == time_difference_candidate2:
                best_rttm_timestamp = closest_start_datetimes[1]
            elif smallest_time_difference == time_difference_candidate3:
                best_rttm_timestamp = closest_end_datetimes[0]
            elif smallest_time_difference == time_difference_candidate4:
                best_rttm_timestamp = closest_end_datetimes[1]

        # Add diarization to json file
        diarization_dict = {
            'RTTM_START': best_rttm_timestamp[0],
            'RTTM_END': best_rttm_timestamp[1],
            'SPEAKER': best_rttm_timestamp[2]
        }
        turn['TURN']['DIARIZATION'] = diarization_dict
        """turn['RTTM_START'] = best_rttm_timestamp[0]
        turn['RTTM_END'] = best_rttm_timestamp[1]
        #Add the speaker
        turn['SPEAKER'] = best_rttm_timestamp[2]"""

    # After going through all turns, save the json file
    with open(jsonfilename, 'w') as json_file:
        json.dump(data, json_file, indent=4)
    print('JSON file with diarization saved as: ' + jsonfilename)

if __name__ == "__main__":
	jsonfilename = 'path/to/json_file.json' #Replace with your JSON file name
	rttmfilename = 'path/to/diarisation_file.rttm' #Replace with your RTTM file name
	json_and_diarization_combiner(jsonfilename, rttmfilename)










