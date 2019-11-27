import setuptools

with open('README.md', 'r') as fn:
    long_description = fn.read()

setuptools.setup(
    name='florana',
    version='1.0.3',
    description='Extract data from Flora of North America',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/josiest/Flora-Data-Extraction/',
    author='Josie Thompson',
    author_email='josiest@uw.edu',
    license='MIT',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Intended Audience :: Science/Research',
    ],
    packages=setuptools.find_packages(),
    python_requires='>=3',
    package_data={'': ['*.txt', '*.json']},
)
