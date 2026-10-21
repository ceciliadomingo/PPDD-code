# Function to add rowID to the Excel file to distinguish each annotation
def add_row_id(excel, excel_folder, dialogue_number):
    # Read the Excel file into a DataFrame
    df = pd.read_excel(excel)
    # Add a new column 'Row ID' with the index values
    df['Row ID'] = df.index + 1
    # Save the modified DataFrame to a new Excel file
    output_file = excel_folder + '\\' + dialogue_number + '_01_withrowID.xlsx'
    df.to_excel(output_file, index=False)
    return output_file

# Function to remove trailing punctuation and reflect that in indexes
# (e.g., if mention is "hello.", it becomes "hello" and the end index is reduced by 1)
def remove_trailing_punctuation(excel, excel_folder, dialogue_number):
    # Read the Excel file into a DataFrame
    df = pd.read_excel(excel)
    # Create a dictionary to store the values for later use
    stored_values = {}
    # Dictionary of punctuation marks to check for, their length, and whether beginning or end
    greedy_punctuation_marks_start ={
        '...': (3, 'beginning')
    }
    greedy_punctuation_marks_end = {
        '...': (3, 'end')
    }
    punctuation_marks = {  
        '.': (1, 'end'),
        ',': (1, 'end'),
        '?': (1, 'end'),
        '!': (1, 'end'),
        ', ': (2, 'beginning')  
    }
    punctuation_dicts_greedy_first_list = [greedy_punctuation_marks_start, greedy_punctuation_marks_end, punctuation_marks]
    # Iterate through each row in the DataFrame
    for index, row in df.iterrows():
        mention = str(row['Mention']) # In case it's a number parsed as int
        turn_id = row['Turn ID']
        mention_start = row['Mention start']
        mention_end = row['Mention end']

        if pd.isna(mention):
            print(f"Skipping row {index} because 'Mention' is NaN.")
            continue  # Skip rows where Mention is NaN

        # Go through punctuation dictionary
        # Start with greedy punctuation
        for dictionary in punctuation_dicts_greedy_first_list:
            for punctuation, (length, position) in dictionary.items():
                # Check if the mention starts or ends with the punctuation
                if position == 'beginning' and mention.startswith(punctuation):
                    # Trimming the mention. I do not change the variable name, because otherwise other less greedy punctuation would be checked
                    # So mention changes value; in stored values, I store the trimmed mention
                    mention = mention[length:]
                    # Store the values in the dictionary
                    stored_values[(turn_id, mention_start, mention_end)] = (mention, turn_id, mention_start + length, mention_end)
                    # Remove the leading punctuation from the Mention column
                    df.at[index, 'Mention'] = mention
                    # Update the Mention start value
                    df.at[index, 'Mention start'] += length
                elif position == 'end' and mention.endswith(punctuation):
                    # Trimming the mention. I do not change the variable name, because otherwise other less greedy punctuation would be checked
                    # So mention changes value; in stored values, I store the trimmed mention
                    mention = mention[:-length]
                    # Store the values in the dictionary
                    stored_values[(turn_id, mention_start, mention_end)] = (mention, turn_id, mention_start, mention_end - length)
                    # Remove the trailing punctuation from the Mention column
                    df.at[index, 'Mention'] = mention
                    # Update the Mention end value
                    df.at[index, 'Mention end'] -= length

    # Iterate through the stored values to update the Referent Turn Span End and Start columns
    for (turn_id, mention_start, mention_end), (trimmed_mention, turnID, trimmed_mention_start, trimmed_mention_end) in stored_values.items():
        referent_mask = (df['Referent Turn ID'] == turn_id) & \
                        (df['Referent Turn Span Start'] == mention_start) & \
                        (df['Referent Turn Span End'] == mention_end)
        df.loc[referent_mask, 'Referent Turn Span End'] = trimmed_mention_end
        df.loc[referent_mask, 'Referent Turn Span Start'] = trimmed_mention_start


    # Save the stored values dictionary to a txt log file
    with open(excel.replace('.xlsx', '_punctuationfixlog.txt'), 'a') as log_file:
        log_file.write("Stored Values for punctuation fix:\n")
        for (turn_id, mention_start, mention_end), (trimmed_mention, turnID, trimmed_mention_start, trimmed_mention_end) in stored_values.items():
            log_file.write(f"Turn ID: {turn_id}, Mention Start: {mention_start}, Mention End: {mention_end}, "
                           f"Trimmed Mention: {trimmed_mention}, Trimmed Mention Start: {trimmed_mention_start}, "
                           f"Trimmed Mention End: {trimmed_mention_end}\n")
            
    # Save the modified DataFrame to a new Excel file
    output_file = excel_folder + '\\' + dialogue_number + '_02_punctuationfixed.xlsx'
    df.to_excel(output_file, index=False)
    return output_file


# Function to fix incomplete BLEEPs
# E.g., if mention is "BLEEP)", it becomes "(BLEEP)" and the start index is reduced by 1. Anonymised names should all be in the format (BLEEP)
def complete_bleeps(excel, excel_folder, dialogue_number):
    # Read the Excel file into a DataFrame
    df = pd.read_excel(excel)
    # Create a dictionary to store the values for later use
    stored_values = {}
    # Iterate through each row in the DataFrame
    for index, row in df.iterrows():
        mention = row['Mention']
        turn_id = row['Turn ID']
        mention_start = row['Mention start']
        mention_end = row['Mention end']

        # Check if the mention is missing a (
        if mention == 'BLEEP)':
            # Store the values in the dictionary
            completed_mention = '(BLEEP)'
            trimmed_mention_start = mention_start - 1
            stored_values[(turn_id, mention_start, mention_end)] = (completed_mention, turn_id, trimmed_mention_start, mention_end)
            # Update the Mention column
            df.at[index, 'Mention'] = completed_mention
            # Update the Mention start value
            df.at[index, 'Mention start'] -= 1

        # Check if the mention is missing a )
        elif mention == '(BLEEP':
            # Store the values in the dictionary
            completed_mention = '(BLEEP)'
            trimmed_mention_end = mention_end + 1
            stored_values[(turn_id, mention_start, mention_end)] = (completed_mention, turn_id, mention_start, trimmed_mention_end)
            # Update the Mention column
            df.at[index, 'Mention'] = completed_mention
            # Update the Mention end value
            df.at[index, 'Mention end'] += 1
        

        # Check if the mention is missing both ( and )
        elif mention == 'BLEEP':
            # Store the values in the dictionary
            completed_mention = '(BLEEP)'
            trimmed_mention_start = mention_start - 1
            trimmed_mention_end = mention_end + 1
            stored_values[(turn_id, mention_start, mention_end)] = (completed_mention, turn_id, trimmed_mention_start, trimmed_mention_end)
            # Update the Mention column
            df.at[index, 'Mention'] = completed_mention
            # Update the Mention start and end values
            df.at[index, 'Mention start'] -= 1
            df.at[index, 'Mention end'] += 1

    # Iterate through the stored values to update the Referent Turn Span End and Start columns
    for (turn_id, mention_start, mention_end), (trimmed_mention, turnID, trimmed_mention_start, trimmed_mention_end) in stored_values.items():
        referent_mask = (df['Referent Turn ID'] == turn_id) & \
                        (df['Referent Turn Span Start'] == mention_start) & \
                        (df['Referent Turn Span End'] == mention_end)
        df.loc[referent_mask, 'Referent Turn Span End'] = trimmed_mention_end
        df.loc[referent_mask, 'Referent Turn Span Start'] = trimmed_mention_start

    # Save the stored values dictionary to a txt log file
    with open(excel.replace('.xlsx', '_bleepfixlog.txt'), 'w') as log_file:
        for (turn_id, mention_start, mention_end), (completed_mention, turnID, trimmed_mention_start, trimmed_mention_end) in stored_values.items():
            log_file.write(f"Turn ID: {turn_id}, Mention Start: {mention_start}, Mention End: {mention_end}, "
                           f"Completed Mention: {completed_mention}, Trimmed Mention Start: {trimmed_mention_start}, "
                           f"Trimmed Mention End: {trimmed_mention_end}\n")
            
    # Save the modified DataFrame to a new Excel file
    output_file = excel_folder + '\\' + dialogue_number + '_03_bleepfixed.xlsx'
    df.to_excel(output_file, index=False)
    return output_file

