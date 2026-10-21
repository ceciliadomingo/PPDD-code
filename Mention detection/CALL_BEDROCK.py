
from time import time

# Function to call Bedrock
def mention_detection_with_aws(input_transcript, few_shot_examples, model_id,system_prompt_content, temperature, top_p, max_tokens):
    start_time = time()  # Start the timer for inference time measurement
    # Create a Bedrock Runtime client in the specified AWS Region.
    client = boto3.client("bedrock-runtime", region_name="eu-west-2")

    # Define the system prompt for the model.
    system_prompt = system_prompt_content
    for few_shot_example in few_shot_examples:
        system_prompt += f"\nEXAMPLE: {few_shot_example[2]} --> {few_shot_example[3]}"
    
    # Add a preface for the user input.
    prompt = "TEXT TO PARSE: " + input_transcript

    # Embed the prompt in Llama 3's instruction format.
    formatted_prompt = f"""
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    {system_prompt}
    <|eot_id|>
    <|start_header_id|>user<|end_header_id|>
    {prompt}
    <|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    """

    
    # Format the request payload using the model's native structure.
    native_request = {
        "prompt": formatted_prompt,
        "max_gen_len": max_tokens,
        "temperature": temperature,
        "top_p": top_p
    }

    # Convert the native request to JSON.
    request = json.dumps(native_request)

    try:
        # Invoke the model with the request.
        response = client.invoke_model(modelId=model_id, body=request)

    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)

    # Decode the response body.
    model_response = json.loads(response["body"].read())

    # Extract the token information from the response.
    headers = response['ResponseMetadata']['HTTPHeaders']
    input_tokens = int(headers.get('x-amzn-bedrock-input-token-count', 0))
    output_tokens = int(headers.get('x-amzn-bedrock-output-token-count', 0))

    # Extract and print the response text.
    response_text = model_response["generation"]
    end_time = time()  # End the timer
    turn_inference_time = end_time - start_time  # Calculate inference time
    return response_text, turn_inference_time, input_tokens, output_tokens


