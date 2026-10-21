# Function to convert defaultdict to a regular dict for JSON serialization
# Otherwise the output doesn't come out as a normal pretty json

def convert_to_regular_dict(obj):
    if isinstance(obj, defaultdict):
        return {k: convert_to_regular_dict(v) for k, v in obj.items()}
    elif isinstance(obj, dict):
        return {k: convert_to_regular_dict(v) for k, v in obj.items()}
    elif isinstance(obj, set):
        return list(obj)  # sets aren't JSON serializable, convert to list
    else:
        return obj