#Reduce keylog granularity
#Keep all key and pressed data points
#But reduce the number of move actions

#Import libraries
import pandas as pd
import re
from datetime import datetime, timedelta
import numpy as np
import os

def reduce_keylog_granularity(merged_keylog_excel):
	#Import data
	df = pd.read_excel(merged_keylog_excel)
	#For csv files
	#df = pd.read_csv('012_Keylog_Trimmed_synchronized.csv')
	#print(df)
	#Create lists of data
	time_list = df['Time'].tolist()
	key_list = df['Key'].tolist()
	modifier_list = df['Modifier'].tolist()
	mouseclick_list = df['MouseClick'].tolist()
	x_list = df['X'].tolist()
	y_list = df['Y'].tolist()
	task_list = df['Task'].tolist()
	relative_timestamp_list = df['Relative Timestamp'].tolist()

	#Create list of indexes that we'll keep
	keep_index_list = []
	#Create dicitonary of Move actions and their indexes
	move_dict = {}

	#Iterate through Action column
	#If the action is Move, add the index as key to dictionary, the Time as value
	#If the action is not Move, add the index to keep_index_list
	for index, value in df['Action'].items():
		if value != 'Move':
			keep_index_list.append(index)
		else:
			move_dict[index] = df['Time'][index]

	print("move dict", len(move_dict)) #--> Should be almost as long as the whole df, most actions are Move

	#Create smaller dictionary of Move actions and their indexes which we'll keep
	keep_move_dict = {}

	#Iterate through move_dict
	# Convert timestamp strings to datetime objects
	timestamp_objects = {}
	for key, value in move_dict.items():
		timestamp_objects[key] = datetime.strptime(re.sub(r":(\d{3})", r".\1", value), "%Y-%m-%dT%H:%M:%S.%f")

	# Adjust granularity
	adjusted_timestamps = {}
	previous_timestamp = None
	quarter_second = timedelta(milliseconds=250)
	for key, timestamp in timestamp_objects.items():
		if previous_timestamp is None or (timestamp - previous_timestamp) >= quarter_second:
			adjusted_timestamps[key] = timestamp
			previous_timestamp = timestamp

	# Convert datetime objects back to timestamp strings
	for key, timestamp in adjusted_timestamps.items():
		keep_move_dict[key] = timestamp.strftime("%Y-%m-%dT%H:%M:%S:%f")[:-3]  # Remove last three digits

	#print(keep_move_dict)
	print("keep move dict", len(keep_move_dict)) #--> Should be much smaller than move_dict

	#Add the indexes of the keep_move_dict to the keep_index_list
	for key, value in keep_move_dict.items():
		keep_index_list.append(key)


	#Create new dataframe with only the rows we want to keep from the old df
	df_new = df.iloc[keep_index_list]

	#Sort the new dataframe by Time
	sort_indices = np.argsort(df_new['Time'])
	# Use the indices to rearrange the rows of the entire new df and create sorted df
	df_sorted = df_new.iloc[sort_indices]

	#Export to csv
	output_filepath = os.path.join(os.path.dirname(merged_keylog_excel), os.path.basename(merged_keylog_excel).replace('.xlsx', '_reduced_granularity.csv'))
	df_sorted.to_csv(output_filepath, index=False)

if __name__ == "__main__":
	merged_keylog_excel = 'path/to/merged_keylog_excel.xlsx' #Replace with actual path to merged keylog excel file
	reduce_keylog_granularity(merged_keylog_excel)