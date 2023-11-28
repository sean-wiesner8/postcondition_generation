from openai import OpenAI
from datasets import load_dataset
import os

os.environ['OPENAI_API_KEY'] = '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'
client = OpenAI()

INPUT_INTRO = "Given the problem description of the programming problem defined below, as well as the definition of a post-condition defined below, create 10 post-conditions in Python to test against an implementation of the programming problem. Before creating these test cases, reiterate what a post-condition is based on the definition described below.\n\n"

POSTCONDITION_DEF = "Definition of a post-condition: A post-condition is an assert statement that checks for a condition that should be true regardless of the input.\n\n"

EXAMPLE_POSTCONDITION = 'Here is an example post-condition for an arbitrary programming problem:\n"# Post-condition 1: The output should be a float or an integer.\nassert isinstance(result, (int, float))"'


def load_data(dataset):

    if dataset == "humanEval":
        raw_datasets = load_dataset(
            'openai_humaneval')  # loading dataset
        return raw_datasets['test']

    if dataset == "mbpp":
        raw_datasets = load_dataset(
            'mbpp')
        return raw_datasets['test']


def format_inputs(raw_data, dataset):

    prompt_data = []
    if dataset == "humanEval":
        for prompt in raw_data['prompt']:
            prompt = prompt.split(">>>", 1)[0].strip(" ").strip("\n")
            prompt = prompt.replace("\n", "")
            if '"""' in prompt:
                prompt = prompt.split('"""')
            else:
                prompt = prompt.split("'''")

            function_def = prompt[0].strip(" ")
            function_desc = prompt[1].split("Example:")[0].strip(" ")

            def_idx = function_def.find("def")
            if def_idx != 0:
                function_def = function_def[:def_idx] + \
                    "\n" + function_def[def_idx:]
            function_def = function_def.strip("\n")

            prompt = '"' + function_def + "\n" + function_desc + '"\n\n'
            prompt = INPUT_INTRO + 'Programming problem:\n' + \
                prompt + POSTCONDITION_DEF + EXAMPLE_POSTCONDITION
            prompt_data.append(prompt)

    else:
        pass

    return prompt_data


def main():
    dataset = 'humanEval'
    raw_data = load_data(dataset)
    formatted_inputs = format_inputs(raw_data, dataset)

    with open('generated_inputs.txt', 'w') as f:
        for generation in formatted_inputs:
            f.write(f"{generation}\n\n********\n\n")


if __name__ == "__main__":
    main()
