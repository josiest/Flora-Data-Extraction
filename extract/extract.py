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

# --- Species name from index line ---
#
# Relies on the assumption that index lines have the following format
#
#  n. Arbitrary text m. Species name\n
#
# Where n and m are arbitrary naturals, not necessarily equal to each other,
# and there are an arbitrary number of spaces before "n." and after "m."
name_pattern = re.compile(r'^[ ]*\d+\..*\d+\.[ ]*([A-Za-z]+[A-Za-z ]*)',
                          flags=re.MULTILINE)
names = name_pattern.findall(text)

# --- Species Introduction ---
#
# Relies on the assumption that a species introduction is formatted as:
#
#  n[a]*. Species name {arbitrary text}
#
# Where n is an arbitrary natural, a is an arbitrary alphabetical character,
# and there are an arbitrary number of space characters between "n[a]*." and
# "Species name" and an arbitrary number of space characters between
# "Species name" and "{arbitrary text}"

names = '|'.join(['(?:{})'.format(s) for s in names])
intro_pattern = re.compile(r'^\d+[a-z]*\.[ ]*(?:'+names+')',
                           flags=re.MULTILINE)

# Split the whole text into blocks based on the introduction to each subsp.
indices = [m.start() for m in intro_pattern.finditer(text)]
indices.append(-1) # add the end of the text to the list so as to include the
                   # last block (ideally I'd like to cut off the info not
                   # relevant, but it's really not that important to do that)
blocks = [text[indices[i]:indices[i+1]] for i in range(len(indices)-1)]

# --- Finding identifiers ---
#
# Always terminates the line
# Always set off by spaces (never punctuation - before or after)
# If a common name (of the form "* Common name") appears, there will be
#   text between the date and identifiers
# Otherwise it's possible to have a "(parenthetical statement)" between
#   the date and the identifier, but usually not
# It's possible that there are no identifiers
id_pattern = re.compile(r'([(?:C|E|F|I|W) ]+)$')
def find_id(block):
    for line in block.split('\n'):
        matches = id_pattern.findall(line)
        if matches:
            return matches[-1].strip()
    return ''
ids = [find_id(block) for block in blocks]

# --- Finding provinces ---
#
# abbreviations and full state names are listed in geography.csv and states.csv
# so grab each of them

# I could just use a string, but I want to '|'.join(loc_names) so it'll be
# easier to '|' the two to gether
loc_names = []
for fn in ('geography.csv', 'states.csv'):
    path = os.path.join(os.getcwd(), fn)
    with open(path) as f:
        s = f.read()
        # these are special regex charaters, so escape them wherever they
        # appear
        for r in ('.', '(', ')'):
            s = s.replace(r, '\\'+r)
        # I want to '|' each province name, but since they have non-alphabetic
        # characters I need to group each name w/o captureing, hence the (?:)
        #
        # Also cut off the last blank line
        loc_names.append('|'.join(['(?:'+m+')' for m in s.split('\n')[:-1]]))

# add the parentheses to capture the names
loc_names = '('+'|'.join(loc_names)+')'

loc_pattern = re.compile('('+geo+'|'+states+')')
locs = [loc_pattern.findall(block) for block in blocks]
