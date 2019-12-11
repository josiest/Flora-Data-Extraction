# Flora Data Extraction Project

This script is designed to extract data from pdf files of genera from the book *Flora of North America*. It creates csv files whose names match the PDF files given to the script as arguments. The csv files have the format

> "Species name", "Location where the species appears"

and

> "Species name", "Classifiers (if any)"

The easiest way to run the script is to move to a folder where the only pdf files are genera files from *Flora of North America* and enter:

    python -m florana.extract -A -o data.csv

The script will then run on every pdf file in the directory and create a file called 'data.csv' of all the locations it can find, as well as a file 'data-classifiers.csv'. If the script couldn't find locations for some species, detailed information will be included in 'error.log'.

#### Note: python 2
> If you also have python 2 installed on your system, you will probably need to run `python3` instead of `python`

### Installing

    python -m pip install florana

#### Note: Windows Users
> If you're running Windows, you'll likely need to install [poppler](https://blog.alivate.com.au/poppler-windows/). You'll need to extract the latest binary from the link provided and add its bin folder to your PATH environment variable. *i.e.* If `C:\path\to\poppler` is the directory where you extracted poppler, then you'll need to add `C:\path\to\poppler\bin` to your PATH environment variable.

### Dependencies

- python > 3  
- [textract](https://textract.readthedocs.io/en/stable/)
