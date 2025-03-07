import os
import json
import random

from pprint import pprint

MODEL = "gpt-4o-mini"
LLM_RESULT_DIR = "llm_outputs"
TEST_MESSAGE_DIR = os.path.join(LLM_RESULT_DIR, "messages")
SEQUENCE_REPEAT = 5
LLM_RETRY = 3

def hex_to_bytearray(hex_string: str) -> str:
    """Convert hex string to binary string.
    
    Args:
        hex_string (str): Hex string in format like "0x12 0x34" or "12 34"
        
    Returns:
        str: bytearray (e.g. "0x12 0x34" -> bytearray([0x12, 0x34]))
    """
    # Remove "0x" prefix and spaces
    hex_string = hex_string.replace("0x", "").replace(" ", "")
    if len(hex_string) % 2 == 1:
        hex_string = "0" + hex_string

    # Add spaces between each two characters
    hex_string = ' '.join(hex_string[i:i+2] for i in range(0, len(hex_string), 2))
    
    return bytearray.fromhex(hex_string)

def check_all_fields_non_binary(message_payload: dict) -> bool:
    """Check if all fields in the message payload are non-binary.
    
    Args:
        message (dict): Message dictionary containing payload fields
        
    Returns:
        bool: True if all fields are non-binary (is_binary=False), False otherwise
    """
    
    for field in message_payload:
        if field.get("is_binary", True):
            return False
            
    return True

def get_message_random(message: dict) -> bytearray:
    # Randomly select a message from the list of generated messages
    selected_message = random.choice(message["generated_message"])
    message = bytearray()

    is_text_based = not selected_message["is_binary"]

    # Process the message string directly
    if is_text_based:
        if not (selected_message['message'].endswith('\r\n') or selected_message['message'].endswith('\n')):
            message.extend(f"{selected_message['message']}\r\n".encode())
        else:
            message.extend(selected_message['message'].encode())
    else:
        # If it were binary, you would handle it differently
        # Assuming you have a way to convert the string to binary if needed
        binary_string = hex_to_bytearray(selected_message["message"])  # Example, adjust as needed
        message.extend(binary_string)
    
    # message.extend(b'\r\n')
    return message

def generate_test_cases(protocol: str, message_types: dict, _message_sequences: dict) -> None:
    message_sequences = {}
    idx = 1
    
    # 메시지 시퀀스 하나당 SEQUENCE_REPEAT 수만큼 메시지 생성
    for _ in range(SEQUENCE_REPEAT):
        for type_sequence in _message_sequences["message_sequences"]:
            message_sequence = bytearray()

            for message_type in type_sequence["message_type"]:
                message = get_message_random(message_types[message_type])
                message_sequence.extend(message)

            message_sequences[idx] = message_sequence
            idx += 1

    return message_sequences

def save_test_cases(test_cases: dict, output_dir: str) -> None:
    """Save test cases to files.
    
    Args:
        test_cases (dict): Dictionary containing test messages (bytearray)
        output_dir (str): Directory to save the files
    """
    concatnated_messages = bytearray()
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    for idx, testcase in enumerate(test_cases.values(), 1):
        for sequence in testcase["sequences"]:
            for message in sequence["messages"]:
                if message["is_binary"]:
                    # have to convert hex to binary
                    concatnated_messages += hex_to_bytearray(message["message"]) + b"\r\n"
                else:
                    concatnated_messages += message["message"].encode() + b"\r\n"

        file_path = os.path.join(output_dir, f"new_{idx}.raw")
        with open(file_path, "wb") as f:
            f.write(concatnated_messages)
        concatnated_messages = bytearray()

def save_messages(messages: dict) -> None:
    """Save individual messages to separate files.
    
    Args:
        messages (dict): Dictionary containing message types and their generated messages
    """
    os.makedirs(TEST_MESSAGE_DIR, exist_ok=True)
    
    for message_type, message_data in messages.items():
        for idx, generated_msg in enumerate(message_data["generated_message"], 1):
            # print(f"Debug: generated_msg = {generated_msg}")  # Debugging line
            
            if isinstance(generated_msg, str):
                print(f"Error: generated_msg is a string, expected a dictionary. Value: {generated_msg}")
                continue  # Skip this iteration if it's a string
            
            message = bytearray()
            
            # Check if the message is text-based
            is_text_based = not generated_msg["is_binary"]  # Use is_binary directly
            
            # Process the message string directly
            if is_text_based:
                if not (generated_msg['message'].endswith('\r\n') or generated_msg['message'].endswith('\n')):
                    message.extend(f"{generated_msg['message']}\r\n".encode())
                else:
                    message.extend(generated_msg['message'].encode())
            else:
                # If it were binary, you would handle it differently
                # Assuming you have a way to convert the string to binary if needed
                binary_string = hex_to_bytearray(generated_msg["message"])  # Example, adjust as needed
                message.extend(binary_string)
            
            # message.extend(b'\r\n')
            
            # Save individual message to file with message type in filename
            file_path = os.path.join(TEST_MESSAGE_DIR, f"{message_type}_{idx}.raw")
            with open(file_path, "wb") as f:
                f.write(message)
