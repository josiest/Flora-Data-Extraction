import textract
import os
import re
import json
import argparse

from collections import OrderedDict

# Data to extract:
#   species name | identifier | states and provinces it appears in

def load_treatment(fn, encoding='utf-8'):
    """ Load the treatement using textract

    Parameters:

        fn - the file name of the treatment
        encoding - the encoding of the file (defaults to utf-8)
    """
    path = os.path.join(os.getcwd(), fn)
    return textract.process(path, encoding=encoding).decode(encoding)

# regex patterns

# --- Species name from index line ---
#
# Relies on the assumption that index lines have the following format
#
#  n. Arbitrary text m. Species name\n
#
# Where n and m are arbitrary naturals, not necessarily equal to each other,
# and there are an arbitrary number of spaces before "n." and after "m."

index_pattern = re.compile(r'\d+\.[ ]*([A-Za-z]+[A-Za-z ]*)'+
                           r'[ ]*(?:\(in part\))?$', flags=re.MULTILINE)

genus_pattern = re.compile(r'^[ ]*\d+\.[ ]*([A-Z]+)', flags=re.MULTILINE)

def get_species_names(text):
    """Get the names of all species listed in the treatment.

    Parameters:
        text - the treatment to search from (a string)
    """
    names = index_pattern.findall(text)

    # it's possible that the text has no index - this happens when there's
    # only one subspecies
    if len(names) > 0:
        return names

    # if this is the case, find the genus name and search for the first
    # occurence of the species
    genus = genus_pattern.search(text)[1]
    genus = genus[0] + genus[1:].lower()
    p = re.compile(r'^[ ]*1\.[ ]*('+genus+' [a-z]+)', flags=re.MULTILINE)
    return list(OrderedDict.fromkeys(p.findall(text)))

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

def get_all_names(text, names):
    """Get all species and subspecies names, including the numbering

    Parameters:
        text - the treatment text (a string)
        names - a list of species names
    """
    reg_names = '|'.join(['(?:{})'.format(s) for s in names])
    intro_pattern = re.compile(r'^\d+[a-z]*\.[ ]*(?:'+reg_names+')',
                               flags=re.MULTILINE)
    return intro_pattern.findall(text)

def partition_text(text, names):
    """Partition the text into blocks based on species name.

    text - the treatment text (a string)
    names - a list of species names

    This will also break subspecies into their own blocks.
    """
    reg_names = '|'.join(['(?:{})'.format(s) for s in names])
    intro_pattern = re.compile(r'^\d+[a-z]*\.[ ]*(?:'+reg_names+')',
                               flags=re.MULTILINE)
    
    # Split the whole text into blocks based on the introduction to each subsp.
    indices = [m.start() for m in intro_pattern.finditer(text)]
    indices.append(-1) # add the end of the text to the list so as to include
                       # the last block (ideally I'd like to cut off the info
                       # not relevant, but it's really not that important to do
                       # that)
    return [text[indices[i]:indices[i+1]] for i in range(len(indices)-1)]

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
    """Finds the identifiers for a species.

    Parameters:
        block - a block of text (a string) with its scope limited to a single
                species or subspecies

    Returns an empty string if there are no identifiers for this species.
    """
    for line in block.split('\n'):
        matches = id_pattern.findall(line)
        if matches:
            return matches[-1].replace(':','').strip()
    return ''

# --- Finding provinces ---
#
# abbreviations and full state names are listed in geography.txt and
# locations.txt so grab each of them

# I could just use a string, but I want to '|'.join(loc_names) so it'll be
# easier to '|' the two to gether
loc_names = []
for fn in ('geography.txt', 'locations.txt'):
    path = os.path.join(os.getcwd(), fn)
    with open(path) as f:
        s = f.read()
        # these are special regex charaters, so escape them wherever they
        # appear
        for r in ('.', '(', ')'):
            s = s.replace(r, '\\'+r)
        # I want to '|' each province name, but since they have non-alphabetic
        # characters I need to group each name w/o capturing, hence the (?:)
        #
        # Also cut off the last blank line
        loc_names.append('|'.join(['(?:'+m+')' for m in s.split('\n')[:-1]]))

# add the parentheses to capture the names
loc_names = '('+'|'.join(loc_names)+')'
loc_pattern = re.compile(loc_names)

# load the key which maps full state and province names to their abbreviations
key_fn = 'key.json'
key_path = os.path.join(os.getcwd(), key_fn)

key = {}
with open('key.json') as f:
    key = json.load(f)

def get_locations(block):
    """Finds the locations a species appears in.

    Parameters:
        block - a block of text (a string) with its scope limited to a single
                species or subspecies
    """
    # find all states and provinces in the block
    locs = loc_pattern.findall(block)
   
    # convert full state and province names to their abbreviations and
    # remove duplicates
    locs = {key[loc] if loc in key else loc for loc in locs}
    return '"'+', '.join(locs)+'"'

def parse_file(fn):
    """Parse the pdf file (a genus treatment) into a csv file

    The csv file has the format
        species name, identifier, locations it appears in

    The csv file name has the same name as the pdf.

    Parameters:
        fn - the file name of the pdf
    """
    # Load the text
    text = load_treatment(fn)

    # Find the names of the species, then find all occurences of the
    # species and subspecies
    names = get_species_names(text)
    all_names = get_all_names(text, names)

    # Partition the text into blocks based on species and subspecies
    blocks = partition_text(text, names)

    # Find the identifiers and the locations they appear in for each species
    # and subspecies
    ids = [find_id(block) for block in blocks]
    locs = [get_locations(block) for block in blocks]

    # put each sub/species, id, and list of locations onto a line in a csv file
    csv_iter = zip(all_names, ids, locs)
    lines = [', '.join([name, ID, loc]) for name, ID, loc in csv_iter]
    s = '\n'.join(lines)

    # name the csv file after the pdf input
    fn_pattern = re.compile(r'(\w+)\.pdf')
    fn = fn_pattern.match(fn)[1]
    with open(fn+'.csv', 'w') as f:
        f.write(s)

def main():
    parser = argparse.ArgumentParser(description='Extract flora data')
    parser.add_argument('filenames', metavar='F', nargs='+',
                        help='the treatment files to extract from')

    args = parser.parse_args()
    for fn in args.filenames:
        parse_file(fn)

if __name__ == '__main__':
    main()
