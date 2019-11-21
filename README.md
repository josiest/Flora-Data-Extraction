# Flora Data Extraction Project

This script is designed to extract data from pdf files of genera from the book *Flora of North America*. It creates csv files whose names match the PDF files given to the script as arguments. The csv files have the format

> "Species name", "Location where the species appears", "Identifier"

The easiest way to run the script is to move to a folder where the only pdf files are genera files from *Flora of North America* and enter:

    python -m florana.extract -A

The script will then run on every pdf file in the directory and create a csv for each pdf.

**Note:** if you also have python 2 installed on your system, you will probably need to run `python3` instead of `python`

### Installing

    python -m pip install florana

### Dependencies

python > 3  
[textract](https://textract.readthedocs.io/en/stable/)
