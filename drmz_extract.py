import json
import re

def create_json_from_drmz_txt():
    with open('/home/twain/noteVault/drmz.md', 'r') as f:
        drmz = f.read()
        lines = drmz.split('\n')
    # Initialize variables to hold the current date and story
    current_date = None
    current_story = ""
    stories_dict = {}

    # Iterate over the lines in the file
    for line in lines:
        # If the line is a date, save it as the current date
        # If the line is a date, save it as the current date
        if re.match(r'\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?', line.strip()):
            current_date = line.strip().split()[0]
        # If the line is part of a story, add it to the current story
        elif line.strip() != "" and line.strip() != ",,,":
            current_story += line.strip() + " "
        # If the line is the end of a story, add the current date and story to the dictionary
        elif line.strip() == ",,," or line.strip() == "":
            if current_date and current_story.strip():
                if current_date in stories_dict:
                    stories_dict[current_date].append(current_story.strip())
                else:
                    stories_dict[current_date] = [current_story.strip()]
            current_story = ""

    # Add the last story to the dictionary
    if current_date and current_story.strip():
        if current_date in stories_dict:
            stories_dict[current_date].append(current_story.strip())
        else:
            stories_dict[current_date] = [current_story.strip()]
    # Write the dictionary to a JSON file
    with open('stories.json', 'w') as f:
        json.dump(stories_dict, f, indent=4)
    
    return stories_dict

#create_json_from_drmz_txt()
