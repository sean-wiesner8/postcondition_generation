from datasets import load_dataset
from io import StringIO
import sys


def load_data(dataset):
    if dataset == "humanEval":
        raw_data = load_dataset(
            'openai_humaneval')['test']
        return raw_data
    else:
        raw_data = load_dataset('mbpp')['test']
        return raw_data


"""
Gets the names of the parameters given the raw data of the given dataset.
"""


def get_param_names(data, dataset):
    all_params = []
    if dataset == "humanEval":
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

    else:
        for code, test_list in zip(data['code'], data['test_list']):
            first_test = test_list[0]
            start_idx = 7
            end_idx = first_test.find("(")
            func_name = first_test[start_idx:end_idx].strip()

            var_start_idx = code.find(func_name) + len(func_name)
            while code[var_start_idx] != "(":
                var_start_idx += 1
            var_end_idx = var_start_idx
            while code[var_end_idx] != ")":
                var_end_idx += 1

            var_names = code[var_start_idx + 1:var_end_idx].split(",")
            var_names = [var_name.strip() for var_name in var_names]

            all_params.append(var_names)

        return all_params


"""
For each programming problem, extract the example inputs provided by the dataset.
"""


def get_inputs(data, dataset):
    inputs = []
    if dataset == "humanEval":
        for test in data['test']:
            test = test.split('\n')
            curr_inputs = []
            for test_case in test:
                try:
                    test_case = test_case.strip()
                    if len(test_case) >= 6 and test_case[:6] == "assert":
                        args = test_case.split("candidate")[
                            1].replace("is", "==")
                        args = args.split("==")[0].strip()
                        curr_inputs.append(args)
                except Exception:
                    curr_inputs.append("*ERROR*")

            inputs.append(curr_inputs)

        return inputs

    else:
        for test_list in data['test_list']:
            curr_inputs = []
            for test in test_list:
                input_vals = test.split("==")[0].strip()
                input_vals = input_vals[input_vals.find("("):]
                input_vals = input_vals.strip()
                input_vals = input_vals[:-1] + ",)"

                try:
                    input_vals = eval(input_vals)
                    curr_inputs.append(input_vals)

                except Exception:
                    curr_inputs.append("ERR")

            inputs.append(curr_inputs)

        return inputs


def generate_outputs(inputs, data, param_names, dataset):
    if dataset == "humanEval":
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()

        canonical_solutions = data['canonical_solution']
        for solution, input_group, param_name in zip(canonical_solutions, inputs, param_names):
            for input in input_group:
                if input == "*ERROR*":
                    print("*ERROR*")
                else:
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

                    except Exception:
                        print("*ERROR*")

                print("*END_INPUT*")

            print("*END_PROBLEM*")

        sys.stdout = old_stdout

        all_outputs_str = mystdout.getvalue()
        all_outputs_temp = all_outputs_str.split("*END_PROBLEM*")
        all_outputs = []
        for output_group in all_outputs_temp:
            output_group_temp = output_group.split("*END_INPUT*")
            output_group = []
            for output in output_group_temp:
                output = output.strip('\n')
                output_group.append(output)

            output_group.pop()  # remove extra blank input created with split
            all_outputs.append(output_group)

        return all_outputs

    else:
        all_outputs = []
        for test_list in data['test_list']:
            curr_outputs = []
            for test in test_list:
                output_val = test.split("==")[1].strip()
                try:
                    output_val = eval(output_val)
                except Exception:
                    output_val = "ERR"

                curr_outputs.append(output_val)

            all_outputs.append(curr_outputs)

        return all_outputs


def extract_postconditions(dataset):
    if dataset == "humanEval":
        with open('humanEval_generations.txt') as f:
            lines = f.readlines()

        executable_postconditions = []
        for line in lines:
            if len(line) >= 9 and line[:9] == 'HumanEval':
                executable_postconditions.append([])

            elif len(line) >= 6 and line[:6] == "assert":
                executable_postconditions[-1].append(line)

        return executable_postconditions

    else:
        with open('mbpp_generations.txt') as f:
            lines = f.readlines()

        executable_postconditions = []
        curr_problem_postconditions = []
        curr_postcondition = ""
        valid_add = False
        for line in lines:
            if len(line) >= 8 and line[:8] == "********":
                executable_postconditions.append(curr_problem_postconditions)
                curr_problem_postconditions = []
            elif valid_add and line == "\n":
                valid_add = False
                curr_problem_postconditions.append(curr_postcondition)
                curr_postcondition = ""
            elif valid_add:
                curr_postcondition += line
            elif not valid_add and line[0] == '#':
                valid_add = True
                curr_postcondition += line

        return executable_postconditions


def execute_postconditions(postconditions, param_names, inputs, outputs):
    true_counter = 0
    false_counter = 0
    err_counter = 0
    for problem_postconditions, problem_param_names, problem_inputs, problem_outputs in zip(postconditions, param_names, inputs, outputs):
        for example_input, example_output in zip(problem_inputs, problem_outputs):
            example_context = {}
            for param_name, input_val in zip(problem_param_names, example_input):
                example_context[param_name] = input_val
            example_context['result'] = example_output
            for postcondition in problem_postconditions:
                try:
                    exec(postcondition, example_context)
                    print(True)
                    true_counter += 1
                except AssertionError:
                    print(False)
                    false_counter += 1
                except Exception as e:
                    print("ERROR: " + str(e))
                    err_counter += 1

    print(f"true counter: {true_counter}")
    print(f"false counter: {false_counter}")
    print(f"error counter: {err_counter}")


def main():
    dataset = "mbpp"
    raw_data = load_data(dataset)
    param_names = get_param_names(raw_data, dataset)
    inputs = get_inputs(raw_data, dataset)

    outputs = generate_outputs(inputs, raw_data, param_names, dataset)
    postconditions = extract_postconditions(dataset)

    execute_postconditions(postconditions, param_names, inputs, outputs)


if __name__ == "__main__":
    main()
