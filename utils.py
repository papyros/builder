import re
import yaml

def load_yaml(fileName):
    from yaml import load
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader
    stream = open(fileName, "r")
    return load(stream, Loader=Loader)


def append_to_file(filename, text):
    if isinstance(text, list):
        text = '\n'.join(text)
    with open(filename, 'a') as file:
        file.write(text)


def replace_in_file(filename, regex, replacement):
    regex = re.compile(regex)

    lines = []
    with open(filename) as infile:
        for line in infile:
            line = regex.sub(replacement, line)
            lines.append(line)
    with open(filename, 'w') as outfile:
        for line in lines:
            outfile.write(line)
