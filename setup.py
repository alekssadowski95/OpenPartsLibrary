from setuptools import setup, find_packages


# read the contents of your README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='OpenPartsLibrary',
    version='0.1.12',    
    description='Python library for creating a database of hardware components for manufacturing',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/alekssadowski95/OpenPartsLibrary',
    author='Aleksander Sadowski',
    author_email='aleksander.sadowski@alsado.de',
    license='MIT',
    packages=find_packages(),
    install_requires=['sqlalchemy', 'datetime', 'pandas', 'openpyxl'],

    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',  
        'Programming Language :: Python :: 3'
    ],
)
