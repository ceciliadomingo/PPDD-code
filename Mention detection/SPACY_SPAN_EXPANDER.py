

def convert_tagged_heads_to_mentions(tagged_text, loaded_model):
    # Input: "<M>I</M> love this <M>Paris</M>. <M>It</M> is a nice <M>city</M>."
    # Output: "<M>I</M> love <M>this Paris</M>. <M>It</M> is <M>a nice city</M>."
    mention_pattern = re.compile(r'<M>(.*?)</M>')
    matches = [(match.group(), match.start(), match.end()) for match in mention_pattern.finditer(tagged_text)]
    # Index 0 is matched text <M>I</M>
    # Index 1 is start index
    # Index 2 is end index
    #print(matches)
    untagged_text = tagged_text.replace("<M>","").replace("</M>", "")
    mention_doc = loaded_model(untagged_text)
    phrases_list = []
    for match in matches:
        #print("Mention found:", match[0].replace("<M>","").replace("</M>", ""))
        for token in mention_doc:
            if token.text == match[0].replace("<M>","").replace("</M>", ""):
                # If the token is the main verb, I don't want to extract the whole sentence as a phrase, in most cases that won't be a mention
                if token.dep_ == "ROOT" and token.pos_ == "VERB":
                    head_pattern = re.compile(re.escape(match[0].replace("<M>","").replace("</M>", ""))) # I use escape in case the match contains characters that need escaping
                    head_location_in_phrase = [(token.text, 0, len(token.text))]
                    phrase_info = (token.text, head_location_in_phrase)
                else:
                    phrase = mention_doc[min([t.i for t in token.subtree]) : max([t.i for t in token.subtree]) + 1]
                    #print("Phrase of mention:", phrase.text)
                    #print("Length of phrase:", len(phrase.text))
                    head_pattern = re.compile(re.escape(match[0].replace("<M>","").replace("</M>", ""))) # I use escape in case the match contains characters that need escaping
                    head_location_in_phrase = [(match.group(), match.start(), match.end()) for match in head_pattern.finditer(phrase.text)]
                    #print("Location of head in phrase", head_location_in_phrase)
                    phrase_info = (phrase.text, head_location_in_phrase)
                phrases_list.append(phrase_info)
    # Remove duplicates, which can happen with single-word mentions:
    phrases_list = set((word, tuple(tuplecontents)) for word, tuplecontents in phrases_list)
    phrases_list = list(phrases_list)
    #print(f"phrases without duplicates: {phrases_list}")
    # Replace the head in the tagged text with the mention  
    list_of_found_phrases_in_text = []
    list_index_counter = 0
    for phrase_info in phrases_list:
        phrase_in_text_pattern = re.compile(re.escape(phrase_info[0])) # I use escape in case the match contains characters that need escaping
        found_phrase = [(match.group(), match.start(), match.end()) for match in phrase_in_text_pattern.finditer(untagged_text)]
        phrase_in_text_info = list_index_counter, found_phrase
        list_of_found_phrases_in_text.append(phrase_in_text_info)
        list_index_counter += 1
    #print(f"phrases found in untagged text: {list_of_found_phrases_in_text}")
    # If a mention is repeated, the list has an ugly structure like 
    #[(0, [('I', 0, 1), ('I', 18, 19)]), (1, [('it', 14, 16), ('it', 26, 28)])]
    cleaned_list_of_found_phrases_in_text = []
    for unique_phrase in list_of_found_phrases_in_text:
        for item in unique_phrase[1]:
            cleaned_list_of_found_phrases_in_text.append(item)
    #print(f"cleaned list: {cleaned_list_of_found_phrases_in_text}")
    # Get list of indexes to put closing and opening tags
    closing_indexes_list = []
    opening_indexes_list = []
    for phrase_data in cleaned_list_of_found_phrases_in_text:
        #print(phrase_data)
        closing_index = phrase_data[2]
        closing_indexes_list.append(closing_index)
        opening_index = phrase_data[1]
        opening_indexes_list.append(opening_index)
    # I now put all indexes in the same list (with infor about whether they are opening or closing) to be able to traverse them in order, especially if there are nested mentions
    list_of_all_indexes = []
    for index in closing_indexes_list:
        index_tuple = (index, "E") # E for end
        list_of_all_indexes.append(index_tuple)
    for index in opening_indexes_list:
        index_tuple = (index, "S") # S for start
        list_of_all_indexes.append(index_tuple)
    # Order index lists
    list_of_all_indexes.sort(key=lambda x: x[0], reverse=True)
    # Now with the list of phrases in the text linked to the list of heads, we can add the tags
    # I traverse the list starting from the end to avoid having to iteratively add 3 or 4 to the index whenever I add a label
    tagged_text_reworked = untagged_text
    for index, mention_type in list_of_all_indexes:
        if mention_type == 'S':
            # Add the opening tag
            tagged_text_reworked = tagged_text_reworked[:index] + '<M>' + tagged_text_reworked[index:]
        elif mention_type == 'E':
            # Add the closing tag
            tagged_text_reworked = tagged_text_reworked[:index] + '</M>' + tagged_text_reworked[index:]
    return tagged_text_reworked