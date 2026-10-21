# Functions to convert separated mentions from the mentions jason file into coreference chains

# Function to convert floats to integers, as excel may parse some numbers as floats
# We need this to process the numbers of the referent spans
def convert_to_int_if_float(value):
    import pandas as pd
    # If it's a float (and not nans, those are detected as floats) #and it is convertible to integer
    if isinstance(value, float) and not pd.isna(value):# and value.is_integer():
        return int(value)
    else:
        return value

# Function to find clusters in a list of edges
# We need this to use a graph algorithm to find all connected mentions in the mentions JSON
def find_clusters(edges):
    from collections import defaultdict, deque
    # Build adjacency list (Each key is a node. Each value is a set of neighbors.)
    # For example, from: edges = [('A', 'B'), ('B', 'C')] we get: 
    # graph = {'A': {'B'},
    # 'B': {'A', 'C'},
    # 'C': {'B'}}
    graph = defaultdict(set)
    for a, b in edges:
        graph[a].add(b)
        graph[b].add(a)

    # Tracking variables
    visited = set() # Tracks which nodes we've already explored (to avoid repeats).
    clusters = {} # A dictionary to store the clusters.
    cluster_id = 0 # A numeric key for each new cluster we find.

    for node in graph:
        if node not in visited:
            # Start BFS (Breadth-First Search)
            # Start from the unvisited node.
            # Add it to a queue.
            # Keep visiting neighbors that haven’t been seen yet.
            # Collect everything connected to this node in a set (cluster).

            queue = deque([node])
            cluster = set()

            while queue:
                current = queue.popleft()
                if current not in visited:
                    visited.add(current)
                    cluster.add(current)
                    queue.extend(graph[current] - visited)

            clusters[cluster_id] = cluster # Save cluster in dictionary
            cluster_id += 1 # Move on to the next cluster

    return clusters

# --------------------------------
# MAIN FUNCTION
# --------------------------------
def chain_up_mentions(chain_json, dialogue_number, excel_file, output_log):

    # Load the chain JSON file
    with open(chain_json, 'r', encoding='utf-8') as f:
        single_mentions_data = json.load(f)

    # Load the excel file
    excel_df = pd.read_excel(excel_file)

    # Create a list to add all the edges
    edges = []

    # Iterate through chain JSON and extract the row ID
    # Check row with that row ID in the excel file, see if it has a discourse referent
    # if it does, add the mention row and the discourse referent to the mention_row_id_dict    
    # Then use the mention_row_id_dict to move the mentions to links in the connected part of the chains json using a graph algorithm
    
    # Use the Row ID to order the mentions in the chain JSON
    # Also use that info to fill out the first mention and cataphora fields:
    # First mention is true if the mention has no discourse referent and it's the lowest or second lowest row ID in the chain.
    # Cataphora is true if the mention has a referent with a row ID in the future

    for single_mention in single_mentions_data['CHAINS']['SINGLE MENTIONS']:
        # Initialise referent row ID for debugging
        referent_row_ID = None
        single_mention_row_ID = single_mention['MENTION ID']
        single_mention_row_in_df = excel_df[excel_df['Row ID'] == single_mention_row_ID]
        discourse_referent_turn_ID = single_mention_row_in_df['Referent Turn ID'].iloc[0]
        discourse_referent_start = single_mention_row_in_df['Referent Turn Span Start'].iloc[0]
        discourse_referent_end = single_mention_row_in_df['Referent Turn Span End'].iloc[0]

        if pd.notna(discourse_referent_turn_ID): # If this mention has a referent, we need to connect them
            # Finding the referent's row ID
            # (I convert all values to string in case they are parsed as different types and thus not matching)
            # (Before that, I convert the floats to ints lest the strings end up having a .0 at the end) that causes a mismatch)
            for index, referent_as_mention_in_excel in excel_df.iterrows():
                #print(f"Checking if span start of mention as referent {str(convert_to_int_if_float(referent_as_mention_in_excel['Mention start']))} matches the discourse referent start {str(convert_to_int_if_float(discourse_referent_start))} for mention with Row ID {single_mention_row_ID}.", file=open(output_log, 'a+'))
                if str(convert_to_int_if_float(referent_as_mention_in_excel['Turn ID'])) == str(convert_to_int_if_float(discourse_referent_turn_ID)) and \
                    str(convert_to_int_if_float(referent_as_mention_in_excel['Mention start'])) == str(convert_to_int_if_float(discourse_referent_start)) and \
                    str(convert_to_int_if_float(referent_as_mention_in_excel['Mention end'])) == str(convert_to_int_if_float(discourse_referent_end)):
                        referent_row_ID = referent_as_mention_in_excel['Row ID']
                        # Create mention, referent tuple
                        mention_referent_tuple = (single_mention_row_ID, referent_row_ID)
            if not referent_row_ID:
                print(f"Error: Could not find referent as mention for the mention with Row ID {single_mention_row_ID}.", file=open(output_log, 'a+'))
                # Create mention, referent tuple
                # We don't have a referent row ID (e.g., the annotator added as referent a mention that did not exists as mention, or used a whole turn as referent)
                # So instead of the referent row ID, we use the full referent info
                string_to_replace_referent_row_ID = str(convert_to_int_if_float(discourse_referent_turn_ID)) + '+' + str(convert_to_int_if_float(discourse_referent_start)) + '+' + str(convert_to_int_if_float(discourse_referent_end))
                mention_referent_tuple = (single_mention_row_ID, string_to_replace_referent_row_ID)

            edges.append(mention_referent_tuple)
    
    dictionary_of_chains = find_clusters(edges)
    print(dictionary_of_chains, file=open(output_log, 'a+'))

    # Now we use the dictionary of clusters to update the chain JSON
    linked_mentions_list = []
    for cluster_id, cluster in dictionary_of_chains.items():
        # Get the mentions in the cluster
        mentions_in_cluster = [mention for mention in single_mentions_data['CHAINS']['SINGLE MENTIONS'] if mention['MENTION ID'] in cluster]
        
        # Sort mentions by their row ID
        mentions_in_cluster.sort(key=lambda x: x['MENTION ID'])

        # Create a new chain entry
        new_chain_entry = {'CHAIN ID': f"{dialogue_number}_chain_{cluster_id}",
                            'MENTIONS':mentions_in_cluster
                        }
        # Add it to the linked mentions list
        linked_mentions_list.append(new_chain_entry)

        # Iterate through single mentions and remove the objects that are now in a chain
        for mention in mentions_in_cluster:
            # Remove the mention from the single mentions list
            single_mentions_data['CHAINS']['SINGLE MENTIONS'].remove(mention)
    
    # Add the new chain entries  to the json data
    single_mentions_data['CHAINS']['LINKED MENTIONS']['TASK MENTIONS'] = linked_mentions_list

            
    # Save the updated chain JSON
    output_chain_json = os.path.join(os.path.dirname(chain_json), f"{dialogue_number}_09_updated_chains.json")
    with open(output_chain_json, 'w', encoding='utf-8') as f:
        json.dump(single_mentions_data, f, indent=4, ensure_ascii=False)

    return output_chain_json
