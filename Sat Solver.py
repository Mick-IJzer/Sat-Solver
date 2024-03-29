from itertools import chain
from collections import Counter
from copy import deepcopy
from timeit import default_timer as timer
import sys
import numpy as np
import pandas as pd
import random

sys.setrecursionlimit(10000000)

rules_filename = 'sudoku-rules.txt'
backtrack_counter = 0
split_counter = 0
putnam_counter = 0
np.random.seed(25)
random.seed(25)
HEURISTIC = 'DLIS'


def dimacs_to_cnf(filename=None, dimacs=None):
    if dimacs is None:
        file = open(filename, 'r')
        text = file.readlines()
    else:  # filename == None:
        text = dimacs.split(' 0\n')

    rules = list()
    app = rules.append
    for row in text[1:]:
        app(list(map(int, row.strip(' 0\n').split(' '))))

    result = dict()
    for x in list(set(map(abs, chain.from_iterable(rules)))):
        if x > 0:
            result[x] = 'unknown'

    return rules, result


def get_sudokus(filename, n_rows, samplesize):
    file = open(f'{filename}.txt', 'r')
    text = file.readlines()

    puzzles = list()
    start_list = list()
    for i in range(1, n_rows + 1):
        for j in range(1, n_rows + 1):
            start_list.append(int(str(i) + str(j)))

    for sudoku in random.sample(text, samplesize):
        sudoku_clauses = list()
        app = sudoku_clauses.append
        for i in range(n_rows * n_rows):
            if sudoku[i] != '.':
                app([int(str(start_list[i]) + str(sudoku[i]))])
        puzzles.append(sudoku_clauses)

    return puzzles


def format_result(result_dict):
    result = []
    app = result.append
    for key in result_dict:
        if result_dict[key]:
            app(key)

    return result


def adjust_counters(i):
    global backtrack_counter, split_counter, putnam_counter
    i += 1
    backtrack_counter = 0
    split_counter = 0
    t = timer()
    putnam_counter = 0
    return putnam_counter, backtrack_counter, split_counter, t, i


def check_tautology(clause):
    for variable in clause:
        if -variable in clause:
            return True

    return False


def check_pure_literals(rules):
    variable_dict = dict(Counter(chain.from_iterable(rules)))
    pure_literals = list()
    app = pure_literals.append

    for key in variable_dict.keys():
        if -key not in variable_dict.keys():
            app(key)

    return [pure_literals]


def check_tautology_unit(rules):
    global putnam_counter

    to_remove = list()
    unit_clauses = list()
    app = unit_clauses.append

    for clause in rules:
        if putnam_counter == 1 and check_tautology(clause):
            to_remove.append(clause)

        if len(clause) == 1:
            app(clause)

        elif len(clause) == 0:
            return rules, unit_clauses, 'Backtrack'

    for clause in to_remove:
        rules.remove(clause)

    return rules, unit_clauses, 'Loop'


def set_clause(rules, result, variables_to_set):
    # t = timer()

    for variable in variables_to_set:
        state = True if variable > 0 else False
        result[abs(variable)] = state

    new_rules = list()
    for clause in rules:
        skip = False
        for variable in variables_to_set:
            if -variable in clause:
                clause.remove(-variable)
            elif variable in clause:
                skip = True
                break
        if not skip:
            new_rules.append(clause)

        rules = new_rules
    # print(len(variables_to_set), round(timer() - t, 2))
    return rules, result


def simplify_rules(rules, result):
    global putnam_counter

    rules, unit_clauses, action = check_tautology_unit(rules)
    if action == 'Backtrack':
        return rules, result, 'Backtrack'

    variables_to_set = check_pure_literals(rules)
    variables_to_set.extend(unit_clauses)

    variables_to_set = list(chain.from_iterable(variables_to_set))
    for variable in variables_to_set:
        if -variable in variables_to_set:
            if putnam_counter > 1:
                return rules, result, 'Backtrack'
            else:
                return rules, result, 'Unsolvable'

    if len(variables_to_set) > 0:
        new_rules, new_result = set_clause(rules, result, variables_to_set)
        return new_rules, new_result, 'Loop'
    elif len(variables_to_set) == 0 and len(rules) == 0:
        return rules, result, 'Satisfied'
    else:
        return rules, result, 'Split'


def backtrack(history):
    global backtrack_counter
    backtrack_counter += 1

    variable, rules, result = history[-1]
    history = history[:-1]

    rules, result = set_clause(rules, result, [-variable])
    putnam(rules, result, history)


def split(rules, result, history, heuristic='RANDOM'):
    global split_counter
    split_counter += 1

    if heuristic == 'DLIS':
        variable = DLIS(rules)
    elif heuristic == 'PDLIS':
        variable = PDLIS(rules)
    elif heuristic == 'RDLIS':
        variable = RDLIS(rules)
    elif heuristic == 'RPDLIS':
        variable = RPDLIS(rules)
    else:  # heuristic == 'RANDOM'
        variable = random.choice(list(set(chain.from_iterable(rules))))

    history.append((variable, deepcopy(rules), deepcopy(result)))
    rules, result = set_clause(rules, result, [variable])

    putnam(rules, result, history)


def DLIS(rules):
    variable_dict = dict(Counter(chain.from_iterable(rules)))

    return min(variable_dict, key=variable_dict.get)


def PDLIS(rules):
    variable_dict = dict(Counter(chain.from_iterable(rules)))
    values = [variable_dict[key] for key in variable_dict.keys()]
    probabilities = [(value / sum(values)) for value in values]

    return np.random.choice(list(variable_dict.keys()), size=1, p=probabilities)[0]


def RDLIS(rules):
    variable_dict = dict(Counter(chain.from_iterable(rules)))

    return (max(variable_dict, key=variable_dict.get)) * (random.sample([-1, 1], 1)[0])


def RPDLIS(rules):
    variable_dict = dict(Counter(chain.from_iterable(rules)))
    values = [variable_dict[key] for key in variable_dict.keys()]
    probabilities = [(value / sum(values)) for value in values]

    return np.random.choice(list(variable_dict.keys()), size=1, p=probabilities)[0] * (random.sample([-1, 1], 1)[0])


def putnam(rules, result, history):
    global putnam_counter
    putnam_counter += 1

    while True:
        rules, result, action = simplify_rules(rules, result)
        if action != 'Loop':
            break

    if putnam_counter == 1:
        history.append(('Initial', deepcopy(rules), deepcopy(result)))

    if action == 'Split':
        split(rules, result, history, heuristic=HEURISTIC)
    elif action == 'Backtrack':
        backtrack(history)
    elif action == 'Unsolvable':
        print('UNSOLVABLE')
    else:  # action == 'Satisfied'
        # print('SATISFIED')
        return format_result(result)


# get the rules and the result template from the dimacs file and give them to the putnam function
base_rules, result_template = dimacs_to_cnf(rules_filename)
sudokus = get_sudokus('1000 sudokus', 9, 200)
dataset = pd.DataFrame(columns=['Id', 'Heuristic', 'Time', 'Backtracks', 'Splits', 'Putnam calls'])

i = 0
for sudoku in sudokus:
    print('SUDOKU', i + 1)
    putnam_counter, backtrack_counter, split_counter, t, i = adjust_counters(i)

    rules = deepcopy(base_rules)
    rules.extend(sudoku)
    result = deepcopy(result_template)
    putnam(rules, result, history=list())  # give an empty list as history in the first function call

    dataset = dataset.append({'Id': i, 'Heuristic': HEURISTIC, 'Time': timer() - t, 'Backtracks': backtrack_counter,
                              'Splits': split_counter, 'Putnam calls': putnam_counter}, ignore_index=True)

# example for using the satsolver based on a dimacs in text
# adimacs = 'a pnf 6 4\n1 -2 3 0\n2 4 -5 6 0\n -1 3 4 0\n -4 6'
# rules, result = dimacs_to_cnf(dimacs=adimacs)
# result = putnam(rules, result, history=list())

filename = f'Sat_solver_{HEURISTIC}.xls'
dataset.to_excel(filename, index=False)
