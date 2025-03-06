import os
import json

from typing import Optional, List
from pydantic import BaseModel
from openai import OpenAI
from utility.utility import MODEL, LLM_RETRY, LLM_RESULT_DIR, SEQUENCE_REPEAT

TESTCASE_OUTPUT_DIR = "testcase_results"

class Message(BaseModel):
    message: str
    is_binary: bool

class Sequence(BaseModel):
    sequenceId: str
    messages: List[Message]
    explanation: str

class TestCase(BaseModel):
    protocol: str
    sequences: List[Sequence]

MESSAGE_PROMPT = """\
You are a network protocol expert with deep understanding of [PROTOCOL]. Your task is to generate client-to-server message sequences for the [PROTOCOL] protocol based on the following inputs:

1. **Type Sequence:**  
[SEQUENCE]

2. **Type Structure:**  
[STRUCTURE]

3. **Number of Message Sequences to Generate:**  
[NUMBER]

Please adhere to the following instructions:

1. **Generate Messages for the Sequence:**
   - Generate messages according to the order specified in type sequence.
   - Create [NUMBER] message sequences following the order specified in type sequence.
   - If additional messages are needed, generate them according to the protocol specification.
   - For binary-based protocols, represent the message as a sequence of bytes in hex format seperated in spaces (e.g., "1a 0b 34 00").
   - For text-based protocols, generate the message in plain ASCII text seperated in spaces, newlines, or CRLF according to the protocol specification if necessary.
   - For each message in a sequence, map the message type to its corresponding structure from type structure and generate realistic, concrete values for each defined field.
   - For each message, if is_binary is true, all messages MUST be written in a hex format seperated in spaces.
   - **Example:**  
     For SMTP, an acceptable output would be:  
     ```json
     {
        "protocol": "SMTP",
        "sequences": [
            {
                "sequenceId": "1",
                "messages": [
                    {"message": "HELO example.com", "is_binary": False},
                    {"message": "MAIL FROM:<sender@example.com>", "is_binary": False},
                    {"message": "RCPT TO:<recipient@example.com>", "is_binary": False},
                    {"message": "DATA", "is_binary": False},
                    {"message": "From: Sender <sender@example.com>\nTo: Recipient <recipient@example.com>\nSubject: Test Email\n\nThis is a test email body.", "is_binary": False},
                    {"message": "QUIT", "is_binary": False}
                ],
                "explanation": "Explanation of the sequence generation process"
            }
        ]
     }
     ```
     For SSH, an acceptable output would be:
     ```json
     {
        "protocol": "SSH",
        "sequences": [
            {
                "sequenceId": "1",
                "messages": [
                    {"message": "53 53 2d 48 2e 32 2d 30 70 4f 6e 65 53 53 5f 48 2e 37 0d 35 00 0a", "is_binary": True},
                    {"message": "00 00 9c 05 14 09 00 00 00 00 00 00 00 00 00 30 01 75 63 76 72 32 65 35 35 39 31 73 2d 61 68 35 32 2c 36 6c 7a 62 69 00 00 1a 00 6f 6e 65 6e 7a 2c 69 6c 40 62 70 6f 6e 65 73 73 2e 68 6f 63 2c 6d 6c 7a 62 69 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 2c 00 1e 06 00 00 20 00 e5 2f a3 7d cd 47 43 62 28 15 ac da bb 5f 07 29 ff 30 84 f6 c4 af c2 cf 90 ed 5f 99 cb 58 74 3b 00 00 00 00 00 00 00 00 0c 00 00 0a", "is_binary": True},
                    {"message": "00 15 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 06 18 00 05 00 00 73 0c 68 73 75 2d 65 73 61 72 74 75 00 68 00 00 00 00 b9 00 1a ac 9c e0 c1 fa 00 d5 00 00 0a 30", "is_binary": True},
                    {"message": "00 32 00 00 75 06 75 62 74 6e 00 75 00 00 73 0e 68 73 63 2d 6e 6f 65 6e 74 63 6f 69 00 6e 00 00 6e 04 6e 6f 00 65 00 00 00 00 00 00 f3 00 35 ee e3 b0 27 3a 00 5d 00 00 0a 48", "is_binary": True}
                ],
                "explanation": "Explanation of the sequence generation process"
            }
        ]
     }
     ```

2. **Ensure Maximum Coverage:**
   - Design sequences to maximize coverage by including variations (e.g., repeated message types, edge-case values, error-triggering values) that exercise different protocol states and transitions.
   - Include variations that account for both normal and exceptional conditions in the protocol.

3. **Authoritative and Accurate:**
   - Base the actual values strictly on the provided type structure.
   - Use official documentation and RFC details from type structure to ensure correctness.
   - Avoid subjective assumptions; rely solely on the provided inputs.

4. **Step-by-Step Reasoning:**
   - In the "explanation" field, include a clear, step-by-step explanation of how the sequences were generated.
   - Describe the process of mapping each message type in sequence to its corresponding structure in type structure and how actual values were determined.
   - Note any differences in handling text-based versus binary-based protocols.

5. **Final Output Format:**
   - The final output must be a JSON object with the following structure:
     ```json
     {
       "protocol": "[PROTOCOL]",
       "sequences": [
         {
           "sequenceId": "A unique identifier for the sequence",
           "message_sequence": "Total messages in the sequence",
           "explanation": "A step-by-step explanation of how the sequences were generated and the rationale behind the actual values selected.",
           "is_binary": "True if the protocol is binary-based, False otherwise"
         }
         // ... additional sequence objects, up to [NUMBER] sequences
       ]
     }
     ```

Please generate multiple valid messages for [PROTOCOL] based on the above requirements and constraints.
"""


def using_llm(prompt: str) -> TestCase:
    client = OpenAI()
    try:
        completion = client.beta.chat.completions.parse(
            model=MODEL,
            temperature=0.7,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            response_format=TestCase,
            timeout=30
        )
        response = completion.choices[0].message.parsed

        return response
    except Exception as e:
        print(f"Error processing protocol: {e}")
        return None

def get_test_case(protocol: str, type_sequence: List[str], specialized_structure: dict) -> None:
    sequence = ""
    structure = ""
    for i, type in enumerate(type_sequence):
        sequence += f"{i+1}. {type}\n"
        structure += f"""\
{type}\n\
- Code: {specialized_structure[type]['code']}\n\
- Description: {specialized_structure[type]['type_description']}\n\
- Fields: {specialized_structure[type]['fields']}\n\n
"""
    sequence = sequence.strip()
    structure = structure.strip()

    prompt = MESSAGE_PROMPT.replace("[PROTOCOL]", protocol)\
                           .replace("[SEQUENCE]", sequence)\
                           .replace("[STRUCTURE]", structure)\
                           .replace("[NUMBER]", str(SEQUENCE_REPEAT))

    for _ in range(LLM_RETRY):
        response = using_llm(prompt)
        if response is not None:
            break

    if response is None:
        raise Exception(f"Failed to generate message for {specialized_structure['message_type']} in {protocol}")

    return response.model_dump()

def get_test_cases(protocol: str, message_sequences: dict, specialized_structures: dict) -> None:
    test_cases = {}
    for sequence in message_sequences["sequences"]:
        try:
            print(f"Processing message sequence: {sequence['sequenceId']}")
            test_cases[sequence["sequenceId"]] = get_test_case(protocol, sequence["type_sequence"], specialized_structures)
        except Exception as e:
            print(f"Error processing message sequence {sequence['sequenceId']} in {protocol}: {e}")
    
    # Save the results to a JSON file
    os.makedirs(TESTCASE_OUTPUT_DIR, exist_ok=True)
    file_path = os.path.join(TESTCASE_OUTPUT_DIR, f"{protocol.lower()}_testcases.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(test_cases, f, indent=4, ensure_ascii=False)    
    print(f"Saved results for {protocol} to {file_path}")

    os.makedirs(LLM_RESULT_DIR, exist_ok=True)
    file_path = os.path.join(LLM_RESULT_DIR, f"4_{protocol.lower()}_testcases.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(test_cases, f, indent=4, ensure_ascii=False)   

    return test_cases
