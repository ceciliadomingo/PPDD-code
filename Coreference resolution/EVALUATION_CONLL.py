# CONLL EVALUATION
import os
import json
import re
import random
import statistics


# EXTRACTING COREFERENCE CHAINS (ground truth + locating the already extracted predicted chains)
# The dictionaries of clusters need to be in the same format. For each mention, they need to have the turn ID, the mention form, and the span start and end.
# Any additional infomration like mention ID would hinder the comparisons
def locate_annotator_json(dialogue_number, annotation_folder):
    speakers_pattern = re.compile(r'(\d\d\d)[xX_-](\d\d\d)')
    speaker_A = speakers_pattern.search(dialogue_number).group(1)
    speaker_B = speakers_pattern.search(dialogue_number).group(2)
    for file in os.listdir(annotation_folder):
        if file.endswith('_NOTCODE.json') and speaker_A in file and speaker_B in file:
            return os.path.join(annotation_folder, file)

def extract_dict_of_GT_clusters(annotator_json):
    # Initialise the dicitonary and the key variable (the keys will just be numbers)
    dict_of_GT_clusters = {}
    current_key = 0
    # Load the json
    with open(annotator_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # First let's add the speaker mentions
    for speaker in data["CHAINS"]["LINKED MENTIONS"]["SPEAKER MENTIONS"]:
        mentions_in_this_chain = []
        for mention in data["CHAINS"]["LINKED MENTIONS"]["SPEAKER MENTIONS"][speaker]:
            current_key += 1
            turn_ID = mention["Turn ID"]
            mention_text = mention["Mention"]
            span_start = mention["Mention start"]
            span_end = mention["Mention end"]
            mentions_in_this_chain.append((turn_ID, mention_text, span_start, span_end))
        dict_of_GT_clusters[current_key] = mentions_in_this_chain
    # Now let's look at task mentions
    for task_chain in data["CHAINS"]["LINKED MENTIONS"]["TASK MENTIONS"]:
        mentions_in_this_chain = []
        for mention in task_chain["MENTIONS"]:
            current_key += 1
            turn_ID = mention["TURN ID"]
            mention_text = mention["MENTION"]
            span_start = mention["SPAN"]["START"]
            span_end = mention["SPAN"]["END"]
            mentions_in_this_chain.append((turn_ID, mention_text, span_start, span_end))
        dict_of_GT_clusters[current_key] = mentions_in_this_chain
    # And finally the singletons
    for singleton in data["CHAINS"]["SINGLE MENTIONS"]:
        current_key += 1
        turn_ID = singleton["TURN ID"]
        mention_text = singleton["MENTION"]
        span_start = singleton["SPAN"]["START"]
        span_end = singleton["SPAN"]["END"]
        dict_of_GT_clusters[current_key] = [(turn_ID, mention_text, span_start, span_end)]
    return dict_of_GT_clusters


# CEAF 4
# CEAF4 Precision
# True positives / Total predicted mentions
# True positives =  average for all GT chains of: intersect of GT chain and most similar predicted chain (number of mentions that they have in common)
# CEAF4 Recall
# True positives / Total GT mentions

# I use as matching algorithm:
# Greedy algorithm that can match the same ideal match for more than one query chain
# Hungarian algorithm that can only match the ideal match for one query chain, and then removes it from the pool of candidates for the next query chains
def ceaf4_precision_greedy(dict_of_GT_clusters, dict_of_pred_clusters):
	precisions_list = []
	for pred_chain in dict_of_pred_clusters.values():
		# Find the most similar GT chain
		most_similar_gt_chain = [] # Initailise as 0 in case no GT chain has any overlap
		for gt_chain in dict_of_GT_clusters.values():
			# The most similar gt chain to a pred chain is the one who has the most number of mentions in common with it
			similarity_with_pred_chain = set(pred_chain) & set(gt_chain)
			# If this chain is a better fit than the previous ones we looked at, update best fit
			if len(similarity_with_pred_chain) > len(most_similar_gt_chain):
				most_similar_gt_chain = gt_chain
		# Calculate precision for this pred chain
		overlap_for_this_chain = set(pred_chain) & set(most_similar_gt_chain)
		precision_for_this_chain = len(overlap_for_this_chain) / len(pred_chain)
		precisions_list.append(precision_for_this_chain)
	average_precision_greedy = statistics.mean(precisions_list) if len(precisions_list) > 0 else 0
	return average_precision_greedy

def ceaf_precision_hungarian(dict_of_GT_clusters, dict_of_pred_clusters):
    # Proper ceaf should follow the Hungarian bipartite one-to-one algorithm where, once a perfect match is found, the matched chain cannot be matched with any other
    precisions_list_hungarian = []
    # I initialise the list of unmatched GT chains, which will shrink as I match pred and GT chains
    list_of_unmatched_gt_chains = []
    for gt_chain in dict_of_GT_clusters.values():
        list_of_unmatched_gt_chains.append(gt_chain)
    for pred_chain in dict_of_pred_clusters.values():
        # Find the most similar GT chain
        most_similar_gt_chain_hungarian = [] # Initailise as 0 in case no GT chain has any overlap
        if len(list_of_unmatched_gt_chains) > 0: # If there are no GT chains left for matching, this will be precision 0
            for gt_chain in list_of_unmatched_gt_chains:
                # The most similar gt chain to a pred chain is the one who has the most number of mentions in common with it
                similarity_with_pred_chain = set(pred_chain) & set(gt_chain)
                # If this chain is a better fit than the previous ones we looked at, update best fit
                if len(similarity_with_pred_chain) > len(most_similar_gt_chain_hungarian):
                    most_similar_gt_chain_hungarian = gt_chain
            # After finding the perfect match, I remove it from the available candidates
            if len(most_similar_gt_chain_hungarian) > 0: # If the match is the default 0, that's not on the list to be removed
                list_of_unmatched_gt_chains.remove(most_similar_gt_chain_hungarian)
            # Calculate precision for this pred chain
            overlap_for_this_chain = set(pred_chain) & set(most_similar_gt_chain_hungarian)
            precision_for_this_chain_hungarian = len(overlap_for_this_chain) / len(pred_chain)
            precisions_list_hungarian.append(precision_for_this_chain_hungarian)
        else:
            precision_for_this_chain_hungarian = 0
            precisions_list_hungarian.append(precision_for_this_chain_hungarian)
    average_precision_hungarian = statistics.mean(precisions_list_hungarian) if len(precisions_list_hungarian) > 0 else 0
    return average_precision_hungarian 

def ceaf_recall_hungarian(dict_of_GT_clusters, dict_of_pred_clusters):
    # Proper ceaf should follow the Hungarian bipartite one-to-one algorithm where, once a perfect match is found, the matched chain cannot be matched with any other
    recall_list_hungarian = []
    # I initialise the list of unmatched pred chains, which will shrink as I match pred and GT chains
    list_of_unmatched_pred_chains = []
    for pred_chain in dict_of_pred_clusters.values():
        list_of_unmatched_pred_chains.append(pred_chain)
    for gt_chain in dict_of_GT_clusters.values():
        # Find the most similar pred chain
        most_similar_pred_chain_hungarian = [] # Initailise as 0 in case no GT chain has any overlap
        if len(list_of_unmatched_pred_chains) > 0: # If there are no GT chains left for matching, this will be precision 0
            for pred_chain in list_of_unmatched_pred_chains:
                # The most similar pred chain to a gt chain is the one who has the most number of mentions in common with it
                similarity_with_gt_chain = set(pred_chain) & set(gt_chain)
                # If this chain is a better fit than the previous ones we looked at, update best fit
                if len(similarity_with_gt_chain) > len(most_similar_pred_chain_hungarian):
                    most_similar_pred_chain_hungarian = pred_chain
            # After finding the perfect match, I remove it from the available candidates
            if len(most_similar_pred_chain_hungarian) > 0: # If the match is the default 0, that's not on the list to be removed
                list_of_unmatched_pred_chains.remove(most_similar_pred_chain_hungarian)
            # Calculate precision for this pred chain
            overlap_for_this_chain = set(gt_chain) & set(most_similar_pred_chain_hungarian)
            recall_for_this_chain_hungarian = len(overlap_for_this_chain) / len(gt_chain)
            recall_list_hungarian.append(recall_for_this_chain_hungarian)
        else:
            recall_for_this_chain_hungarian = 0
            recall_list_hungarian.append(recall_for_this_chain_hungarian)
    average_recall_hungarian = statistics.mean(recall_list_hungarian) if len(recall_list_hungarian) > 0 else 0
    return average_recall_hungarian       

def ceaf4_recall_greedy(dict_of_GT_clusters, dict_of_pred_clusters):
    recalls_list = []
    for gt_chain in dict_of_GT_clusters.values():
        # Find the most similar pred chain
        most_similar_pred_chain = [] # I initialise as 0 in case no pred chain has any overlap
        for pred_chain in dict_of_pred_clusters.values():
            # The most similar pred chain to a GT chain is the one who has the most number of mentions in common with it
            similarity_with_gt_chain = set(pred_chain) & set(gt_chain)
            # If this chain is a better fit than the previous ones we looked at, update best fit
            if len(similarity_with_gt_chain) > len(most_similar_pred_chain):
                most_similar_pred_chain = pred_chain
        # Calculate recall for this pred chain
        overlap_for_this_chain = set(gt_chain) & set(most_similar_pred_chain)
        recall_for_this_chain = len(overlap_for_this_chain) / len(gt_chain)
        recalls_list.append(recall_for_this_chain)
    average_recall_greedy = statistics.mean(recalls_list) if len(recalls_list) > 0 else 0
    return average_recall_greedy


# B3
# B3 Precision
# per mention in pred (it is later averaged over all pred mentions) = 
# (intersect of pred chain where the mention is and GT chain where the mention is [i.e., number of items those chains have in common])/number of items in the output chain where the mention is
# B3 Recall
# per mention in GT (it is later averaged over all GT mentions) = 
# (intersect of GT chain where the mention is and output chain where the mention is [i.e., number of items those chains have in common])/number of items in the ground truth chain where the mention is

def b3_precision(dict_of_GT_clusters, dict_of_pred_clusters):
    b3_precision_list = []
    # I initialise the variable to prevent errors. If it's not overwritten to a match, precision is 0
    overlap_pred_and_gt_chain_for_this_mention = None
    # Go through each predicted mention and then look at the chain it's in (so the iteration is guided by the mention, not the chain)
    for pred_chain in dict_of_pred_clusters.values():
        for pred_mention in pred_chain:
            # Find the GT chain that contains this mention to then calculate overlap with predicted chain
            for gt_chain in dict_of_GT_clusters.values():
                if pred_mention in gt_chain:
                    gt_chain_with_this_mention = gt_chain
                    overlap_pred_and_gt_chain_for_this_mention = set(gt_chain_with_this_mention) & set(pred_chain) # xxx this was outside the if and gave an error
                    break
            if overlap_pred_and_gt_chain_for_this_mention:
                precision_for_this_pred_mention = len(overlap_pred_and_gt_chain_for_this_mention) / len(pred_chain)
                b3_precision_list.append(precision_for_this_pred_mention)
            else:
                precision_for_this_pred_mention = 0
                b3_precision_list.append(precision_for_this_pred_mention)
    average_b3_precision = statistics.mean(b3_precision_list) if len(b3_precision_list) > 0 else 0
    return average_b3_precision

def b3_recall(dict_of_GT_clusters, dict_of_pred_clusters):
    b3_recall_list = []
    # I initialise the variable to prevent errors. If it's not overwritten to a match, recall is 0
    overlap_pred_and_gt_chain_for_this_mention = None
    # Go through each GT mention and then look at the chain it's in (so the iteration is guided by the mention, not the chain)
    for gt_chain in dict_of_GT_clusters.values():
        for gt_mention in gt_chain:
            # Find the pred chain that contains this mention to then calculate overlap with gt chain
            # I initialise the pred chain as an empty chain in case it's never predicted
            pred_chain_with_this_mention = []
            for pred_chain in dict_of_pred_clusters.values():
                if gt_mention in pred_chain:
                    pred_chain_with_this_mention = pred_chain
                    overlap_pred_and_gt_chain_for_this_mention = set(pred_chain_with_this_mention) & set(gt_chain) # xxx this was outside the if and gave an error
                    break
            if overlap_pred_and_gt_chain_for_this_mention:
                recall_for_this_pred_mention = len(overlap_pred_and_gt_chain_for_this_mention) / len(gt_chain)
                b3_recall_list.append(recall_for_this_pred_mention)
            else:
                recall_for_this_pred_mention = 0
                b3_recall_list.append(recall_for_this_pred_mention)
    average_b3_recall = statistics.mean(b3_recall_list) if len(b3_recall_list) > 0 else 0
    return average_b3_recall


# MUC
# Muc Precision
# precision per chain in output (we then extract the average for all output chains) = 
# How many predicted links are also in GT
# (number of items in the chain – number of GT chains that have at least one item from this output chain)/(number of items in the output chain – 1)
# Muc Recall
# per chain in GT (we then extract the average for all GT chains) = 
# Links preserved by predicted clusters
# (number of items in the chain – number of output chains that have at least one item from this GT chain)/(number of items in the GT chain – 1)
def muc_precision(dict_of_GT_clusters, dict_of_pred_clusters):
    # MUC ignores singletons, as the formula for them results in 1-1/1-1
    all_muc_precisions = []
    for pred_chain in dict_of_pred_clusters.values():
        if len(pred_chain) > 1: # ignoring singletons to avoid dividing by 0
            num_mentions_in_pred_chain = len(pred_chain)
            num_of_gt_chains_with_item = 0
            for gt_chain in dict_of_GT_clusters.values():
                if set(pred_chain) & set(gt_chain):
                    num_of_gt_chains_with_item += 1
            if num_of_gt_chains_with_item > 0: # Omitting cases where predicted links are not in GT, as that leads to a larger numerator
                muc_p_this_pred_chain = (num_mentions_in_pred_chain - num_of_gt_chains_with_item) / (num_mentions_in_pred_chain - 1)
                all_muc_precisions.append(muc_p_this_pred_chain)
            else:
                all_muc_precisions.append(0) # If whole chain is unmatched, precision is 0
    muc_precision_average = sum(all_muc_precisions) / len(all_muc_precisions) if all_muc_precisions else 0
    return muc_precision_average

def muc_recall(dict_of_GT_clusters, dict_of_pred_clusters):
    # MUC ignores singletons, as the formula for them results in 1-1/1-1
    all_muc_recalls = []
    for gt_chain in dict_of_GT_clusters.values():
        if len(gt_chain) > 1: # ignoring singletons to avoid dividing by 0
            num_mentions_in_gt_chain = len(gt_chain)
            num_of_pred_chains_with_item = 0
            for pred_chain in dict_of_pred_clusters.values():
                if set(pred_chain) & set(gt_chain):
                    num_of_pred_chains_with_item += 1
            if num_of_pred_chains_with_item > 0: # Omitting cases where GT links are not predicted, as that leads to larger numerator
                muc_r_this_gt_chain = (num_mentions_in_gt_chain - num_of_pred_chains_with_item) / (num_mentions_in_gt_chain - 1)
                all_muc_recalls.append(muc_r_this_gt_chain)
            else:
                all_muc_recalls.append(0) # If whole chain is unmatched, recall is 0
    muc_recall_average = sum(all_muc_recalls) / len(all_muc_recalls) if all_muc_recalls else 0
    return muc_recall_average

def f1(p, r):
    if p + r == 0:
        return 0
    return 2 * (p * r / (p + r))


if __name__ == "__main__":
    dialogue_number = "dddxddd" # Replace with the actual dialogue number you want to evaluate
    annotation_folder = 'path/to/folder/with/annotations'
    GT_json = locate_annotator_json(dialogue_number, annotation_folder)
    predicted_json = locate_annotator_json(dialogue_number)
    dict_of_GT_clusters = extract_dict_of_GT_clusters(GT_json)
    ceaf_p_greedy = ceaf4_precision_greedy(dict_of_GT_clusters, predicted_json)
    ceaf_r_greedy = ceaf4_recall_greedy(dict_of_GT_clusters, predicted_json)
    ceaf_greedy_f1 = f1(ceaf_p_greedy, ceaf_r_greedy)
    print(f"CEAF4 Precision redo: {ceaf_p_greedy}")
    print(f"CEAF4 Recall redo: {ceaf_r_greedy}")
    print(f"CEAF4 F1 redo: {ceaf_greedy_f1}")
    ceaf_precision_hungarian = ceaf_precision_hungarian(dict_of_GT_clusters, predicted_json)
    ceaf_recall_hungarian = ceaf_recall_hungarian(dict_of_GT_clusters, predicted_json)
    ceaf_f1_hungarian = f1(ceaf_precision_hungarian, ceaf_recall_hungarian)
    print(f"CEAF4 Precision Hungarian: {ceaf_precision_hungarian}")
    print(f"CEAF4 Recall Hungarian: {ceaf_recall_hungarian}")
    print(f"CEAF4 F1 Hungarian: {ceaf_f1_hungarian}")
    b3_P = b3_precision(dict_of_GT_clusters, predicted_json)
    b3_R = b3_recall(dict_of_GT_clusters, predicted_json)
    b3_f1 = f1(b3_P, b3_R)
    print(f"B3 Precision: {b3_P}")
    print(f"B3 Recall: {b3_R}")
    print(f"B3 F1: {b3_f1}")
    muc_P = muc_precision(dict_of_GT_clusters, predicted_json)
    muc_R = muc_recall(dict_of_GT_clusters, predicted_json)
    muc_F1 = f1(muc_P, muc_R)
    print(f"MUC Precision: {muc_P}")
    print(f"MUC Recall: {muc_R}")
    print(f"MUC F1: {muc_F1}")