import json
import re
import os

#Function to take srt file and create json with:
#session id
    #turn objects with turn ID
        #transcript objects within the turns
        #time objects within the turns
            #start and end times within the time objects
def create_annotation_json(srt_filepath):

    #Extract session id using regex
    srtfilename = os.path.basename(srt_filepath)
    session_id = re.search('(0\d\d[_&xX]0\d\d)', srtfilename).group(1)

    #Create json object
    annotation_json = {
        "SESSION": {
            "sessionID": session_id,
            "TURNS": []
            }
    }

    #Iteate through srt file to add each turn to json object
    with open(srt_filepath, "r") as file:
        #Create turns object
        turns = annotation_json['SESSION']['TURNS']

        #Read srt lines
        lines = file.readlines()
        for line1, line2 in zip(lines[::2], lines[1::2]):
            #Extract transcript
            transcript = line2
            # Example format: 00:01:02,000 --> 00:01:05,000
            start_time = re.search('((\d\d:\d\d:\d\d,\d\d\d) --> (\d\d:\d\d:\d\d,\d\d\d))', line1).group(2)
            end_time = re.search('((\d\d:\d\d:\d\d,\d\d\d) --> (\d\d:\d\d:\d\d,\d\d\d))', line1).group(3)

            #Add TURN object content        
            turns.append({
            "TURN": {
                "TRANSCRIPT": transcript,
                "TIME": {"START": start_time, "END": end_time}
                }
            })

        json_filename = srt_filepath.strip("srt") + "json"
        print(json.dumps(annotation_json, indent=4), file=open(json_filename, "+a"))
        print('Generated json file: ' + json_filename)

if __name__ == "__main__":
	srt_filepath = 'path/to/your/srt/file.srt' #Replace with your subtitle file name
	create_annotation_json(srt_filepath)