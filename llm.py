import json
import aiohttp
import asyncio
import logging
from tenacity import retry, stop_after_attempt, wait_fixed

# Load configuration
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# LLM endpoint and model
llm_endpoint = config['llm_endpoint']
llm_model = config['llm_model']
max_tokens = config['max_tokens']
max_retries = config['max_retries']
retry_delay_seconds = config['retry_delay_seconds']

# Function to perform LLM analysis or response generation with retries
@retry(stop=stop_after_attempt(max_retries), wait=wait_fixed(retry_delay_seconds))
async def llm_request(prompt, output_schema, max_tokens=max_tokens):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            llm_endpoint,
            json={
                "model": llm_model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": ""}
                ],
                "max_tokens": max_tokens
            },
            headers={
                "Authorization": f"Bearer {config['github_token']}"
            }
        ) as response:
            if response.status == 200:
                result = await response.json()
                content = result['choices'][0]['message']['content'].strip()
                try:
                    response_data = json.loads(content)
                    if validate_output(response_data, output_schema):
                        return response_data
                    else:
                        logging.error(f"LLM response does not conform to the output schema: {content}")
                        raise ValueError("LLM response does not conform to the output schema")
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse LLM response: {e}")
                    raise ValueError("Failed to parse LLM response")
            else:
                logging.error(f"Failed to process LLM request: {response.status} {await response.text()}")
                raise ValueError("Failed to process LLM request")

# Function to validate LLM output against the schema
def validate_output(output, schema):
    try:
        schema_dict = json.loads(schema)
        for key, value in schema_dict.items():
            if key not in output or not isinstance(output[key], str) or output[key] not in value.split('|'):
                return False
        return True
    except json.JSONDecodeError:
        return False
