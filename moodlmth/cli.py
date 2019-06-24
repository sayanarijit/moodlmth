import os
import sys
from argparse import ArgumentError, ArgumentParser, FileType

import requests

from moodlmth.converter import Converter


def main():
    parser = ArgumentParser(__file__)
    parser.add_argument("target", help="Target path or URL")
    parser.add_argument(
        "-o",
        "--outfile",
        type=FileType("w"),
        help="Destination file path.",
        default=sys.stdout,
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force python formatting with black's 'fast' mode",
    )

    args = parser.parse_args()
    content = ""
    if args.target.startswith("http://") or args.target.startswith("https://"):
        content = requests.get(args.target).text
    elif os.path.exists(args.target):
        with open(args.target) as f:
            content = f.read()
    else:
        raise ArgumentError(f"Invalid target: {args.target}")

    if not content:
        raise ValueError("No content found")

    print(Converter().convert(content), file=args.outfile)


if __name__ == "__main__":
    main()
