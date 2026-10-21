

# fs example = (fs_dialogue_number, fs_turn_ID,fs_transcript, fs_tagged_transcript)
#fs_examples = [('004x021', 436, "I love Paris. It is a nice city.", "<M>I</M> love <M>this Paris</M>. <M>It</M> is <M>a nice city</M>.")]
#two_prompt_fs_examples = [('004x021', 436, "I love Paris. It is a nice city.", "<M>I</M> love this <M>Paris</M>. <M>It</M> is a nice <M>city</M>.", "<M>I</M> love <M>this Paris</M>. <M>It</M> is <M>a nice city</M>.")]


def convert_tagged_text_to_tagged_heads(tagged_text,model_for_span_changing):
    # Input: "<M>I</M> love <M>this Paris</M>. <M>It</M> is <M>a nice city</M>."
    # Output: "<M>I</M> love this <M>Paris</M>. <M>It</M> is a nice <M>city</M>."
    mention_pattern = re.compile(r'<M>(.*?)</M>')
    matches = mention_pattern.findall(tagged_text)
    for match in matches:
        #print("Mention found:", match)
        mention_doc = model_for_span_changing(match)
        nucleus = mention_doc[:].root
        #print("Head of mention:", nucleus.text)
        # Replace the mention in the tagged text with its head
        fixed_mention = match.replace(nucleus.text, f"<M>{nucleus.text}</M>")
        tagged_text = tagged_text.replace(f"<M>{match}</M>", fixed_mention)
    return tagged_text

def convert_fs_example_list_to_two_prompt_fs_examples(fs_examples,model_for_span_changing):
    two_prompt_fs_examples = []
    for fs_example in fs_examples:
        dialogue_number, turn_ID, original_transcript, tagged_transcript = fs_example
        # Convert the tagged transcript to tagged heads
        fixed_tagged_transcript = convert_tagged_text_to_tagged_heads(tagged_transcript,model_for_span_changing)
        # Create the two-prompt example
        two_prompt_example = (dialogue_number, turn_ID, original_transcript, fixed_tagged_transcript, tagged_transcript)
        two_prompt_fs_examples.append(two_prompt_example)
    return two_prompt_fs_examples
