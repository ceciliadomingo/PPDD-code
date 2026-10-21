# CLEANING SCRIPTS
import json
import os
import re
import regex
from difflib import SequenceMatcher
import Levenshtein

# Function to remove added "
def remove_extra_comillas(response_text, cleaning_report):
	comillas_start_pattern = re.compile(r'^"')
	comillas_end_pattern = re.compile(r'"$')
	cleaned_text = re.sub(comillas_start_pattern, "", response_text)
	cleaned_text = re.sub(comillas_end_pattern, "", cleaned_text)
	if response_text != cleaned_text:
		cleaning_report.append("removed_extra_comillas")
	return cleaned_text, cleaning_report

# Function to remove added ```plaintext``` tags
def remove_plaintext_tags(response_text, cleaning_report):
	cleaned_text = response_text.replace("```","").replace("plaintext\n", "")
	if cleaned_text != response_text:
		cleaning_report.append("removed_plaintext_tags")
	return cleaned_text, cleaning_report

# Function to remove added <transcript> tags
def remove_transcript_tags(response_text, cleaning_report):
	cleaned_text = response_text.replace("<transcript>\n","").replace("\n</transcript>", "")
	if cleaned_text != response_text:
		cleaning_report.append("removed_transcript_tags")
	return cleaned_text, cleaning_report

# Function to separate pronouns from contracted verbs. Our annotations seaparate them, but the LLMs sometimes rejoin them
def separate_contracted_verbs_cr(response_text, cleaning_report):
	contracted_verbs = ["'m", "'re", "'ve", "'ll", "'d"] # We're excluding 's due to conflicts with let's. We can observe the impact of such cases later and leave that for future work if needed
	for verb in contracted_verbs:
		cleaned_text = re.sub((verb + r"<(/C?\d*)M>"), (r"</\1M>" + verb), response_text)
	if response_text != cleaned_text:
		cleaning_report.append("separated_contracted_verbs_cr")
	return cleaned_text, cleaning_report

# Function to fix cases where the LLM replaces <M>I.. with <I> (somehow oddly common)
def fix_i(response_text, cleaning_report):
	cleaned_text =  re.sub(r'<I>', r'<M>I', response_text)
	cleaned_text =  re.sub(r'<I<', r'<M>I<', cleaned_text)
	return cleaned_text, cleaning_report

# Function to fix cases where the LLM puts the C tag outside the M tag
def put_c_back_inside_m(response_text, cleaning_report):
	c_outside_pattern = re.compile(r'</M>(C\d+)')
	cleaned_text = re.sub(c_outside_pattern, r'</\1M>', response_text)
	# In case the C also contained an M, I'll fix the resulting </C4M>M>
	cleaned_text = re.sub(r'</C(\d+)M>M>', r'</C\1M>', cleaned_text)
	if cleaned_text != response_text:
		cleaning_report.append("put_c_back_inside_m")
	return cleaned_text, cleaning_report

# Function to add a backlash before the C tag where it's missing
def put_backlash_before_c(response_text, cleaning_report):
	find_c_with_slash_bad_pattern = re.compile(r'<C(\d)/M>')
	cleaned_text = re.sub(find_c_with_slash_bad_pattern, r'</C\1M>', response_text)
	if cleaned_text != response_text:
		cleaning_report.append("put_backlash_before_c")
	return cleaned_text, cleaning_report

# Function to ensure original and response have the same newline at the end of the string, as sometimes the LLM misses it or adds it
def compare_newline(response_text, original_tagged, cleaning_report):
	newline_at_end_pattern = r'\\n$'
	match_original = re.search(newline_at_end_pattern, original_tagged)
	match_response = re.search(newline_at_end_pattern, response_text)
	# Check if correction is needed
	performed_correction = False
	if match_original and not match_response:
		fixed_response = re.sub(r'$', r'\\n', response_text)
		performed_correction = True
	if match_response and not match_original:
		performed_correction = True
		fixed_response = re.sub(r'\\n$', '', response_text)
	if match_original and match_response:
		performed_correction = False
	if not match_original and not match_response:
		performed_correction = False
	# Return results
	if performed_correction:
		cleaning_report.append("compared_newline")
		return fixed_response, cleaning_report
	if not performed_correction:
		return response_text, cleaning_report

# Function to fix cases where the closing C tag does contain the M closing tag, but after an additional closing M tag
def fix_c_outside_c(response_text, cleaning_report):
	c_outside_pattern = re.compile(r'</M><C(\d+)M>') # </M><C4M>
	cleaned_text = re.sub(c_outside_pattern, r'</C\1M>', response_text)
	if cleaned_text != response_text:
		cleaning_report.append("fixed_c_outside_c")
	return cleaned_text, cleaning_report

# Function to fix cases where some mention tags have no closing, or where a closing has no opening; we remove the unmatched tags
def clean_mismatched_tags(response_text, cleaning_report):
	tag_pattern = re.compile(r'</?C?\d*M>')  # matches <M>, </M>, </C123M>
	number_of_fixes = 0
	result = []
	stack = []
	out_pos = 0 # for tracking the length of the cleaned output so far. To keep track of the tag spans without built-in methods
	last_end = 0 
	not_contemplated_tags = [] 
	for match in tag_pattern.finditer(response_text): # find all tags. Using finditer instead of sinply findall to get attributes of matches
		start, end = match.span() # Get span
		tag = match.group() # Get label
		text_before = response_text[last_end:start]
		result.append(text_before) # Save the text before this label
		out_pos += len(text_before)
		# We add all opening labels
		if tag == "<M>":
			stack.append((out_pos, out_pos + len(tag))) # Record tag span so then what's left in the stack is informative
			result.append(tag)
			out_pos += len(tag)
		# We inspect the closing labels
		elif tag.startswith("</"):
			# If we previously loaded an umatched opening tag, we validate this closing tag and empty the stack
			if stack:
				stack.pop() # Pop deletes ONE item from stack of openings, these opening and closing tags are paired
				# It will delete the latest one added, so this way the smaller mentions are dealt before the broader mention in ensted mentions :)
				result.append(tag)  # valid closer
				out_pos += len(tag)
			else:
				# Skip mismatched closer
				number_of_fixes += 1
		else:
			# In case of other hallucianted tags
			result.append(tag)
			not_contemplated_tags.append(tag)
			out_pos += len(tag)
		# Update the index we last looked at to start there in teh enxt iteration
		last_end = end
	# Append any trailing text after the last tag
	result.append(response_text[last_end:])
	cleaned_response = "".join(result)
	# Check if some opening tag was also mismatched
	# To do that, we'll repeat the iteration in reverse, this time on the cleaned text
	if stack:
		number_of_fixes += len(stack)
		# We saved the tags in the stack with spans, so now we locate the mismatched ones and remove those indexes
		for start_idx, end_idx in reversed(stack):
			cleaned_response = cleaned_response[:start_idx] + cleaned_response[end_idx:]
	if cleaned_response != response_text:
		cleaning_report.append(f"cleaned_{number_of_fixes}_mismatched_tags")
	if len(not_contemplated_tags) > 0:
		cleaning_report.append(f"found_{len(not_contemplated_tags)}_not_contemplated_tags_{'_'.join(set(not_contemplated_tags))}")
	return cleaned_response, cleaning_report

# Function to check that the LLM didn't add mentions where the input didn't have them
def check_number_of_mentions(response_text, original_tagged, cleaning_report):
	# copy response text
	cleaned_text = response_text
	mention_pattern = regex.compile(r"<M>(?:[^<]+|<(?!/?M|/M>)|(?R))*</M>")
	original_mentions = mention_pattern.findall(original_tagged, overlapped=True) # Overlapped allows (?R) to capture the nested structures with recursion
	mention_pattern_with_c = regex.compile(r'<M>(?:[^<]+|<(?!/?M|/C\d+M>)|(?R))*</(?:M|C\d+M)>')
	response_mentions = mention_pattern_with_c.findall(cleaned_text, overlapped=True)
	# Remove tags from original mentions to avoid issues comparing nested mentions
	original_mentions_no_tags = []
	for mention in original_mentions:
		mention_cleaned = mention.replace("</M>", "").replace("<M>", "")
		original_mentions_no_tags.append(mention_cleaned)
	# Check if the mentions were in the original (all comparisons without tags to look at mention without considering diffs in submentions). If not, remove tags from response
	hallucinated_mentions = []
	for response_mention in response_mentions:
		# Original mentions and response will both have all tags removed for easier comparison
		without_tags = response_mention.replace("</M>", "").replace("<M>", "")
		without_tags =  re.sub(r'</(C\d+)?M>', r'', without_tags) # Remove final tag
		if without_tags not in original_mentions_no_tags:
			hallucinated_mentions.append(response_mention)
	# Dehallucinating
	if len(hallucinated_mentions) > 0:
		for hallucination in hallucinated_mentions:
			hallucination_without_outer_tags = re.sub(r'^<M>', "", hallucination) # Remove initial tag
			hallucination_without_outer_tags = re.sub(r'</(C\d+)?M>$', "", hallucination_without_outer_tags) # Remove final tag
			# Replace the hallucination with the hallucination without outer tags
			#cleaned_text = re.sub(f'{hallucination}', f"{hallucination_without_outer_tags}", cleaned_text)
			cleaned_text = cleaned_text.replace(hallucination, hallucination_without_outer_tags)
		cleaning_report.append(f"removed_{len(hallucinated_mentions)}_hallucinated_mentions")
	return cleaned_text, cleaning_report

# -------------------------------------------------------------------------------------------------------------------------
# Auxiliary functions for "compare_against_original"
def tokenize_with_spans(text):
    #Tokenize text into tags with optional attached punctuation, words, or punctuation, preserving their start/end positions.
    pattern = re.compile(r'<[^>]+>[^<\s]*|[^\s<>]+|\s+')
    return [(m.group(), m.start(), m.end()) for m in pattern.finditer(text)]

def normalize_token(token):
    #Normalize tags by removing C IDs, with words and punctuation unchanged
    if token.startswith('<'):
        m = re.match(r'<(/?)([A-Z]+)[^>]*>', token)
        if m:
            return f"<{m.group(1)}{m.group(2)}>"
    return token

def align_preserve_cids_and_spaces(response_text, original_tagged):
    # Tokenize original and normalize
    orig_tokens = [t for t, _, _ in tokenize_with_spans(original_tagged)]
    norm_orig = [normalize_token(t) for t in orig_tokens]

    # Tokenize response and normalize
    resp_tokens_with_spans = tokenize_with_spans(response_text)
    resp_tokens_norm = [normalize_token(t) for t, _, _ in resp_tokens_with_spans]

    # Use SequenceMatcher to find matching blocks
    matcher = SequenceMatcher(a=norm_orig, b=resp_tokens_norm)
    result_spans = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ('equal', 'replace') and j2 > j1:
            # Extract substring from response using the original spans (keeps spaces & C IDs)
            start = resp_tokens_with_spans[j1][1]
            end = resp_tokens_with_spans[j2-1][2]
            result_spans.append((start, end))

    # Merge spans into final string
    return ''.join(response_text[start:end] for start, end in result_spans)

# function to do a final check comparing original and response, to see if they are very different after all corrections.
# We allow some margin of added length due to C IDs, but:
# if the response is much longer we realign it preserving C IDs and spaces and check similarity again
# if it's shorter we also check similarity as it could be a case of overcleaning
def compare_against_original(response_text, original_tagged, cleaning_report):
	# Compare lengths. Response should be longer due to C IDs, so we only allow that margin
	original_length = len(original_tagged)
	# Locate mentions in original to count how many C IDs we need to add to length
	mention_pattern = regex.compile(r"<M>(?:[^<]+|<(?!/?M|/M>)|(?R))*</M>")
	original_mentions = mention_pattern.findall(original_tagged, overlapped=True) # Overlapped allows (?R) to capture the nested structures with recursion
	number_of_mentions_in_original = len(original_mentions)
	response_length = len(response_text)
	if response_length > (original_length + (3*number_of_mentions_in_original)): # The 4 represents C\d{1,3} for each mention.
		fixed_response = align_preserve_cids_and_spaces(response_text, original_tagged)
		cleaned_text = fixed_response
		if Levenshtein.ratio(cleaned_text, response_text) < 1:
			cleaning_report.append(f"hallucination_check_LONGER-THAN-ORIGINAL: Similairty ratio is {Levenshtein.ratio(cleaned_text, response_text)}")
	elif response_length < original_length:
		cleaned_text = response_text
		if Levenshtein.ratio(cleaned_text, response_text) < 1:
			cleaning_report.append(f"hallucination_check_SHORTER-THAN-ORIGINAL: Similarity ratio is {Levenshtein.ratio(cleaned_text, response_text)}")	
	else:
		cleaned_text = response_text
		if Levenshtein.ratio(cleaned_text, response_text) < 1:
			cleaning_report.append(f"hallucination_check_WITHIN-RANGE-OF-ORIGINAL: Similarity ratio is {Levenshtein.ratio(cleaned_text, response_text)}")
	return cleaned_text, cleaning_report
# ----------------------------------------------------------------------------------------------------------------------------------------------------------




def clean_cr_output(response_text, original_tagged, dialogue_number, approach, turn_id, report_folder):
	cleaned_text, cleaning_report = remove_extra_comillas(response_text, cleaning_report)
	cleaned_text, cleaning_report = remove_plaintext_tags(cleaned_text, cleaning_report)
	cleaned_text, cleaning_report = remove_transcript_tags(cleaned_text, cleaning_report)
	cleaned_text, cleaning_report = separate_contracted_verbs_cr(cleaned_text, cleaning_report)
	cleaned_text, cleaning_report = fix_i(cleaned_text, cleaning_report)
	cleaned_text, cleaning_report = put_c_back_inside_m(cleaned_text, cleaning_report)
	cleaned_text, cleaning_report = put_backlash_before_c(cleaned_text, cleaning_report)
	cleaned_text, cleaning_report = compare_newline(cleaned_text, original_tagged, cleaning_report)
	cleaned_text, cleaning_report = fix_c_outside_c(cleaned_text, cleaning_report)
	cleaned_text, cleaning_report = clean_mismatched_tags(cleaned_text, cleaning_report)
	cleaned_text, cleaning_report = check_number_of_mentions(cleaned_text, original_tagged, cleaning_report)
	cleaned_text, cleaning_report = compare_against_original(cleaned_text, original_tagged, cleaning_report)
	# Save cleaning report
	if not os.path.exists(os.path.join(report_folder, approach)):
		cleaning_report_json = {}
	else:
		with open(os.path.join(report_folder, approach, f"cleaning_report_{approach}.json"), 'r') as f:
			cleaning_report_json = json.load(f)
	cleaning_report_json[turn_id] = cleaning_report
	report_path = os.path.join(report_folder, f"cleaning_report_{approach}.json")
	with open(report_path, 'a+') as f:
		json.dump(cleaning_report_json, f, indent=4)
	if cleaned_text != response_text:
		print(f"Report for dialogue {dialogue_number}, turn {turn_id}: {cleaning_report}", file=open(os.path.join(report_folder, f"{approach}comparing gt and clean.txt"), 'a+', encoding='utf-8'))
		print(f"Original response text for dialogue {dialogue_number}, turn {turn_id}: {response_text}", file=open(os.path.join(report_folder, f"{approach}comparing gt and clean.txt"), 'a+', encoding='utf-8'))
		print(f"Cleaned text for dialogue {dialogue_number}, turn {turn_id}: {cleaned_text}", file=open(os.path.join(report_folder, f"{approach}comparing gt and clean.txt"), 'a+', encoding='utf-8'))
		print("--------------------------------------------------", file=open(os.path.join(report_folder, f"{approach}comparing gt and clean.txt"), 'a+', encoding='utf-8'))
	return cleaned_text, cleaning_report



