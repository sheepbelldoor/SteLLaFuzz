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
You are a network protocol expert with deep understanding of [PROTOCOL]. Your task is to generate a series of message sequences for client-to-server communications in the [PROTOCOL] protocol using a Tree-of-Thoughts (ToT) approach.

The objective is to systematically traverse the protocol's state machine so that each defined protocol state is entered or tested at least once (including normal operation states, error states, out-of-order message handling states, and any other states relevant to [PROTOCOL]). To achieve this, you MUST create message sequences that explore all possible transitions between states and any edge cases that may appear in real-world usage.

You are provided with a complete list of client-to-server message types:
[TYPES]

Please adhere to the following instructions:

1. **Generate Message Sequences:**
   - You MUST create multiple message sequences that incorporate **all** client-to-server message types from the provided list at least once across the entire set of sequences.
     - (Note: It is NOT required for every sequence to use every message type. The requirement is that each message type appears at least once somewhere in the overall collection of sequences.)
   - Each sequence MUST vary the order of messages and include conditional transitions, error-handling cases, or other patterns (such as loop constructs) that cause the protocol to enter different states.
   - **Repetitions MUST be included**:
     - You MUST repeat a message type or a set of messages if doing so leads to exploring different protocol states, error conditions, or transitions.
     - Repeated or consecutive occurrences of the same message type MUST serve a specific purpose (e.g., transitioning the protocol into a unique state or validating behavior when multiple identical messages arrive in sequence).
       - (Note: Causing an explicit error is NOT a requirement; the primary objective is to discover valid message sequences that traverse as many unique states as possible.)
   - You MUST generate as many **valid** sequences as possible within the protocol's rules.
     - (Note: The overarching goal is to produce valid message call sequences according to the protocol specification.)

2. **Include Detailed Message Information (Optional):**
   - For each message in the "type_sequence" array, you MUST ensure that the "type" field exactly matches one of the provided client-to-server types.
   - If necessary, you MAY add a "details" or similar field (within your JSON structure) to specify parameters or variations for each message that might trigger unique transitions or error states.

3. **Tree-of-Thoughts Reasoning and Candidate Generation:**
   - Internally generate and evaluate multiple candidate message sequences (i.e., branches of thought) that explore different orders, conditional paths, loop constructs, and error-handling scenarios.
   - For each candidate branch, consider how variations in message ordering, repetition, or specific detail parameters trigger distinct protocol states or transitions.
   - Compare these candidate branches internally to ensure that each selected sequence uniquely contributes to traversing additional protocol states or testing edge cases.
   - Do not output the internal intermediate thought processes; only provide the final selected sequences that maximize coverage.

4. **Provide a Coverage Rationale:**
   - In the "explanation" field, you MUST briefly describe how you designed these sequences to traverse and test every reachable state (including error states, alternate branches, and repeated transitions).
   - You MUST explain the logic behind the order, repetition, and any special variations you used.
   - Your explanation MUST also detail the Tree-of-Thoughts process you applied – how multiple candidate branches were generated and evaluated to select the final sequences that achieve broad state coverage.

5. **Final Output Requirements:**
   - You MUST NOT include any extraneous text; only provide the final JSON output.
   - You MUST ensure the output is valid JSON strictly adhering to the structure below. (Invalid JSON or additional text will not be accepted.)

6. **Final Output Structure:**
   The final output MUST be a JSON object structured as follows:
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
       // ... additional sequence objects
     ],
     "explanation": "A brief explanation of how these sequences were constructed to cover all protocol states, including the rationale behind the order, repetition, and selection of messages, as well as the Tree-of-Thoughts process used to generate and evaluate multiple candidate branches."
   }
```

Please generate the final message call sequences strictly following the above instructions.
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

def get_repetited_message_sequences(protocol: str, message_types: dict) -> dict:
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
