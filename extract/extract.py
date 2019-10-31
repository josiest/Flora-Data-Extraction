import textract
import os
import re

# species name | identifier | provinces it appears in

encoding="utf-8"
fn = 'Bauhinia05bgal.pdf'
path = os.path.join(os.getcwd(), fn)
text = textract.process(path, encoding=encoding).decode(encoding)
#with open("out.txt", "w") as f:
#    f.write(text)

# regex patterns

# --- Index Line ---
#
# Relies on the assumption that table of contents lines have following formats
#
#  n. Arbitrary text [.]*m. Species name\n
#
# Where n and m are arbitrary naturals, not necessarily equal to each other.
iline_pattern = re.compile(r'^[ ]*\d+\..*\d+\.[ ]*([A-Za-z]+[A-Za-z ]*)',
                           flags=re.MULTILINE)

matches = iline_pattern.findall(text)
print("There are {} matches:\n".format(len(matches)))
for match in matches:
    print(match+'\n')
