import os
import json
import random
from typing import List
from pprint import pprint
import re

MODEL = "gpt-4o-mini"
LLM_RESULT_DIR = "llm_outputs"
TEST_MESSAGE_DIR = os.path.join(LLM_RESULT_DIR, "messages")
SEQUENCE_REPEAT = 1
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

def convert_message_to_binary(message: str) -> bytes:
    """
    메시지를 처리하는 함수:
    1. 메시지를 공백으로 나누고, 각 요소가 0x로 시작하는지 확인
    2. 0x로 시작하는 요소는 바이트 데이터로 변환하고 is_binary=True로 표시
       0x로 시작하지 않는 요소는 바이트로 변환하되 is_binary=False로 표시
    3. 리스트를 순회하며 bytearray에 데이터를 추가
       - 현재 데이터와 다음 데이터가 모두 is_binary=False이면 사이에 공백 추가
       - 그 외에는 공백 없이 이어붙임
    4. 생성된 bytearray 반환
    
    Args:
        message (str): 처리할 메시지
        
    Returns:
        bytes: 변환된 바이트 데이터
    """
    if not message:
        return b''
    
    # 1. 메시지를 공백으로 나누고 각 요소 처리
    parts = message.split(' ')
    processed_parts = []
    
    # 2. 각 요소를 처리하여 (data, is_binary) 형태로 저장
    for part in parts:
        if part.startswith('0x'):
            try:
                # 0x 접두사 제거 후 16진수를 바이트로 변환
                binary_value = bytes([int(part[2:], 16)])
                processed_parts.append((binary_value, True))
            except ValueError:
                # 변환 실패 시 원래 문자열을 바이트로 변환
                processed_parts.append((part.encode(), False))
        else:
            # 0x로 시작하지 않는 요소는 그대로 바이트로 변환
            processed_parts.append((part.encode(), False))
    
    # 3. 처리된 부분들을 순회하며 bytearray에 추가
    result = bytearray()
    for i in range(len(processed_parts)):
        current_data, current_is_binary = processed_parts[i]
        result.extend(current_data)
        
        # 마지막 요소가 아니고, 현재와 다음 요소가 모두 바이너리가 아닌 경우 공백 추가
        if i < len(processed_parts) - 1:
            next_is_binary = processed_parts[i+1][1]
            if not current_is_binary and not next_is_binary:
                result.extend(b' ')
    
    # 4. 생성된 bytearray 반환
    return bytes(result)

def save_test_cases(test_cases: dict, output_dir: str) -> None:
    """Save test cases to files.
    
    Args:
        test_cases (dict): Dictionary containing test messages (bytearray)
        output_dir (str): Directory to save the files
    """
    concatnated_messages = bytearray()
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    idx = 1
    for testcase in test_cases.values():
        for sequence in testcase["sequences"]:
            try:
                for message in sequence["messages"]:   
                    concatnated_messages += convert_message_to_binary(message["message"]) + b"\r\n"

                # Find the next available file name
                while True:
                    file_path = os.path.join(output_dir, f"new_{idx}.raw")
                    if not os.path.exists(file_path):
                        break
                    idx += 1
                
                with open(file_path, "wb") as f:
                    f.write(concatnated_messages)
                concatnated_messages = bytearray()
                idx += 1
            except Exception as e:
                print(f"Error: {e}")
            
def load_seed_messages(seed_messages_dir: str) -> List[str]:
    """Load seed messages from files.
    
    Args:
        seed_messages_dir (str): Directory containing seed message files
        
    Returns:
        list[str]: List of seed messages with non-ASCII characters converted to hex representation
    """
    seed_messages = []
    for file in os.listdir(seed_messages_dir):
        file_path = os.path.join(seed_messages_dir, file)
        # Read file as binary
        with open(file_path, "rb") as f:
            binary_content = f.read()
        
        # Convert to readable format (ASCII where possible, hex otherwise)
        readable_content = ""
        for byte in binary_content:
            # If printable ASCII (32-126 range, plus tab, newline, carriage return)
            if byte in (9, 10, 13) or (32 <= byte <= 126):
                readable_content += chr(byte)
            else:
                # Convert to hex representation
               readable_content += f" 0x{byte:02x} "
        
        seed_messages.append(readable_content)
    return seed_messages
