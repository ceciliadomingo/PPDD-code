from time import time

# Function to call GPT
def mention_detection_with_gpt(key_path,input_transcript, few_shot_examples, model_id,system_prompt_content, temperature, top_p,max_tokens):
    start_time = time()  # Start the timer for inference time measurement
    # Initialize OpenAI client
    with open(key_path, 'r') as file:
        key = file.read().strip()
    client = OpenAI(api_key=key)

    # Define the system prompt for the model.
    system_prompt = system_prompt_content
    if len(few_shot_examples) != 0:
        for few_shot_example in few_shot_examples:
            system_prompt += f"\nEXAMPLE: {few_shot_example[2]} --> {few_shot_example[3]}"
    
    # Add a preface for the user input.
    prompt = "TEXT TO PARSE: " + input_transcript

    # Embed the prompt in GPT's instruction format and obtain a response
    response = client.chat.completions.create(model=model_id,
        messages=[
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": prompt}
      ], temperature=temperature, top_p=top_p, max_completion_tokens=max_tokens)
    response_text = response.choices[0].message.content
    # Extract token usage
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    total_tokens = response.usage.total_tokens
    end_time = time()  # End the timer
    turn_inference_time = end_time - start_time  # Calculate inference time
    return response_text, turn_inference_time, input_tokens, output_tokens, total_tokens