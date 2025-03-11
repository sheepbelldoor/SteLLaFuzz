import os
import json
import argparse

from LLM.basic_protocol_template import get_basic_protocol_template
from LLM.protocol_types import get_protocol_message_types
from LLM.specialized_structures import get_specialized_structures
from LLM.message_sequence import get_message_sequences
from LLM.testcases import get_test_cases
from utility.utility import save_test_cases, load_seed_messages

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", "-p", type=str, required=True)
    parser.add_argument("--output_dir", "-o", type=str, required=False, default="results")
    parser.add_argument("--seed_messages", "-s", type=str, required=False, default=None, help="Path to the seed messages directory")
    args = parser.parse_args()

    protocol = args.protocol
    output_dir = args.output_dir
    seed_messages_dir = args.seed_messages
    try:
        seed_messages: list[str] = load_seed_messages(seed_messages_dir) if seed_messages_dir else None
        # print(f"Seed messages: {seed_messages}")
        test_cases = {}
        if True:
            # 1. Extract message types
            message_types: dict = get_protocol_message_types(protocol)

            # 2. Extract specialized structure
            # message_types = json.load(open(f"protocol_type_results/{protocol}_types.json"))
            specialized_structures: dict = get_specialized_structures(protocol, message_types)

            # 3. Generate message sequences
            # message_types = json.load(open(f"protocol_type_results/{protocol}_types.json"))
            message_sequences: dict = get_message_sequences(protocol, message_types)

            # 4. Generate test cases
            # specialized_structures = json.load(open(f"protocol_specialized_structure_results/{protocol}_specialized_structures.json"))
            # message_sequences = json.load(open(f"message_sequence_results/{protocol}_message_sequences.json"))
            seed_index = 0
            if seed_messages:
                for seed_message in seed_messages:
                    test_cases[seed_index] = get_test_cases(protocol, message_sequences, specialized_structures, seed_message)
                    seed_index += 1
            else:
                test_cases[0] = get_test_cases(protocol, message_sequences, specialized_structures, None)

        if True:
            # 5. Save results
            test_cases[0] = json.load(open(f"testcase_results/{protocol}_testcases.json"))
            for seed_index, test_case in test_cases.items():
                save_test_cases(test_case, output_dir)

    except Exception as e:
        print(f"Error processing protocol {protocol}: {e}")

if __name__ == "__main__":
    main()
