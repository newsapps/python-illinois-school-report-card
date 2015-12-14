"""
Utilities for naming relational database columns based on the record layout
spreadsheets.

The hope is to create human readable database column names that fit within the
constraints of column names for database engines.
"""
import re

# Name cleaning/shortening functions

def replace_percent_sign(s):
    return re.sub(r'^%( OF){0,1}', 'PCT', s, flags=re.I)

def abbreviate_percent(s):
    return re.sub(r'PERCENT(AGE){0,1}', 'PCT', s, flags=re.I)

def remove_and(s):
    return re.sub(r'\s+AND\s+', ' ', s, flags=re.I)

def remove_for(s):
    return re.sub(r'\s+FOR\s+', ' ', s, flags=re.I)

def remove_yet(s):
    return re.sub(r'\s+YET\s+', ' ', s, flags=re.I)

def remove_composite(s):
    return re.sub(r'\s+COMPOSITE\s+', ' ', s, flags=re.I)

def remove_students(s):
    return re.sub(r'\s+STUDENTS\s+', ' ', s, flags=re.I)

def fix_particially(s):
    return s.replace('PARTICIALLY', 'PARTIALLY')

def shorten_expectations(s):
    return s.replace('EXPECTATIONS', 'EXPECTNS')

def shorten_subregion(s):
    return s.replace('SUBREGION', 'SUBRGN')

def shorten_native_hawaiian(s):
    return s.replace('NATIVE HAWAIIAN AND OTHERS', 'HAWAIIAN')

def number_word_to_numeral(s):
    """
    Naively convert number words to numerals.

    This handle the cases we need, but won't handle all cases.

    For a more robust approach, cosnider one of the strategies mentioned at
    http://stackoverflow.com/questions/493174/is-there-a-way-to-convert-number-words-to-integers-python
    """
    number_words = {
      "ONE": '1',
      "TWO": '2',
      "THREE": '3',
      "FOUR": '4',
      "FIVE": '5',
      "SIX": '6',
      "SEVEN": '7',
      "EIGHT": '8',
      "NINE": '9',
    }

    def replace_number_word(m):
        return " " + number_words[m.group(1)] + " "

    pattern = r'\s+({})\s+'.format("|".join(number_words.keys()))
    return re.sub(pattern, replace_number_word, s)

def apply_filters(s, filters=[]):
    cleaned = s
    for fn in filters:
        cleaned = fn(cleaned)

    return cleaned

