import random
import string

# Function to generate ID numbers for Heidi json metadata
def annotation_ID_generator(length, log_of_used_IDs):

    # Load list to keep track of generated strings
    with open(log_of_used_IDs, 'a+') as file:
        used_strings = file.readlines()

    characters = string.ascii_letters + string.digits
    while True:
        random_string = ''.join(random.choices(characters, k=length))
        if random_string not in used_strings:
            used_strings.append(random_string)
            print(random_string, file=open(log_of_used_IDs, 'a'))
            return random_string

# -------------------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------------------
# Function to extract potential mentions from text using spaCy
def spacy_mention_extractor(text: str,lang_model, turn_ID, log_of_used_IDs):  

    #Parse text with spaCy
    text_parsed = lang_model(text)

    result = []

    # Extract noun phrases, their indices, and grammatical number
    for chunk in text_parsed.noun_chunks:  
        #Process pronouns separately
        if len(chunk) == 1 and chunk.root.pos_ == "PRON":
            mention_gram_number = "Singular" if chunk.root.morph.get("Number") == ["Sing"] else "Plural"
            mention_label = "Pronoun-->Demonstrative" if ("this" in chunk.text or "that" in chunk.text) else "Pronoun-->Personal"
        #Non-pronoun noun phrases 
        else:
            # Check the number for the root token of the noun phrase
            root_token = chunk.root
            mention_gram_number = "Singular" if root_token.morph.get("Number") == ["Sing"] else "Plural"
            mention_label = "NP-->Definite" if ("the" in chunk.text or "The" in chunk.text) else "NP-->Indefinite"
        
        mention_value_dict = {"start": chunk.start_char, "end": chunk.end_char, "text": chunk.text, "labels": [mention_label]}
        mention_gram_number_dict =  {"start": chunk.start_char, "end": chunk.end_char, "text": chunk.text, "choices": [mention_gram_number]}
        
        #Generate random ID
        mention_ID = annotation_ID_generator(10)

        mention_entry_dict = {"value": mention_value_dict,
                        "id": mention_ID,
                        "from_name": "labels",
                        "to_name": "text",
                        "type": "labels",
                        "origin": "manual"}
        number_entry_dict = {"value": mention_gram_number_dict,
                        "id": mention_ID,
                        "from_name": "Number",
                        "to_name": "text",
                        "type": "choices",
                        "origin": "manual"}
        turnID_entry_dict = {"value":{"text": ["TURN " + str(turn_ID)]},
                        "from_name": "generated_text",
                        "to_name": "text",
                        "type": "textarea",
                        "origin": "manual"}
    
        #Add mention to result
        result.append(mention_entry_dict)
        result.append(number_entry_dict)
        result.append(turnID_entry_dict)
    return result