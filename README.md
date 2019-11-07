# Flora Data Extraction Project

This script is designed to extract data from pdf files of genera from the book *Flora of North America*. It creates csv files whose names match the PDF files given to the script as arguments. The csv files have the format

> "Species name", "Identifiers", "Locations where the species appears"

The easiest way to run the script is to move to a folder where the only pdf files are genera files from *Flora of North America* and write:

    python3 extract.py *.pdf

The script will then run on every pdf file in the directory and create a csv for each pdf.

### Dependencies

python > 3  
textract
