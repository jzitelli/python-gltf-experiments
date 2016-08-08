import argparse
import json


def convert_three(three_json):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='path to input file')
    args = parser.parse_args()

    with open(args.input) as f:
        json_str = f.read()
    three_json = json.loads(json_str)
