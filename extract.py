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

# --- Genus pattern ---
#
# Assumes that the file contains the genus name in the following format:
#
#   n. GENUS
#
# Where n is an arbitrary natural and GENUS is all-caps. GENUS doesn't
# necessarily end the line
genus_pattern = re.compile(r'^[ ]*\d+\.[ ]*([A-Z]+)', flags=re.MULTILINE)

def build_key_pattern(genus):
    """Build a regex pattern for the genus key

    Parameters:
        genus - the genus of the file (a string)

    The pattern has one subgroup: the genus and species name
    """

    # --- Species name from index line ---
    #
    # Relies on the assumption that index lines have the following format
    #
    #  n. Arbitrary text m. Species name\n
    #
    # Where n and m are arbitrary naturals, not necessarily equal to each other,
    # and there are an arbitrary number of spaces before "n." and after "m."

    key_pattern = re.compile(r'\d+\.[ ]*('+genus+' [a-z]+)'+
                             r'(?: \(in part\))?\n', flags=re.MULTILINE)
    return key_pattern

def build_intro_pattern(genus, species=r'[a-z]+', subspecies=''):
    """Build a regex pattern for a species introduction.

    Paramters:
        genus - of the species
        species - specific species to look for (defaults to any)
        subspecies - the subspecies to look for (defaults to empty string)

    The regex pattern has three potenital subgroups.

    1 - the genus name
    2 - the species name
    2 - the subspecies name (if specified)
    """
    # --- Species Introduction ---
    #
    # Relies on the assumption that a species introduction is formatted as:
    #
    #  n[a]*. Species name {arbitrary text} [subsp. name] {arbitrary text}
    #
    # Where n is an arbitrary natural and a is an arbitrary alphabetical
    # character.

    # This will match the "n[a]*" part of the inroduction
    pattern = r'^\d+[a-z]'

    # if the subspecies was specified, we know there must be alphabetical
    # numbering on them
    if subspecies:
        pattern += '+'

    # otherwise, we're either not sure there are subspecies or know that there's
    # none, which is exactly what a '*' match is useful for
    else:
        pattern += '*'

    # This will now match the 'n[a]*. Species name' part of the introduction
    pattern += r'\.[ ]*('+genus+') ('+species+')'

    # if the subspecies was specified, we know there must be some descriptor
    # followed by 'subsp.' and the subspecies name
    #
    # i.e. the '{arbitrary text} [subsp. name] {arbitrary text}' part of the
    # introduction is now matched
    if subspecies:
        pattern += r'.*subsp\. ('+subspecies+')'

    return re.compile(pattern, flags=re.MULTILINE)

def get_species_names(text):
    """Get the names of all species listed in the treatment.

    Parameters:
        text - the treatment to search from (a string)

    Returns an empty list if it couldn't find the genus name in the text, or
    if it couldn't find a single species.
    """
    genus_match = genus_pattern.search(text)
    # If the genus name couldn't be found, return an empty list
    if not genus_match:
        return []
    # Else, get the first match and de-"caps-lock" it
    genus = genus_match[1]
    genus = genus[0]+(genus[1:].lower())

    key_pattern = build_key_pattern(genus)

    # It's possible that the pattern will find duplicates of a species in
    # the species key. We want to remove the duplicates, but preserve the order,
    # so use the keys of an OrderedDict as a set.
    species = list(OrderedDict.fromkeys(key_pattern.findall(text)).keys())

    # it's possible that the text has no species key - this happens when
    # there's only one species
    if not species:
        intro_pattern = build_intro_pattern(genus)
        intro = intro_pattern.search(text)

        if not intro:
            return []

        # return the first and second subgroup ("<genus> <species>")
        return [' '.join(intro.groups())]

    # otherwise, we want to find the names of all species, including subspecies
    all_species = []
    for fullname in species:
        # The full name is composed as '<genus> <species>', so break it up
        # into each and pass them on to the intro pattern
        genus, species_name = fullname.split(' ')
        intro_pattern = build_intro_pattern(genus, species=species_name)

        # We specifically want the match objects, so get them from finditer
        intros = list(intro_pattern.finditer(text))

        # If there are subspecies, rebuild the intro patern to look
        # specifically for subspecies
        if len(intros) > 1:
            intro_pattern = build_intro_pattern(genus, species=species_name,
                                                subspecies=r'[a-z]+')
            intros = list(intro_pattern.finditer(text))

        # Then whether there were subspecies or not, append each full
        # species name to the list of all species
        all_species += [' '.join(match.groups()) for match in intros]

    return all_species

def partition_text(text, names):
    """Partition the text into blocks based on species name.

    text - the treatment text (a string)
    names - a list of species names

    This will also break subspecies into their own blocks.
    """
    # Split the whole text into blocks based on the introduction to each subsp.
    indices = []
    for name in names:
        # split the name up into its individual parts in order to pass once
        # again into the intro_pattern builder
        name_pieces = name.split(' ')
        kwargs = {'genus': name_pieces[0], 'species': name_pieces[1]}

        # If the name has a subspecies, add that to the kwargs
        if len(name_pieces) > 2:
            kwargs['subspecies'] = name_pieces[2]

        intro_pattern = build_intro_pattern(**kwargs)

        # find the first intro that matches the given species and add its
        # index in the string
        indices.append(intro_pattern.search(text).start())

    indices.append(-1) # add the end of the text to the list so as to include
                       # the last block (ideally I'd like to cut off the info
                       # not relevant, but it's really not that important to do
                       # that)

    #reg_names = '|'.join(['(?:{})'.format(s) for s in names])
    #intro_pattern = re.compile(r'^\d+[a-z]*\.[ ]*(?:'+reg_names+')',
    #                           flags=re.MULTILINE)
    
    #indices = [m.start() for m in intro_pattern.finditer(text)]
    
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

# --- Location Paragraph Pattern ---
#
# Assumes That locations that a species appears in meets the following format:
#
#   0{arbitrary white space}m; {locations on an abitrary number of lines where
#   countries are separated by ';' and states/provinces are separated by ','}.\n
#
# The line doesn't necessarily begin at 0, but a line does end at '.\n'

loc_text_pattern = re.compile(r'0\s+?m;.*?\.\n', re.DOTALL)

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
    # First find the flowering paragraph
    s = loc_text_pattern.search(block)
    if s:
        s = s[0]
    else:
        return ""

    # find all states and provinces in the paragraph
    locs = loc_pattern.findall(s)
   
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

    # Partition the text into blocks based on species and subspecies
    blocks = partition_text(text, names)
    message = 'There are{} as many blocks as there are names'

    # Find the identifiers and the locations they appear in for each species
    # and subspecies
    ids = [find_id(block) for block in blocks]
    locs = [get_locations(block) for block in blocks]

    # put each sub/species, id, and list of locations onto a line in a csv file
    csv_iter = zip(names, ids, locs)
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
