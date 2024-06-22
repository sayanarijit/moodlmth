moodlmth
========
Convert raw HTML pages into python source code

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
