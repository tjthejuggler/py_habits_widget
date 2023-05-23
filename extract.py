import re

def extract_icon_names(filename):
    icon_pattern = re.compile(r"icon\s*=\s*'([^']*)'")
    icon_names = []

    with open(filename, 'r') as file:
        content = file.read()
        icon_names = icon_pattern.findall(content)

    return icon_names

if __name__ == "__main__":
    filename = "icontext.txt"  # Replace with your text file's path
    icon_names = extract_icon_names(filename)
    print(icon_names)
