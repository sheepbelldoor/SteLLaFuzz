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
    sequences: Optional[List[Sequence]] = None
    explanation: Optional[str] = None



MESSAGE_PROMPT = """\
You are a network protocol expert with a deep understanding of [PROTOCOL].
Your task is to generate a series of message sequences for client-to-server communications in the [PROTOCOL] protocol.
The primary objective is to maximize code coverage by exercising as many lines, states, and branches in the protocol implementation as possible.

You are provided with a complete list of client-to-server message types:
[TYPES]

Please adhere to the following instructions:

1. **Generate Message Sequences:**
   - Produce multiple message sequences that collectively use **all** client-to-server message types from the provided list at least once.
   - Vary the order of messages and include:
     - **Conditional transitions** (e.g., different messages used when certain states are reached).
     - **Error-handling cases** (e.g., invalid arguments, out-of-order messages) to explore the protocol’s robustness.
     - **Loop constructs** where beneficial (e.g., repeating a set of messages a certain number of times) to ensure deeper exploration of repeated state transitions.
   - Sequences should explore edge cases (boundary values, unusual but valid parameters) and alternative branches in the protocol's state machine to maximize line, state, and branch coverage.
   - A single sequence can repeat any message type multiple times if it helps uncover additional protocol behaviors or paths.

2. **Include Detailed Message Information:**
   - In the output, each sequence is an object with:
     - A unique "sequenceId".
     - A "type_sequence" array, which is an ordered list of the client-to-server message types used in that particular sequence.
   - Each message type in the sequence must match exactly one from the provided [TYPES].
   - Be sure to consider adding parameter details within your explanation if they help illustrate how the loop or conditional transitions are triggered.

3. **Provide a Coverage Rationale:**
   - In the "explanation" field, describe your step-by-step reasoning for the sequence construction. Specifically detail:
     - Why certain messages were repeated (loop).
     - How error cases or conditional branches were introduced.
     - How each message sequence leads to different protocol states or paths.

4. **Final Output Requirements:**
   - **Do not** include any additional text or commentary outside the final JSON.
   - The output must be **valid JSON** that strictly follows the structure below.

5. **Final Output Structure:**
   - The final JSON object must conform to the following layout:
     ```json
     {
       "protocol": "[PROTOCOL]",
       "sequences": [
         {
           "sequenceId": "A unique identifier for the sequence",
           "type_sequence": [
             "Type of message 1",
             "Type of message 2",
             "Type of message 3"
             // ...
           ]
         }
         // Additional sequence objects if necessary
       ],
       "explanation": "A concise explanation of how these sequences were constructed to maximize coverage, including the rationale behind loops, ordering, and any error cases."
     }
     ```

Please produce the final JSON output accordingly, strictly following the above structure.
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

def get_loop_message_sequences(protocol: str, message_types: dict) -> dict:
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
        raise Exception(f"Failed to generate loop message sequence for {protocol}")

    # Save the results to a JSON file
    os.makedirs(MESSAGE_SEQUENCE_OUTPUT_DIR, exist_ok=True)
    file_path = os.path.join(MESSAGE_SEQUENCE_OUTPUT_DIR, f"{protocol.lower()}_loop_message_sequences.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(response.model_dump(), f, indent=4, ensure_ascii=False)    
    print(f"Saved results for {protocol} to {file_path}")

    # Save the prompt and response to a text file
    os.makedirs(LLM_RESULT_DIR, exist_ok=True)
    protocol_file = os.path.join(LLM_RESULT_DIR, f"3_{protocol.lower()}_loop_message_sequences.json")
    with open(protocol_file, "w", encoding="utf-8") as f:
        json.dump(response.model_dump(), f, indent=4, ensure_ascii=False)

    return response.model_dump()
# … existing code …
