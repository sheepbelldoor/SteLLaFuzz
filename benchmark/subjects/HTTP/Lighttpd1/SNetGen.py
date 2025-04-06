import os
import json
import argparse

from LLM.basic_protocol_template import get_basic_protocol_template
from LLM.protocol_types import get_protocol_message_types
from LLM.specialized_structures import get_specialized_structures
from LLM.normal_message_sequence import get_message_sequences
from LLM.repetited_message_sequence import get_repetited_message_sequences
from LLM.testcases import get_test_cases
from LLM.structured_seed_message import get_structured_seed_message
from LLM.dictionary import get_fuzzing_dictionary
from utility.utility import save_test_cases, load_seed_messages, save_fuzzing_dictionary

import pprint

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", "-p", type=str, required=True)
    parser.add_argument("--output_dir", "-o", type=str, required=False, default="results")
    parser.add_argument("--seed_messages", "-s", type=str, required=False, default=None, help="Path to the seed messages directory")
    parser.add_argument("--dictionary", "-d", type=str, required=False, default=None, help="Path to the fuzzing dictionary")
    args = parser.parse_args()

    protocol = args.protocol
    output_dir = args.output_dir
    seed_messages_dir = args.seed_messages
    dictionary_path = args.dictionary

    try:
        seed_messages: list[str] = load_seed_messages(seed_messages_dir) if seed_messages_dir else None
        test_cases = {}
        if True:
            if True:
                # 1. Extract message types
                message_types: dict = get_protocol_message_types(protocol)

                # 2. Extract specialized structure
                # message_types = json.load(open(f"protocol_type_results/{protocol}_types.json"))
                specialized_structures: dict = get_specialized_structures(protocol, message_types)

                # 3. Generate message sequences
                # message_types = json.load(open(f"protocol_type_results/{protocol}_types.json"))
                message_sequences: dict = get_message_sequences(protocol, message_types)
                # Loop message sequences can be None
                repetited_message_sequences: dict = get_repetited_message_sequences(protocol, message_types)

            if True:
                # 4. Generate test cases
                # specialized_structures = json.load(open(f"protocol_specialized_structure_results/{protocol}_specialized_structures.json"))
                # message_sequences = json.load(open(f"message_sequence_results/{protocol}_message_sequences.json"))
                # loop_message_sequences = json.load(open(f"message_sequence_results/{protocol}_loop_message_sequences.json"))
                seed_index = 0
                if seed_messages:
                    for seed_message in seed_messages:
                        structured_seed_message = get_structured_seed_message(protocol, seed_message)
                        test_cases[seed_index] = get_test_cases(protocol, message_sequences, specialized_structures, structured_seed_message)
                        seed_index += 1
                        if repetited_message_sequences:
                            test_cases[seed_index] = get_test_cases(protocol, repetited_message_sequences, specialized_structures, structured_seed_message)
                            seed_index += 1
                else:
                    test_cases[0] = get_test_cases(protocol, message_sequences, specialized_structures, None)
                    if repetited_message_sequences:
                        test_cases[1] = get_test_cases(protocol, repetited_message_sequences, specialized_structures, None)

        if True:
            # 5. Save results
            # test_cases[0] = json.load(open(f"testcase_results/{protocol}_testcases.json"))
            for seed_index, test_case in test_cases.items():
                save_test_cases(test_case, output_dir)

        # 6. Generate dictionary
        if False:
            # 6.1. Generate dictionary
            fuzzing_dictionary = get_fuzzing_dictionary(protocol, dictionary_path, message_types)
            # 6.2. Save dictionary
            save_fuzzing_dictionary(fuzzing_dictionary, dictionary_path if dictionary_path else f"{protocol}.dict")
    
    except Exception as e:
        print(f"Error processing protocol {protocol}: {e}")

if __name__ == "__main__":
    main()
