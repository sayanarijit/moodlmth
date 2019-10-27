moodlmth
========
Convert raw HTML pages into python source code

[![PyPI version](https://img.shields.io/pypi/v/moodlmth.svg)](https://pypi.org/project/moodlmth)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/moodlmth.svg)](https://pypi.org/project/moodlmth)
[![Build Status](https://travis-ci.org/sayanarijit/moodlmth.svg?branch=master)](https://travis-ci.org/sayanarijit/moodlmth)
[![codecov](https://codecov.io/gh/sayanarijit/moodlmth/branch/master/graph/badge.svg)](https://codecov.io/gh/sayanarijit/moodlmth)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

What..?
-------
[moodlmth](https://github.com/sayanarijit/moodlmth) is the reverse of [htmldoom](https://github.com/sayanarijit/htmldoom)

Usage
-----
```bash
# Convert web page to Python syntax
moodlmth https://google.com

# Convert web page into YAML syntax
moodlmth -s yaml https://google.com

# Convert HTML file and write to another file
moodlmth /filepath/index.html -o index.py

# Force conversion
moodlmth index.html -o index.py --fast --debug
```
