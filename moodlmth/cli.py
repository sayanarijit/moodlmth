import logging
import os
import sys
from argparse import ArgumentError, ArgumentParser, FileType

import requests

from moodlmth import __version__
from moodlmth.converter import Converter


def main():
    parser = ArgumentParser("moodlmth")
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
        "--fast",
        action="store_true",
        help="Force python formatting with black's 'fast' mode",
    )
    parser.add_argument("--debug", action="store_true", help="Print debug messages")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args()
    content = ""
    if args.target.startswith("http://") or args.target.startswith("https://"):
        resp = requests.get(args.target)
        resp.raise_for_status()
        content = resp.text
    elif os.path.exists(args.target):
        with open(args.target) as f:
            content = f.read()
    else:
        raise ArgumentError(f"Invalid target: {args.target}")

    if not content:
        raise ValueError("No content found")

    logger = logging.getLogger(__name__)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    converter = Converter(fast=args.fast, logger=logger)
    result = converter.convert(content)
    print(result, file=args.outfile)


if __name__ == "__main__":
    main()
