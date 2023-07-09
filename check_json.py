import json


def is_valid_json_file(filename):
    try:
        with open(filename, 'r') as f:
            json.load(f)
    except ValueError as e:
        return False
    return True

# Example usage
filename = '/home/lunkwill/Documents/obsidyen/habitsdb.txt'
if is_valid_json_file(filename):
    print("Valid JSON file")
else:
    print("Invalid JSON file")



# from collections import OrderedDict

# #create a test dict with number keys
# test_dict = {2: 'two', 3: 'three', 1: 'one'}

# #order this dict
# ordered_dict = OrderedDict(sorted(test_dict.items()))


# print(ordered_dict)
# #import OrderedDict

