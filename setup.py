from setuptools import setup, find_packages
import os

# PyPI only supports nicely-formatted README files in reStructuredText.
# Newsapps seems to prefer Markdown.  Use a version of the pattern from
# https://coderwall.com/p/qawuyq/use-markdown-readme-s-in-python-modules
# to convert the Markdown README to rst if the pypandoc package is
# present.
try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError, OSError):
    long_description = open('README.md').read()

# Load the version from the version module
exec(open(os.path.join('ilreportcard', 'version.py')).read())

setup(
    name='illinois-school-report-card',
    version=__version__,
    author='Geoff Hing for the Chicago Tribune Dataviz Team',
    author_email='geoffhing@gmail.com',
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    install_requires=[
        'xlrd>=0.9.3',
        'enum34>=1.1.1',
        'SQLAlchemy>=1.0.9',
        'invoke>=0.11.1',
        'psycopg2>=2.6.1',
    ],
    entry_points="",
    tests_require=[
        'nose',
    ],
    test_suite='nose.collector',
    keywords=['Illinois', 'schools', 'education', 'scores', 'testing'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
)
