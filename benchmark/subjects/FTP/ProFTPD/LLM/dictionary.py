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
Your task is to generate a fuzzing dictionary for the [PROTOCOL] protocol by enhancing the existing dictionary data provided as Base Dictionary and by analysing real traffic examples supplied as Seed Input.  
You also have information about the message types used to compose protocol sequences, provided as Message Types.

Seed Input:  
```
[SEED_INPUT]
```

Base Dictionary:  
```
[BASE_DICTIONARY]
```

Message Types:  
```
[TYPES]
```

Follow these strict guidelines:

1. **Leverage Seed Input, Base Dictionary, and Message Types**  
   - Start by parsing the **Seed Input** to identify fixed tokens (magic values, delimiters) and mutable fields (length, payload, flags, IDs).  
   - Compare the **Seed Input** against the existing **Base Dictionary** and the listed **Message Types** to spot coverage gaps.  
   - To explore wider state coverage, you must use valid fields from the seed input (username, password, address, etc.) to generate fuzzing dictionary entries.
   - Generate new fuzzing dictionary entries that target those gaps while preserving enough structural validity so the messages are not immediately rejected by a **[PROTOCOL]** parser.

2. **Generate Fuzzing Dictionary Entries**  
   - For each new entry, assign a unique and descriptive `"name"` that indicates the test case and its target (e.g., `"Type-A Length Underflow"`, `"Type-B Header Repetition"`).  
   - The `"data"` field must contain the specially crafted fuzzing input character sequence designed to trigger vulnerabilities in the context of the specified message type.  
   - Modify only the necessary parts of each payload; keep the overall frame conformant to [PROTOCOL].

3. **Output-Size Limitation & Binary-Data Handling**  
   - **Text-based protocols:** every fuzzing payload **MUST** be **≤ 32 characters**.  
   - **Binary-based protocols:** every fuzzing payload **MUST** be **≤ 16 characters**.  
   - When representing binary data in `"0xHH"` form, treat each `0xHH` token as **one character** for these limits.

4. **Final Output Requirements**  
   - Output valid JSON with exactly the structure below—no extra keys or text.  
   - Under `"protocol"` place the protocol name; under `"fuzzing_dictionary"` list the dictionary objects.  
   - For text data, use plain ASCII (spaces, newlines, or CRLF as needed).  
   - For binary data, list bytes in hex notation separated by spaces (e.g., `"0x1a 0x0b 0x34 0x00"`). Each `0xHH` counts as one character.

Final output structure example:
```json
{
  "protocol": "[PROTOCOL]",
  "fuzzing_dictionary": [
    {
      "name": "Descriptive fuzzing entry name",
      "data": "Fuzzing input string or 0xHH formatted binary sequence (e.g., 0x1a 0x0b 0x34 0x00)"
    }
    // ... additional fuzzing entries
  ]
}
```

Please generate the final fuzzing dictionary entries strictly following the above instructions.
"""

DICTIONARY_PROMPT_WITHOUT_BASE_DICTIONARY = """\
You are a network protocol expert with deep understanding of [PROTOCOL] and advanced fuzzing techniques.  
Your task is to create a comprehensive fuzzing dictionary for [PROTOCOL] by analysing real traffic examples supplied as Seed Input and by referencing the set of message types given in Message Types.

Seed Input:  
```
[SEED_INPUT]
```

Message Types:  
```
[TYPES]
```

Follow these strict guidelines:

1. **Leverage Seed Input and Message Types**  
   - Parse the **Seed Input** to identify fixed tokens (magic values, delimiters) and mutable fields (length, payload, flags, IDs).  
   - Cross-check against the listed **Message Types** to uncover coverage gaps.  
   - To explore wider state coverage, you must use valid fields from the seed input (username, password, address, etc.) to generate fuzzing dictionary entries.
   - Generate fuzzing payloads that exercise those gaps while keeping messages structurally valid so they are not instantly rejected by a **[PROTOCOL]** parser.

2. **Generate Fuzzing Dictionary Entries**  
   - For each entry, assign a clear `"name"` indicating the test idea and targeted element (e.g., `"Type-A Length Underflow"`, `"Type-B Header Repetition"`).  
   - Put the crafted fuzzing character sequence in the `"data"` field.  
   - Alter only the necessary parts of each payload; maintain overall [PROTOCOL] conformance.

3. **Output-Size Limitation & Binary-Data Handling**  
   - **Text-based protocols:** every payload **MUST** be **≤ 32 characters**.  
   - **Binary-based protocols:** every payload **MUST** be **≤ 16 characters**.  
   - When using `"0xHH"` notation, count each `0xHH` token as **one character** toward the limits.

4. **Final Output Requirements**  
   - Output valid JSON exactly in the structure below—no extra keys or text.  
   - For text data, use plain ASCII (spaces, newlines, or CRLF as needed).  
   - For binary data, list bytes in hex notation separated by spaces (e.g., `"0x1a 0x0b 0x34 0x00"`). Each `0xHH` counts as one character.

Final output structure example:
```json
{
  "protocol": "[PROTOCOL]",
  "fuzzing_dictionary": [
    {
      "name": "Descriptive fuzzing entry name",
      "data": "Fuzzing input string or 0xHH formatted binary sequence (e.g., 0x1a 0x0b 0x34 0x00)"
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

        index = 0
        os.makedirs(os.path.join(LLM_RESULT_DIR, "7_dictionaries"), exist_ok=True)
        while os.path.exists(os.path.join(LLM_RESULT_DIR, "7_dictionaries", f"response_{index}.json")):
            index += 1
        protocol_file = os.path.join(LLM_RESULT_DIR, "7_dictionaries", f"response_{index}.json")
        with open(protocol_file, "w", encoding="utf-8") as f:
            json.dump(completion.model_dump(), f, indent=4, ensure_ascii=False)
        return response
    except Exception as e:
        print(f"Error processing protocol: {e}")
        return None

def get_dictionary(protocol: str, dictionary_path: str=None, message_types: dict=None, seed_input: str=None) -> dict:
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

def get_fuzzing_dictionary(protocol: str, dictionary_path: str=None, message_types: dict=None, seed_input: str=None) -> dict:
    try:
        print(f"Processing dictionary: {dictionary_path}")
        fuzzing_dictionary = get_dictionary(protocol, dictionary_path, message_types, seed_input)
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
