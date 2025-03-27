import os
import json

from typing import Optional, List
from pydantic import BaseModel
from openai import OpenAI
from utility.utility import MODEL, LLM_RETRY, LLM_RESULT_DIR

DICTIONARY_OUTPUT_DIR = "dictionary_results"

class Dictionary(BaseModel):
    name: str
    data: str

class FuzzingDictionary(BaseModel):
    fuzzing_dictionary: List[Dictionary]

DICTIONARY_PROMPT_WITH_BASE_DICTIONARY = """\
You are a network protocol expert with deep understanding of [PROTOCOL] and advanced fuzzing techniques.
Your task is to generate a fuzzing dictionary for the [PROTOCOL] protocol by enhancing the existing dictionary data provided as [BASE_DICTIONARY].
Additionally, you have information about the message types used to compose protocol sequences, provided as [TYPES].

Base Dictionary:
```
[BASE_DICTIONARY]
```

Message Types:
```
[TYPES]
```

Instructions:

1. **Leverage the Base Dictionary and Message Types:**
   - Start with the existing dictionary data with base dictionary and build upon it.
   - Review the provided list of message types used in constructing protocol message sequences.
   - Identify any coverage gaps in base dictionary related to specific message types and generate new fuzzing payloads targeting those areas (e.g., headers, payloads, status codes specific to each type).

2. **Generate Fuzzing Dictionary Entries:**
   - For each new entry, assign a unique and descriptive "name" indicating the test case and targeted message type (e.g., "Type-A Header Overflow", "Type-B Invalid Format Injection").
   - The "data" field should include the fuzzing input string or byte sequence crafted to trigger vulnerabilities in the context of the specified message type.
   - Ensure that the new entries complement the existing dictionary data and collectively maximize vulnerability coverage across all [TYPES].

3. **Final Output Requirements:**
   - The final output must be valid JSON strictly following the structure below.
   - Include the protocol name under the key "protocol" and the key "fuzzing_dictionary" containing a list of Dictionary objects.
   - Do not include any extraneous fields or text.

Final Output Structure:
```json
{
  "protocol": "[PROTOCOL]",
  "fuzzing_dictionary": [
    {
      "name": "A unique identifier or descriptive name for the fuzzing entry",
      "data": "The fuzzing input string or byte sequence"
    }
    // ... additional fuzzing entries
  ]
}

Please generate the final fuzzing dictionary entries strictly following the above instructions.
"""

DICTIONARY_PROMPT_WITHOUT_BASE_DICTIONARY = """\
You are a network protocol expert with deep understanding of [PROTOCOL] and advanced fuzzing techniques.
Your task is to generate a complete fuzzing dictionary for the [PROTOCOL] protocol without any pre-existing dictionary data.
You are also provided with a list of message types used to compose protocol message sequences.

Message Types:
```
[TYPES]
```

Instructions:
1. **Generate Fuzzing Dictionary Entries from Scratch:**
   - Create multiple fuzzing payloads designed to target different parts of the [PROTOCOL] protocol (e.g., headers, payloads, status codes, etc.).
   - Utilize the provided messagetype list to understand the various message types used in protocol sequences.
   - For each entry, assign a unique and descriptive "name" that includes reference to the relevant message type (e.g., "Type-A Buffer Overflow", "Type-C Malformed Data Injection").
   - The "data" field should include the fuzzing input string or byte sequence specifically crafted for the corresponding message type.

2. **Coverage Considerations:**
   - Ensure that the set of generated payloads covers a wide range of potential vulnerabilities by targeting the diverse message types in the message type list.
   - Include variations in payloads using boundary values, special characters, and malformed structures to enhance test coverage across different protocol sections.

3. **Final Output Requirements:**
   - The final output must be valid JSON strictly following the structure below.
   - Include the protocol name under the key "protocol" and the key "fuzzing_dictionary" containing a list of Dictionary objects.
   - Do not include any extraneous fields or text.
   - For binary-based data, represent each message as a sequence of bytes in hex format separated by spaces (e.g., "0x1a 0x0b 0x34 0x00").
   - For text-based data, generate the message in plain ASCII text using spaces, newlines, or CRLF as needed.


Final Output Structure: 
```json
{
  "protocol": "[PROTOCOL]",
  "fuzzing_dictionary": [
    {
      "name": "A unique identifier or descriptive name for the fuzzing entry",
      "data": "The fuzzing input string or byte sequence"
    }
    // ... additional fuzzing entries
  ]
}
```

Please generate the final fuzzing dictionary entries strictly following the above instructions.
"""

def using_llm(prompt: str) -> FuzzingDictionary:
    client = OpenAI()
    try:
        completion = client.beta.chat.completions.parse(
            model=MODEL,
            # temperature=0.1,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            response_format=FuzzingDictionary,
            timeout=90
        )
        response = completion.choices[0].message.parsed
        return response
    except Exception as e:
        print(f"Error processing protocol: {e}")
        return None

def get_dictionary(protocol: str, dictionary_path: str=None, message_types: dict=None) -> dict:
    dictionary = ""
    prompt = ""
    types_list = [type["name"] for type in message_types["client_to_server_messages"]]
    types = ""
    for type in types_list:
        types += f"- {type}\n"
    types = types.strip()

    if dictionary_path is not None:
        with open(dictionary_path, "r", encoding="utf-8") as f:
            dictionary = f.read()
            prompt = DICTIONARY_PROMPT_WITH_BASE_DICTIONARY.replace("[PROTOCOL]", protocol).replace("[BASE_DICTIONARY]", dictionary).replace("[TYPES]", types)
    else:
        dictionary = ""
        prompt = DICTIONARY_PROMPT_WITHOUT_BASE_DICTIONARY.replace("[PROTOCOL]", protocol).replace("[TYPES]", types)

    for _ in range(LLM_RETRY):
        response = using_llm(prompt)
        if response is not None:
            break

    if response is None:
        raise Exception(f"Failed to generate dictionary for {protocol}")

    return response.model_dump()

def get_fuzzing_dictionary(protocol: str, dictionary_path: str=None, message_types: dict=None) -> dict:
    try:
        print(f"Processing dictionary: {dictionary_path}")
        fuzzing_dictionary = get_dictionary(protocol, dictionary_path, message_types)
    except Exception as e:
        print(f"Error processing dictionary {dictionary_path} in {protocol}: {e}")
    
    # Save the results to a JSON file
    # os.makedirs(DICTIONARY_OUTPUT_DIR, exist_ok=True)
    # with open(dictionary_path, "w", encoding="utf-8") as f:
    #     json.dump(fuzzing_dictionary, f, indent=4, ensure_ascii=False)    
    # print(f"Saved results for {protocol} to {dictionary_path}")

    os.makedirs(LLM_RESULT_DIR, exist_ok=True)
    file_path = os.path.join(LLM_RESULT_DIR, f"4_{protocol.lower()}_dictionaries.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(fuzzing_dictionary, f, indent=4, ensure_ascii=False)   

    return fuzzing_dictionary
