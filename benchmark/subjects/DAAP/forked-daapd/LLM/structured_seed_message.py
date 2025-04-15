import os
import json

from typing import Optional, List
from pydantic import BaseModel
from openai import OpenAI
from utility.utility import MODEL, LLM_RETRY, LLM_RESULT_DIR, SEQUENCE_REPEAT

STRUCTURED_SEED_MESSAGE_OUTPUT_DIR = "structured_seed_message_results"

class Message(BaseModel):
    """
    Represents a single parsed message chunk.
    """
    message: str

class ParsedMessages(BaseModel):
    """
    A container for multiple parsed messages.
    """
    message_sequences: List[Message]

MESSAGE_PROMPT = """\
You are a highly capable [PROTOCOL] protocol analysis and text parsing assistant.

The seed messages you will parse have been loaded from files via the 'load_seed_messages' function.
Within each seed message, printable ASCII characters remain as-is, while non-ASCII bytes have been
converted into their hex notation (e.g., 0x00, 0x1A, 0xFF, etc.).

Below is the resulting seed message sequence, potentially including both ASCII data and these hex-coded
non-ASCII bytes. Your task is to split this sequence into individual message chunks according to the
[PROTOCOL] rules and guidelines.

Seed Message Sequence:
[SEED_MESSAGE]

In your response, you must return a ParsedMessages object that follows the schema below:

{
  "message_sequences": [
    {
      "message": <string>
    },
    ...
  ]
}

**Parsing Requirements**:
1. **Index**: Although not directly stored in the final schema, be mindful that each chunk should
   conceptually be tracked starting from 0.
2. **Content**: Include the exact substring of the seed message that corresponds to each parsed chunk,
   preserving any 0xHH hex notation for non-ASCII characters.
3. **is_binary**: If a chunk contains or represents non-ASCII data (or mixed ASCII/non-ASCII),
   set this field to true. Otherwise, set it to false.
4. **Protocol Rules**: Apply the rules described in [PROTOCOL] to determine how to segment the seed messages.
   For example, if the protocol specifies special delimiters, length fields, or headers, use them 
   to find the boundaries of each message chunk.
5. **Output Format**: Return only the JSON object in the exact schema (no additional commentary or keys).

If the [PROTOCOL] indicates special delimiters, length fields, headers, or other relevant markers,
use that information to identify message boundaries in the seed message sequence.
"""


def using_llm(prompt: str) -> ParsedMessages:
    client = OpenAI()
    try:
        completion = client.beta.chat.completions.parse(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            response_format=ParsedMessages,
            timeout=60
        )   
        response = completion.choices[0].message.parsed

        return response
    except Exception as e:
        print(f"Error processing protocol: {e}")
        return None

def get_structured_seed_message(protocol: str, seed_message: str) -> None:
    prompt = MESSAGE_PROMPT.replace("[PROTOCOL]", protocol)\
                           .replace("[SEED_MESSAGE]", seed_message)
    
    for _ in range(LLM_RETRY):
        response = using_llm(prompt)
        if response is not None:
            break

    if response is None:
        raise Exception(f"Failed to generate message for {protocol}")

    return response.model_dump()