import os
import sys

def notify(text):
    print('text')    
    msg = "notify-send ' ' '"+text+"'"
    os.system(msg)



def main(argument):
    if argument == 'arg1':
        notify("Hello, this is the output for arg1!")
    elif argument == 'arg2':
        notify("Hello, this is the output for arg2!")
    else:
        notify(f"Hello, this is the output for an unrecognized argument: {argument}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        notify("Error: Please provide an argument.")
