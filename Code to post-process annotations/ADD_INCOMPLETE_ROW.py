
# Function to add the information from the rows where the mentions were labelled as INCOMPLETE,
# so that we may remove those rows, as the rest of the information is already in the other rows
# (when a mention is labelled as INCOMPLETE, two rows were geenrated, one for the INCOMPLETE label, and another for the mention form label)
def remove_incomplete_duplicates(incomplete_json, excel_file, excel_folder, dialogue_number):

    # Load the incomplete JSON data
    with open(incomplete_json, 'r') as f:
        incomplete_data = json.load(f)

    # Load the Excel file
    df = pd.read_excel(excel_file)
    
    # Create new "Incomplete" column
    df['Incomplete'] = False

    # Iterate through the incomplete json and update the incomplete column in the DataFrame
    list_of_rows_with_incomplete_true = []
    for completeobj in incomplete_data:
        for item in completeobj['Items']:
            list_of_rows_with_incomplete_true.append(item)
    for index, row in df.iterrows():
        for item in list_of_rows_with_incomplete_true:
            if int(row['Row ID']) == int(item):
                # Update the DataFrame to set 'Incomplete' to True
                df.at[index, 'Incomplete'] = True

    # Now find the rows that are duplicates of the incomplete rows and change the incomplete column to True
    for index, row in df.iterrows():
        if 'INCOMPLETE' in str(row['Mention form']):
            # Check the row before to see if it's the same mention
            if index > 0 and row['Turn ID'] == df.at[index - 1, 'Turn ID'] and row['Mention start'] == df.at[index - 1, 'Mention start'] and row['Mention end'] == df.at[index - 1, 'Mention end']:
                # Update the DataFrame to set 'Incomplete' to True
                df.at[index - 1, 'Incomplete'] = True
            # Check the row after to see if it's the same mention
            if index > 0 and row['Turn ID'] == df.at[index + 1, 'Turn ID'] and row['Mention start'] == df.at[index + 1, 'Mention start'] and row['Mention end'] == df.at[index + 1, 'Mention end']:
                # Update the DataFrame to set 'Incomplete' to True
                df.at[index + 1, 'Incomplete'] = True

    # Iterate through the df and remove all rows where 'Mention form' contains 'INCOMPLETE'
    for index, row in df.iterrows():
        if 'INCOMPLETE' in str(row['Mention form']):
            # Remove the row from the DataFrame
            df.drop(index, inplace=True)

    # Save the updated DataFrame back to the Excel file
    excel_file = excel_folder + '\\' + dialogue_number + '_04_incomplete_removed.xlsx'
    df.to_excel(excel_file, index=False)
    return excel_file
