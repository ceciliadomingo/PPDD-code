# Functions to process "Read-dictate" label
# We have to check if a mention was labelled as "Read-dictate" in the Excel file and as something else as well (e.g., "Read-dictate" and "Name")
# We want to prioritise the more informative label (e.g., "Name") but still keep track that the mention was also labelled as "Read-dictate"
# (e.g., the mention was a variable name, but it was read-out from the code)

# Function to copy referent information from read-dictate row to the row with the other label
def copy_referent_info_from_read_dictate_to_duplicate(df, index, row, output_log):
    list_of_columns_to_check_for_copying = ['Referent Turn ID', 'Referent Turn Span Start', 'Referent Turn Span End', 'Code File', 'Code Span Start', 'Code Span End']
    for column in list_of_columns_to_check_for_copying:
        if pd.isna(df.at[index - 1, column]) and not pd.isna(row[column]):
            # Copy the referent information from the read-dictate row to the duplicate row
            df.at[index - 1, column] = row[column]
        if pd.isna(df.at[index + 1, column]) and not pd.isna(row[column]):
            # Copy the referent information from the read-dictate row to the duplicate row
            df.at[index + 1, column] = row[column]
    print(f"Copying referent information from index {index}", file=(open(output_log, 'a+')))
    return df

# Main function to process read-dictate labels
def read_dictate(excel_file, excel_folder, dialogue_number,output_log):
    print(f"Processing read-dictate for {dialogue_number}.", file=(open(output_log, 'a+')))

    # Read the Excel file
    df = pd.read_excel(excel_file)

    # Initialize the read-dictate dictionary as a defaultdict
    read_dictate_dict = defaultdict()

    # Create list of indexes already confirmed as "Read-dictate"
    indexes_already_added_to_read_dictate = []
    rowids_for_read_dictate = []

    # Create a new column in the DataFrame for "Read-dictate"
    df['Read-dictate'] = False

    # Iterate through the DataFrame to find "Read-dictate"
    for index, row in df.iterrows():
        if index in indexes_already_added_to_read_dictate:
            # Skip this index as it has already been added to the incomplete JSON through the look-forward function
            print(f"Skipping index {index} as it has already been added", file=(open(output_log, 'a+')))
            continue
        if "Read-dictate" in row['Mention form']:
            indexes_already_added_to_read_dictate.append(index)
            rowids_for_read_dictate.append((row['Row ID'],"no duplicate")) # Setting to "no duplicate" initially, we'll look for duplicates later
            print(f"Adding index {index} to the list of read-dictate mentions", file=(open(output_log, 'a+')))
            # Change the "Read-dictate" column to True
            df.at[index, 'Read-dictate'] = True
    
    # Finding duplicate information 
    # (i.e., mentions that are the same as teh Read-dictate mention in the previous or next row, but were annotated twice to add another grammatical label)
    # Iterate through the DataFrame to update the second item of the tuples in rowids_for_read_dictate list
    for index, row in df.iterrows():
        for tuple in rowids_for_read_dictate:
            if int(row['Row ID']) == int(tuple[0]):
                # Look for duplicates
                if  index > 0 and row['Turn ID'] == df.at[index - 1, 'Turn ID'] and row['Mention start'] == df.at[index - 1, 'Mention start'] and row['Mention end'] == df.at[index - 1, 'Mention end']:
                    # Update the tuple to indicate a duplicate
                    rowids_for_read_dictate[rowids_for_read_dictate.index(tuple)] = (tuple[0], "Has duplicate")
                    # Update the DataFrame to set 'Read-dictate' to True for the duplicate
                    df.at[index - 1, 'Read-dictate'] = True
                    # Check if the read-dictate row has referent information that the duplicate row does not have
                    df = copy_referent_info_from_read_dictate_to_duplicate(df, index, row, output_log)
                elif index < len(df) - 1 and row['Turn ID'] == df.at[index + 1, 'Turn ID'] and row['Mention start'] == df.at[index + 1, 'Mention start'] and row['Mention end'] == df.at[index + 1, 'Mention end']:
                    # Update the tuple to indicate a duplicate
                    rowids_for_read_dictate[rowids_for_read_dictate.index(tuple)] = (tuple[0], "Has duplicate")
                    # Update the DataFrame to set 'Read-dictate' to True for the duplicate
                    df.at[index + 1, 'Read-dictate'] = True
                    # Check if the read-dictate row has referent information that the duplicate row does not have
                    df = copy_referent_info_from_read_dictate_to_duplicate(df, index, row, output_log)
    
    # Iterate through the list to remove the read-dictate dataframe rows that have duplicates
    for tuple in rowids_for_read_dictate:     
            if tuple[1] == "Has duplicate":
                # Use the rowID (tuple[0]) to find the index in the DataFrame and delete the row
                index_to_delete = df[df['Row ID'] == tuple[0]].index
                df.drop(index_to_delete, inplace=True)
                print(f"Removing duplicate row with Row ID {tuple[0]} from the DataFrame", file=(open(output_log, 'a+')))

    # Add data to the read-dictate dictionary to save to json
    for index, row in df.iterrows():
        if row['Read-dictate'] == True:
            # Create a dictionary for the read-dictate entry
            read_dictate_entry = {
                'Row ID': row['Row ID'],
                'Turn ID': row['Turn ID'],
                'Mention start': row['Mention start'],
                'Mention end': row['Mention end'],
                'Mention': row['Mention'],
                'Mention form': row['Mention form']
            }
            # Add the entry to the read-dictate dictionary
            read_dictate_dict[row['Row ID']] = read_dictate_entry
    
    # Save the read-dictate dictionary to a JSON file
    excel_folder = os.path.dirname(excel_file)
    read_dictate_json_filename = excel_folder + '\\' + dialogue_number  + '_read_dictate.json'
    with open(read_dictate_json_filename, 'w') as f:
        json.dump(read_dictate_dict, f, indent=4)
    # Save the updated DataFrame back to the Excel file
    excel_file = excel_folder + '\\' + dialogue_number + '_05_read_dictate_removed.xlsx'
    df.to_excel(excel_file, index=False)
    return excel_file
              