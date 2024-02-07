

import requests
import json
import re

def toggle_stats(numbers: list[int]) -> list[int]:
    """Toggle all the stats based on the indexes the given list.
    
    Args:
    numbers (list[int]): The list of indexes to toggle.

    Returns:
    list[int]: The toggled list of integers.
    """
    print('toggled numbers', numbers)
    return numbers

# API endpoint
url = 'http://localhost:11434/api/generate'

prompt = \
'''
def toggle_stats(numbers: list[int]) -> list[int]:
    Toggle all the stats based on the indexes the given list.
    
    Args:
    numbers ([1,2,3]): The list of indexes to toggle.
    *Do not send an empty list.
    
    return toggled_numbers

    {stats_key}

    

User Query: {query}<bot_end>
'''

#/home/lunkwill/projects/py_habits_widget/stats_key.txt
with open ("/home/lunkwill/projects/py_habits_widget/stats_key.txt", "r") as myfile:
    STATS_KEY=myfile.read()

prompt = prompt.format(query="toggle every Juggling stat", stats_key=STATS_KEY)
print("prompt")
data = {
    "model": "nexusraven",
    "prompt": prompt,
    "stream": False,
    "options": {"num_predict": 100}
}

# Headers
headers = {'Content-Type': 'application/json'}

# POST request
response = requests.post(url, headers=headers, data=json.dumps(data))
#convert response.text to json

json_response = response.json()
text_response = json_response["response"]

print(json_response)

print(text_response)

print("\n" + "="*50 + "\n")

function_to_call = text_response.lower().split("Call: ")[0].split("Thought:")[0].strip()

print('function_to_call', function_to_call)
match = re.search(r'(?<=call: ).*(?=\n)', function_to_call)

if match:
    valid_function_call = match.group(0)
    
    try:
        result = eval(valid_function_call)
        print("Result:", result)
    except NameError:
        print("Function not found.")
    except Exception as e:
        print("An error occurred:", str(e))
else:
    print("Valid function call not found.")
