from datasets import load_dataset
from io import StringIO
import sys


def load_data():
    raw_data = load_dataset(
        'openai_humaneval')['test']
    return raw_data


def get_param_names(data):
    all_params = []
    for prompt, entry_point in zip(data['prompt'], data['entry_point']):
        # empty character for edge case where func name is in "def"
        prompt = prompt.split(' ' + entry_point)[1]

        params = ()
        j = 1
        while prompt[j] != ')':
            k = j
            while prompt[k] != ':' and prompt[k] != ',' and prompt[k] != ')':
                k += 1

            param_name = prompt[j:k]
            params += (param_name,)

            while prompt[k] != ',' and prompt[k] != ')':
                k += 1

            if prompt[k] == ',':
                if prompt[k + 1] == ' ':
                    j = k + 2
                else:
                    j = k + 1
            else:
                j = k

        all_params.append(params)

    return all_params


def get_inputs(data):
    inputs = []
    errors = 0
    for test in data['test']:
        test = test.split('\n')
        curr_inputs = []
        for test_case in test:
            try:
                test_case = test_case.strip()
                if len(test_case) >= 6 and test_case[:6] == "assert":
                    args = test_case.split("candidate")[1].replace("is", "==")
                    args = args.split("==")[0].strip()
                    curr_inputs.append(args)
            except Exception:
                pass

        inputs.append(curr_inputs)

    return inputs


def generate_outputs(inputs, data, param_names):
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()

    canonical_solutions = data['canonical_solution']
    all_outputs = []
    for solution, input_group, param_name in zip(canonical_solutions, inputs, param_names):
        curr_outputs = []
        for input in input_group:
            try:
                executable_str = "def candidate("
                for arg_name in param_name:
                    executable_str += arg_name + ", "

                executable_str = executable_str[:-2]
                executable_str += "):\n"
                executable_str += solution + '\n'

                executable_str += "print(candidate" + input + ')'

                compiled_executable = compile(
                    executable_str, "<string>", "exec")
                exec(compiled_executable)

                curr_outputs.append(mystdout.getvalue())

            except Exception as e:
                pass

        all_outputs.append(curr_outputs)

    sys.stdout = old_stdout
    return all_outputs


def extract_postconditions():
    pass


def execute_postconditions(param_names, postconditions, inputs, outputs):
    pass


def calculate_scores(results):
    pass
    # total_score = 0
    # for problem in results:
    #     passed = 0
    #     total = 0
    #     for example in problem:
    #         for postcondition in problem[example]:
    #             passed += int(postcondition)
    #             total += 1

    #     score = passed / total
    #     print(score)
    #     total_score += score

    # print("*******")
    # print(total_score / len(results))


def main():
    raw_data = load_data()
    param_names = get_param_names(raw_data)
    inputs = get_inputs(raw_data)

    outputs = generate_outputs(inputs, raw_data, param_names)
    postconditions = extract_postconditions()
    results = execute_postconditions(
        param_names, postconditions, inputs, outputs)

    calculate_scores(results)


if __name__ == "__main__":
    main()
