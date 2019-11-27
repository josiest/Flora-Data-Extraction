import textract
import re
import json
import argparse
import os
import textwrap

from collections import OrderedDict
from pathlib import Path

file_dir = Path(__file__).parent.absolute()
cwd = Path()

# Data to extract:
#   species name | states and provinces it appears in | identifier

def main():
    # Build the command line argument parser
    description = '''\
            Extract data from genus treatment pdfs of "Flora of North America

            The csv ouptut files should have the following format:

                <genus name>, <locations appeared in>, <identifier>
    '''
    prog='python -m florana.extract'

    fmt_class = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=fmt_class,
                                     description=textwrap.dedent(description),
                                     prog=prog)
    parser.add_argument('-A', action='store_true',
                        help='parse all pdf files in the current directory')
    parser.add_argument('filenames', metavar='F', nargs='*',
                        help='the treatment files to extract from')

    success = True
    args = parser.parse_args()

    treatments = []

    # The user specified to parse all pdf files in the directory
    if args.A and not args.filenames:
        treatments = [fn for fn in os.listdir() if '.pdf' in fn]

    # The user specified the files manually
    elif args.filenames:
        treatments = args.filenames

    else:
        message = 'Please either specify filenames manually or use the '\
                  '"parse all" flag (-A).'
        success = False

    for treatment in treatments:
        # name the csv file after the pdf input
        match = re.match(r'(\w+)\.pdf', treatment)
        if not match:
            print(f'"{treatment}" is not a pdf file!')
            success = False
            continue
        fn = match[1]
        with open(fn+'.csv', 'w') as f:
            # write all of the extracted data in this treatment to the csv
            #try:
            #    f.write(extract_from(treatment))
            #except Exception as e:
            #    print(f'{e}')
            #    success = False
            f.write(extract_from(treatment))

    if success:
        print('Data was extracted successfully')
    else:
        print('An error occured when extracting the flora data')

def extract_from(treatment):
    """Extract the data from the genus treatment.

    Parameters:
        treatment - a pdf file name of the genus treatment.

    Returns a string with the following csv format for each line:

        <Full species name>, <Identifiers>, "<Locations appeared in>"

    Raises a runtime error if the genus isn't found in the treatment.
    """
    text = load_treatment(treatment)
    genus = genus_in(text)
    if not genus:
        raise RuntimeError("No genus found")

    lines = ''
    sep = ''
    for block, name in partition(text, genus):
        lines += sep+'\n'.join(data_in(block, name))
        sep = '\n'
    return lines

def load_treatment(fn, encoding='utf-8'):
    """ Load the treatement using textract

    Parameters:

        fn - the file name of the treatment
        encoding - the encoding of the file (defaults to utf-8)
    """
    path = Path.joinpath(Path.cwd(), fn)
    return textract.process(str(path), encoding=encoding).decode(encoding)

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

def genus_in(treatment):
    """Return the genus name in the given treatment string.
    
    If the genus couldn't be found, an empty string is returned.
    """
    genus_match = genus_pattern.search(treatment)
    # If the genus name couldn't be found, return an empty string
    if not genus_match:
        return ""
    # Else, get the first match and de-"caps-lock" it
    genus = genus_match[1]
    return genus[0]+(genus[1:].lower())

def partition(treatment, genus):
    """Yield the block and name in treatment associated with each species*.

    treatment - the treatment text (a string)
    species - a list of species names

    * This includes subspecies.
    """
    key_pattern = build_key_pattern(genus)
    species = key_pattern.findall(treatment)

    # It's possible that the pattern will find duplicates of a species in
    # the species key. We want to remove the duplicates, but preserve the order,
    # so use the keys of an OrderedDict as a set.
    species = list(OrderedDict.fromkeys(species).keys())

    i, j = 0, 0
    # it's possible that the text has no species key - this happens when
    # there's only one species
    name = ''
    if not species:
        intro_pattern = build_intro_pattern(genus)
        intro = intro_pattern.search(treatment)

        if not intro:
            raise StopIteration('No species found')

        j = intro.start()
        name = ' '.join(intro.groups())

    # Split the whole text into blocks based on the introduction to each subsp.
    for next_name in species:
        # split the name up into its individual parts in order to pass once
        # again into the intro_pattern builder
        genus, species = next_name.split(' ')
        intro_pattern = build_intro_pattern(genus, species=species)

        # get a list of regex matches
        intros = list(intro_pattern.finditer(treatment))

        # if there are subspecies, go through each one
        if len(intros) > 1:
            # rebuild the intro pattern to specifically look for subspecies
            intro_pattern = build_intro_pattern(genus, species=species,
                                                subspecies=r'[a-z]+')

            # go through each species introduction match
            for intro in intro_pattern.finditer(treatment):
                # This is technically actually yielding the previous match,
                # but at the end we'll yield the current match
                i = j
                j = intro.start()
                # Only yield the previous match when we've actually found it
                if i > 0:
                    yield treatment[i:j], name
                name = ' '.join(intro.groups())

        # otherwise, yield the first and only match
        elif len(intros) == 1:
            # Once again, we're technically yielding the previous match, but
            # we'll yield the current match at the end
            i = j
            j = intros[0].start()
            # Once again, only yield the previous match after it's been found
            if i > 0:
                yield treatment[i:j], name
            name = next_name

        # No match!
        else:
            message = f"Couldn't find the species introduction for {name}!"
            raise StopIteration(message)

    # Finally yield the "current" match (the last match). Ideally I'd like to
    # cut off the info not relevant, but it's really not that important
    yield treatment[j:-1], name

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
    #  n. <genus> <species> [(in part)]\n
    #
    # Where n is an arbitrary natural, genus is specified, species is a
    # lowercase word and "(in part)" doesn't necessarily appear

    key_pattern = re.compile(r'\d+\.[ ]*('+genus+' [a-z]+)'+
                             r'(?: \(in part\))?\s*\n', flags=re.MULTILINE)
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

def data_in(block, name):
    """Generate the data from a block of a genus treatment."""
    ids = ids_in(block)
    for loc in locs_in(block):
        yield ', '.join([name, loc, ids])

# --- Finding identifiers ---
#
# Always terminates the line
# Always set off by spaces (never punctuation - before or after)
# If a common name (of the form "* Common name") appears, there will be
#   text between the date and identifiers
# Otherwise it's possible to have a "(parenthetical statement)" between
#   the date and the identifier, but usually not
# It's possible that there are no identifiers

id_pattern = re.compile(r'([CEFIW ]+)$')
def ids_in(block):
    """Finds the identifiers for a species.

    Parameters:
        block - a block of text (a string) with its scope limited to a single
                species or subspecies

    Returns an empty string if there are no identifiers for this species.
    """
    for line in block.split('\n'):
        matches = id_pattern.findall(line)

        # If matches were found return the last match (the pattern is meant to
        # be searched from the end of the line)
        if matches:
            return matches[-1].strip()

    # if no matches found, there are no identifiers; return an empty string
    return ''

# --- Finding provinces ---
#
# abbreviations and full state names are listed in geography.txt and
# locations.txt so grab each of them

# I could just use a string, but I want to '|'.join(loc_names) so it'll be
# easier to '|' the two to gether
loc_names = []
for fn in ('geography.txt', 'locations.txt'):
    path = Path.joinpath(file_dir, fn)
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

loc_text_pattern = re.compile(r'0\s+?m;.*?\.\s*\n', re.DOTALL)

# load the key which maps full state and province names to their abbreviations
key_fn = 'key.json'
key_path = Path.joinpath(file_dir, key_fn)

key = {}
with open(key_path) as f:
    key = json.load(f)

def locs_in(block):
    """Generates the locations that a species appears in.

    Parameters:
        block - a block of text (a string) with its scope limited to a single
                species or subspecies
    """
    # First find the flowering paragraph
    s = loc_text_pattern.search(block)
    if s:
        s = s[0]
    else:
        raise StopIteration("No locations found!")

    # find all states and provinces in the paragraph
    locs = loc_pattern.findall(s)
   
    # remove duplicates
    #locs = {key[loc] if loc in key else loc for loc in matches}

    for loc in locs:
        # convert full state and province names to their abbreviations
        if loc in key:
            loc = key[loc]

        # Handle Nfld/Labr differentiation

        # yield both if both
        if loc == 'Nfld. & Labr.':
            yield 'Nfld.'
            yield 'Labr.'

        # otherwise yield the relevant one
        elif loc == 'Nfld. & Labr. (Labr.)':
            yield 'Labr.'
        elif loc == 'Nfld. & Labr. (Nfld.)':
            yield 'Nfld.'

        # now that these cases have been handled, yield as usual
        else:
            yield loc

if __name__ == '__main__':
    main()
