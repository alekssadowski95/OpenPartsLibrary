from pathlib import Path

from setuptools import find_packages, setup


this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name='OpenPartsLibrary',
    version='0.1.15',
    description='Python library for creating a database of hardware components for manufacturing',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/alekssadowski95/OpenPartsLibrary',
    author='Aleksander Sadowski',
    author_email='aleksander.sadowski@alsado.de',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'openpartslibrary': ['sample/**/*', 'images/*', 'export/*'],
        'openpartslibrary_flask': ['templates/**/*', 'static/**/*', 'settings.json'],
    },
    install_requires=[
        'sqlalchemy',
        'pandas',
        'openpyxl',
        'odfpy',
        'networkx',
        'matplotlib',
        'pywebview',
        'tabulate',
        'flask-cors',
        'Flask-WTF',
        'WTForms',
        'Flask-Login',
        'email_validator',
    ],
    python_requires='>=3.10',

    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',  
        'Programming Language :: Python :: 3',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
    ],
)
