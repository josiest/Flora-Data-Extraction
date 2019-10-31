import textract
import os
import re

# species name | identifier | provinces it appears in

encoding="utf-8"
fn = 'Bauhinia05bgal.doc'
path = os.path.join(os.getcwd(), fn)
text = textract.process(path, encoding=encoding).decode(encoding)

# regex patterns

# --- Species Name ---
#
# This relies on the assumption that species names follows this format:
#
#  n[a]. Species name
#
# where n is an arbitrary natural at the beginning of a line and a is an
# arbitrary alphabetic character. "Species name" starts with a capital letter,
# but the rest of the name isn't capitalized. There are an arbitrary amount of
# space characters between "n[a]." and "Species name"

#name = re.compile(r'^\d+\w?\.[ ]+[A-Z][a-z]+.*(?:Sp\.|subsp\.|\*)',
#                  flags=re.MULTILINE)
#
## find matches and print them
#matches = name.findall(text)
#print("There are {} matches:\n".format(len(matches)))
#for match in matches:
#    print(match)

# --- Table of Contents Line ---
#
# Relies on the assumption that table of contents lines have following formats
#
#  n. Arbitrary text [.]*m. Species name\n
#
# Where n and m are arbitrary naturals, not necessarily equal to each other
tocline
