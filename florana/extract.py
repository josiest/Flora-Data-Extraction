import textract
import re
import json
import argparse
import os
import textwrap
import itertools

from pathlib import Path
from collections import OrderedDict

file_dir = Path(__file__).parent.absolute()
cwd = Path()

# TODO: Recursively iterate through a directory

# Data to extract:
#   species name | states and provinces it appears in | classifier

def main():
    # Build the command line argument parser
    description = '''
            Extract data from genus treatment pdfs of "Flora of North America

            The csv ouptut files should have the following format:

                <genus name>, <locations appeared in>, <classifier>

            Example usage:

                python -m florana.extract -A -o data.csv
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
    parser.add_argument('-o', action='store',
                        help='specify a single output file (csv)')

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
        raise ValueError(message)

    locations = ''
    classifiers = ''
    sep = ''
    error = ''          # Brief error message for program ouput to console
    log_error = ''      # Verbose error message for error.log

    for treatment in treatments:
        # name the csv file after the pdf input
        match = re.match(r'([\w\.]+)\.pdf', treatment)
        if not match:
            print(f'"{treatment}" is not a pdf file!')
            success = False
            continue
        fn = match[1]

        # If the extracting algorithm couldn't find locations, keep track of
        # the error messages
        results = extract_from(treatment)
        if results['error']:
            success = False
            error += sep+results['error']
            log_error += sep+results['verbose-error']

        # If the user specified a single output file, compile all the
        # lines into a single string and write to a file later
        if args.o:
            locations += sep+results['locations']
            classifiers += sep+results['classifiers']

        # If the user didn't specify a single output file write the files
        # for each treatment as we go
        else:
            with open(fn+'.csv', 'w') as f:
                f.write(results['locations'])
            with open(fn+'-classifiers.csv', 'w') as f:
                f.write(results['classifiers'])

        sep = '\n'

    # if the user specified a single output file, now is when we write it
    if args.o:
        # locations file
        fn = args.o

        # classifiers file
        idfn = ''

        # The user may have alread include the file extension
        try:
            i = fn.index('.csv')
            idfn = fn[:i]+'-classifiers'+fn[i:]

        # If the user didn't include the file extension, add it
        except ValueError:
            fn += '.csv'
            idfn = fn+'-classifiers.csv'

        with open(fn, 'w') as f:
            f.write(locations)
        with open(idfn, 'w') as f:
            f.write(classifiers)

    if success:
        print('Data was extracted successfully')
    else:
        print(error)
        with open('error.log', 'wb') as f:
            f.write(log_error.encode('utf8'))
        print('An error occured when extracting the flora data. See ' \
              'error.log for more details.')

def extract_from(treatment):
    """Extract the data from the genus treatment.

    Parameters:
        treatment - a pdf file name of the genus treatment.
        data_type - "locations" or "classifiers"

    Returns a dict of results with the following format

        "locations" - a string of species names and locations they appear in

        "classifiers" - a string of species names and their classifiers

        "error" - a brief error message stating which species the algorithm
                  couldn't find locations for

        "verbose-error" - an error message stating which species the algorithm
                          couldn't find locations for as well as the block of
                          text that the algorithm searched in for the locations

    Raises a Value error if the genus isn't found in the treatment.
    """
    text = load_treatment(treatment)
    genus = genus_in(text)
    if not genus:
        raise ValueError("No genus was found!")

    data = {'locations': '', 'classifiers': '',
            'error': '', 'verbose-error': ''}
    locsep = ''
    errsep = ''
    idsep = ''

    for block, name in partition(text, genus):

        ids = ids_in(block)
        data['classifiers'] += f'{idsep}{name}, {ids}'
        idsep = '\n'

        locs = '\n'.join(f'{name}, {loc}' for loc in locs_in(block))
        if not locs:
            data['error'] += f"{errsep}Couldn't find locations for {name}"
            data['verbose-error'] += f"{errsep}Couldn't find locations for " \
                                     f"{name} in:\n\n{block}\n"
            errsep = '\n'
        else:
            data['locations'] += locsep+locs
            locsep = '\n'

    return data

def load_treatment(fn, encoding='utf-8'):
    """ Load the treatment using textract

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
genus_pattern = re.compile(r'^[ ]*\d+[a-z]*\.[ ]*([A-Z]+)\s+',
                           flags=re.MULTILINE)

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

    *Note that this includes subspecies.

    treatment - the treatment text (a string)
    species - a list of species names
    """
    # Find all the species names in the treatment and reorder them in the order
    # they appear in the text
    name_gens = [keys_in(subgroup, genus) for subgroup in subgroups(treatment)]
    names = sorted(itertools.chain(*name_gens),
                   key=lambda s: int(s.split('.')[0]))

    # We want to remove the number before each name and also remove any
    # duplicates while preserving order. OrderedDict can acheive this
    names = (' '.join(name.split(' ')[1:3]).strip() for name in names)
    names = OrderedDict.fromkeys(names).keys()

    for block, name in species_blocks(treatment, names):
        # each species block may have subspecies
        has_subspecies = False
        for sub_block, sub_name in subspecies_blocks(block, name):
            has_subspecies = True
            yield sub_block, sub_name

        if not has_subspecies:
            yield block, name

def subgroups(treatment):
    """Generate each subgroup block in order."""
    # Find all occurences of genus headers
    headers = list(genus_pattern.finditer(treatment))

    i, j = 0, 0
    # If there are subgroups, the first header is for the entire treatement and
    # there's no species key before the header for the first subgroup, so take
    # the first header out of the list
    if len(headers) > 1:
        headers = headers[1:]

    for next_header in headers:
        # Update j to the start of the current header: we're really yielding
        # the previous match
        j = next_header.start()

        # If the block starts at index 0, then we haven't even reached the first
        # subgroup block, so don't yield yet
        if i > 0:
            yield treatment[i:j]

        # Update i to the start of the current header: on the next iteration
        # it will become the start of the previous header and j will be the
        # start of the current header.
        i = j

    # Once this is encountered, all info is irrelevant for this program
    try:
        k = treatment.lower().index("other reference")
    except:
        k = -1
    if i > 0:
        yield treatment[j:k]

    # If there were no matches, then a genus couldn't be found
    else:
        raise ValueError("No genus was found!")

def keys_in(subgroup, genus):
    """Generate all species names from the species key in a subgroup block.

    subgroup - the subgroup block containing the species
    genus - of the species
    """
    key_pattern = build_key_pattern(genus)

    has_species_key = False
    for match in key_pattern.finditer(subgroup):
        has_species_key = True
        yield match[0]

    # it's possible that the text has no species key - this happens when
    # there's only one species
    if not has_species_key:
        # Compile the intro pattern without knowing what the species is. Since
        # there's only one species this is fine.
        intro_pattern = build_intro_pattern(genus)
        intro = intro_pattern.search(subgroup)

        if not intro:
            raise ValueError('No species found!')

        else:
            yield '1. '+' '.join(intro.groups())

def species_blocks(treatment, names):
    """Generate all species blocks* and names in treatment.

    *Note that this includes all subspecies if any.

    treatment - the treatment text
    names - an ordered list of all species names that appear in the treatment
    """
    error=''
    i, j = 0, 0

    # Split the whole text into blocks based on the introduction to each subsp.
    for next_name in names:
        # split the name up into its individual parts in order to pass once
        # again into the intro_pattern builder, this time compiling to look
        # for a specific species.
        if len(next_name.split(' ')) > 2:
            if error:
                error += '\n'
            error += f'"{next_name}" is too long: expected 2 words!'
            continue
        genus, species = next_name.split(' ')
        intro_pattern = build_intro_pattern(genus, species=species)
        intro = intro_pattern.search(treatment)

        # Produce error message if species introduction couldn't be found
        if not intro:
            if error:
                error += '\n'
            error += f'Could not find species introduction for "{next_name}"'
            continue

        j = intro.start()

        # If i > j, then something went wrong when we reordered the search
        # results.
        if i > j:
            if error:
                error += '\n'
            error += f'When searching in {next_name}: Indices ({i}, {j}) are '\
                     'out of order!'

        # If the block starts at index 0, then we haven't even reached the first
        # species block, so don't yield yet
        elif i > 0:
            yield treatment[i:j], name

        name = next_name
        i = j

    # Finally yield the "current" match (the last match).
    try:
        k = treatment.index("OTHER REFERENCES")
    except ValueError:
        k = -1
    if i > 0:
        yield treatment[j:k], name

    if error:
        error += "\nErrors occured while partitioning species blocks!"
        raise ValueError(error)

def subspecies_blocks(block, species):
    """Generate all subspecies blocks in a species block, if any.
    
    block - the species block to look in
    species - the species name of the form "<genus> <species>"
    """
    if len(species.split(' ')) > 2:
        raise ValueError(f'"{species}" is too long: expected 2 words!')
    genus, species = species.split(' ')

    # Build the intro pattern to specifically look for subspecies
    intro_pattern = build_intro_pattern(genus, species=species,
                                        subspecies=r'[a-z]+')

    error = ''
    i, j = 0, 0
    name = ''
    # go through each subspecies introduction match
    for intro in intro_pattern.finditer(block):

        # Start
        j = intro.start()
        # Only yield the previous match when we've actually found it
        if i > 0:
            if i > j:
                if error:
                    error += '\n'
                error += f'When searching in "{name}" block: Indices ({i}, {j}'\
                         ') are out of order!'
            yield block[i:j], name

        # The name should include the entire species, including the subspecies
        # The intro pattern should have matched all of these.
        name = ' '.join(intro.groups())
        i = j

    # It's possible that there are no subspecies. The intro pattern wouldn't
    # have found anything and i would have never been incremented. If this is
    # the case we don't want to yield anything, otherwise yield the rest of
    # subspecies block until the end of the species block
    if i > 0:
        yield block[j:-1], name

    if error:
        error += "\nErrors occured when partitioning the treatment"
        raise ValueError(error)

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
    # lowercase word and "(in part)" doesn't necessarily appear.
    #
    # The key pattern matches two subgroups:
    #   1. The number that orders how the species appears in the text
    #   2. The genus and species name

    key_pattern = re.compile(r'(\d+)\.[ ]*('+genus+r' (?:x\\)?[a-z\-]+)'+
                             r'(?: \(in part\))?\s*\n', flags=re.MULTILINE)
    return key_pattern

def build_intro_pattern(genus, species=r'(?:x\\)?[a-z\-]+', subspecies=''):
    """Build a regex pattern for a species introduction.

    Paramters:
        genus - of the species
        species - specific species to look for (defaults to any)
        subspecies - the subspecies to look for (defaults to empty string)

    The regex pattern has three potenital subgroups.

    1 - the genus name
    2 - the species name
    3 - the subspecies name (if specified)
    """
    # --- Species Introduction ---
    #
    # Relies on the assumption that a species introduction is formatted as:
    #
    #  n[a]*. Species name {arbitrary text} [(subsp|var). name] {arbitrary text}
    #
    # Where n is an arbitrary natural and a is an arbitrary alphabetical
    # character.

    # This will match the "n[a]*" part of the inroduction
    pattern = r'^\d+'

    # if the subspecies was specified, we know there must be alphabetical
    # numbering on them
    if subspecies:
        pattern += r'[a-z]+'

    if 'x\\' in species and '[a-z' not in species:
        species = species.replace('x\\', 'x\\\\')

    # This will now match the 'n[a]*. Species name' part of the introduction
    pattern += r'\.[ ]*('+genus+') ('+species+')'

    # if the subspecies was specified, we know there must be some descriptor
    # followed by 'subsp.' and the subspecies name
    #
    # i.e. the '{arbitrary text} [(subsp|var). name] {arbitrary text}' part of
    # the introduction is now matched
    if subspecies:
        pattern += r'.*?(?:subsp|var)\.\s*('+subspecies+')'

    return re.compile(pattern, flags=re.MULTILINE|re.DOTALL)

# --- Finding classifiers ---
#
# Always terminates the line
# Always set off by spaces (never punctuation - before or after)
# If a common name (of the form "* Common name") appears, there will be
#   text between the date and classifiers
# Otherwise it's possible to have a "(parenthetical statement)" between
#   the date and the classifier, but usually not
# It's possible that there are no classifiers

id_pattern = re.compile(r'([CEFIW ]+)\s*$', re.MULTILINE)
def ids_in(block):
    """Finds the classifiers for a species.

    Parameters:
        block - a block of text (a string) with its scope limited to a single
                species or subspecies

    Returns an empty string if there are no classifiers for this species.
    """
    error = ''
    sep = ''
    for line in block.split('\n'):
        matches = id_pattern.findall(line)

        # If matches were found return the last match (the pattern is meant to
        # be searched from the end of the line)
        if matches:
            return matches[-1].strip()

    # if no matches found, there are no classifiers; return an empty string
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
        loc_names.extend('(?:'+m+')' for m in s.split('\n')[:-1])

# If one string is a substring of another, regex will match with whatever
# comes first in the pattern. We want to match the longest substrings possible
# so sort the location names by length
#
# Also replace spaces in each name with arbitrary whitespace
loc_names = sorted((loc.replace(' ', r'\s*') for loc in loc_names),
                   key=len, reverse=True)

# Assumes locations have the following format:
#
# {<beginning of line>, <;> or <,>} {location name (may include newlines)}{<;>,
#  <,> or <end of line>}
loc_pattern_str = r'[^;,]\s*('+'|'.join(loc_names)+r')(?:[;,]|\s*?$|\s*?\n)'
loc_pattern = re.compile(loc_pattern_str, re.MULTILINE)

# --- Location Paragraph Pattern ---
#
# Assumes That locations that a species appears in meets the following format:
#
#   0{arbitrary white space}m; {locations on an abitrary number of lines where
#   countries are separated by ';' and states/provinces are separated by ','}.\n
#
# The line doesn't necessarily begin at 0, but a line does end at '.\n'

loc_text_pattern = re.compile(r'0[\)\]]?\s+?m;.*?(?<!Nfld|Labr|..St)'+
                              r'\.\s*?(?:\n|$)', re.DOTALL|re.MULTILINE)
loc_exception_pattern = re.compile(r'(?:Flowering.*?;|introduced;)' \
                                   r'.*?\.\s*?(?:\n|$)', re.DOTALL|re.MULTILINE)

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
    # First find the locations paragraph
    loc_match = loc_text_pattern.search(block)
    if not loc_match:
        loc_match = loc_exception_pattern.search(block)
    loc_text = ""
    if loc_match:
        loc_text = loc_match[0]

    # find all states and provinces in the paragraph
    locs = loc_pattern.findall(re.sub('[Bb]aja\s*[Cc]alifornia', '', loc_text))
   
    # remove duplicates
    #locs = {key[loc] if loc in key else loc for loc in matches}

    for loc in locs:
        # in replace all whitespace with a single space
        loc = ' '.join(loc.split())

        # convert full state and province names to their abbreviations
        if loc in key:
            loc = key[loc]

        # Handle Nfld/Labr differentiation

        # if specified, yield the relevant one
        if '(Labr.)' in loc:
            yield 'Labr.'
        elif '(Nfld.)' in loc:
            yield 'Nfld.'
        # otherwise yield both if both
        elif 'Nfld' in loc and 'Labr' in loc:
            yield 'Nfld.'
            yield 'Labr.'

        # now that these cases have been handled, yield as usual
        elif loc:
            yield loc

if __name__ == '__main__':
    main()
