import os
import json

from typing import Optional, List
from pydantic import BaseModel
from openai import OpenAI
from utility.utility import MODEL, LLM_RETRY, LLM_RESULT_DIR

MESSAGE_SEQUENCE_OUTPUT_DIR = "message_sequence_results"

class Message(BaseModel):
    """
    Represents a single client-to-server message in a sequence.
    Attributes:
        type (str): The client-to-server message type. Must match one from the provided list.
    """
    type: str

class Coverage(BaseModel):
    """
    Describes the coverage achieved by a message sequence.
    Attributes:
        line (str): A description of the line coverage achieved.
        state (str): A description of the state coverage achieved.
        branch (str): A description of the branch coverage achieved.
    """
    line: str
    state: str
    branch: str

class Sequence(BaseModel):
    """
    Represents a single message sequence.
    Attributes:
        sequenceId (str): A unique identifier for the sequence.
        messages (List[Message]): A list of messages in the sequence. 
                                  Note: The same message type may be used repeatedly.
        coverage (Coverage): Coverage details for this sequence.
    """
    sequenceId: str
    type_sequence: List[str]
    coverage: Coverage

class ProtocolSequences(BaseModel):
    """
    Represents the complete set of client-to-server message sequences for a given protocol.
    Attributes:
        protocol (str): The protocol name (e.g., [PROTOCOL]).
        sequences (List[Sequence]): A list of message sequences.
        explanation (str): An explanation of how these sequences were constructed to maximize
                           line, state, and branch coverage.
    """
    protocol: str
    sequences: List[Sequence]
    explanation: str



MESSAGE_PROMPT = """\
You are a network protocol expert with deep understanding of [PROTOCOL].
Your task is to generate a series of message sequences for client-to-server communications in the [PROTOCOL] protocol.
The objective is to maximize code coverage by exercising as many lines, states, and branches in the protocol implementation as possible.

You are provided with a complete list of client-to-server message types:
[TYPES]

Please adhere to the following instructions:

1. **Generate Message Sequences:**
   - Create multiple message sequences that include all client-to-server message types from the provided list.
   - Each sequence should vary the order of messages and include conditional transitions or error-handling cases to trigger different execution paths.
   - Design the sequences to explore edge cases and alternative branches in the protocol's state machine to maximize line, state, and branch coverage.
   - Message types may be repeated in a sequence if it helps to achieve greater coverage.
   - The number of sequences should be as many as possible.

2. **Include Detailed Message Information:**
   - For each message in the "messages" array, ensure that the "type" field exactly matches one of the provided client-to-server types.
   - The "details" field should include any specific parameters or variations relevant to that message type to help trigger different states or branches.

3. **Provide a Coverage Rationale:**
   - In the "coverage" field for each sequence, include a descriptive summary of the expected line, state, and branch coverage achieved by that sequence.
   - In the "explanation" field, describe your step-by-step reasoning process for constructing these sequences, including how you considered different protocol states and error paths.

4. **Final Output Requirements:**
   - Do not include any extraneous text; only provide the final JSON output.
   - Ensure the output is valid JSON strictly adhering to the above structure.

5. **Final Output Structure:**
   - The final output must be a JSON object structured as follows:
     ```json
     {
       "protocol": "[PROTOCOL]",
       "sequences": [
         {
           "sequenceId": "A unique identifier for the sequence",
           "type_sequence": [
             "Type of message 1",
             "Type of message 2",
             "Type of message 3",
             // ...
           ],
           "coverage": {
             "line": "Description of line coverage achieved",
             "state": "Description of state coverage achieved",
             "branch": "Description of branch coverage achieved"
           }
         }
         // ... additional sequence objects
       ],
       "explanation": "A brief explanation of how these sequences were constructed to maximize coverage, including the rationale behind the order and selection of messages."
     }
     ```

Please produce the final JSON output accordingly, strictly following the above instructions.
"""

def using_llm(prompt: str) -> ProtocolSequences:
    client = OpenAI()
    try:
        completion = client.beta.chat.completions.parse(
            model=MODEL,
            temperature=0.7,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            response_format=ProtocolSequences,
            timeout=90
        )
        response = completion.choices[0].message.parsed
        return response
    except Exception as e:
        print(f"Error processing protocol: {e}")
        return None

def get_message_sequences(protocol: str, message_types: dict) -> dict:
    types_list = [type["name"] for type in message_types["client_to_server_messages"]]
    types = ""
    for type in types_list:
        types += f"- {type}\n"
    types = types.strip()

    prompt = MESSAGE_PROMPT.replace("[PROTOCOL]", protocol)\
                           .replace("[TYPES]", types)

    for _ in range(LLM_RETRY):
        response = using_llm(prompt)
        if response is not None:
            break

    if response is None:
        raise Exception(f"Failed to generate message sequence for {protocol}")

    # Save the results to a JSON file
    os.makedirs(MESSAGE_SEQUENCE_OUTPUT_DIR, exist_ok=True)
    file_path = os.path.join(MESSAGE_SEQUENCE_OUTPUT_DIR, f"{protocol.lower()}_message_sequences.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(response.model_dump(), f, indent=4, ensure_ascii=False)    
    print(f"Saved results for {protocol} to {file_path}")

    # Save the prompt and response to a text file
    os.makedirs(LLM_RESULT_DIR, exist_ok=True)
    protocol_file = os.path.join(LLM_RESULT_DIR, f"3_{protocol.lower()}_message_sequences.json")
    with open(protocol_file, "w", encoding="utf-8") as f:
        json.dump(response.model_dump(), f, indent=4, ensure_ascii=False)

    return response.model_dump()
# … existing code …
