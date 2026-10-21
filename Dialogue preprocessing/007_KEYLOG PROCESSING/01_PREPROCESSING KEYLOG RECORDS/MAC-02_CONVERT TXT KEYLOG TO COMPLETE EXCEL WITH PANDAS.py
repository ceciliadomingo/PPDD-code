import pandas as pd
from datetime import datetime
import os

def convert_mac_txt_keylog_to_excel(mac_keylog_txt):
	#Open file
	df = pd.read_csv(mac_keylog_txt, sep="\t")

	#Changing the format of the Actions
	def transform_actions_to_excel_format(action):
		if action == 'Moved':
			return 'Move'
		elif action == 'Pressed':
			return 'Pressed'
		elif action == 'Key':
			return 'Key'
	df['Action'] = df['Action'].apply(transform_actions_to_excel_format)

	#Creating list of columns for new df
	#Time Action Key Modifier MouseClick X Y Task
	new_df_time_list = []
	new_df_action_list = []
	new_df_key_list = []
	new_df_modifier_list = []
	new_df_mouseclick_list = []
	new_df_x_list =[]
	new_df_y_list = []
	new_df_task_list = []

	#Iterate through old df and add info to lists for new df
	#Action --> Key: move x value to Key column, y to modifier, others blank
	#Action --> Pressed: move x value to MouseClick column, others blank
	#Action --> Move: move x value to X column, y to Y, others blank
	for index, row in df.iterrows():
		if row['Action'] == 'Key':
			new_df_time_list.append(row['Time'])
			new_df_action_list.append(row['Action'])
			new_df_key_list.append(row['X'])
			new_df_modifier_list.append(row['Y'])
			new_df_mouseclick_list.append('')
			new_df_x_list.append('')
			new_df_y_list.append('')
			new_df_task_list.append('')
		elif row['Action'] == 'Pressed':
			new_df_time_list.append(row['Time'])
			new_df_action_list.append(row['Action'])
			new_df_key_list.append('')
			new_df_modifier_list.append('')
			new_df_mouseclick_list.append(row['X'])
			new_df_x_list.append('')
			new_df_y_list.append('')
			new_df_task_list.append('')
		elif row['Action'] == 'Move':
			new_df_time_list.append(row['Time'])
			new_df_action_list.append(row['Action'])
			new_df_key_list.append('')
			new_df_modifier_list.append('')
			new_df_mouseclick_list.append('')
			new_df_x_list.append(row['X'])
			new_df_y_list.append(row['Y'])
			new_df_task_list.append('')

	#Create new df
	new_df = pd.DataFrame(list(zip(new_df_time_list, new_df_action_list, new_df_key_list, new_df_modifier_list, new_df_mouseclick_list, new_df_x_list, new_df_y_list, new_df_task_list)), columns = ['Time', 'Action', 'Key', 'Modifier', 'MouseClick', 'X', 'Y', 'Task'])


	#Change timestampt format from dot to colon
	def transform_time_to_colon_format(timestamp):
		input_format = '%Y-%m-%dT%H:%M:%S.%f'
		desired_format = '%Y-%m-%dT%H:%M:%S:%f'
		datetime_obj = datetime.strptime(timestamp, input_format)
		formatted_timestamp = datetime_obj.strftime(desired_format)[:-3]
		return formatted_timestamp
	new_df['Time'] = new_df['Time'].apply(transform_time_to_colon_format)


	#Export the dataframe to a csv file
	output_filepath = os.path.join(os.path.dirname(mac_keylog_txt), os.path.splitext(os.path.basename(mac_keylog_txt))[0] + '_converted.csv')
	new_df.to_csv(output_filepath, index=False)
