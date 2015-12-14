import unittest

from ilreportcard.schema.column_names import number_word_to_numeral

class ColumnNamesTestCase(unittest.TestCase):
    def test_number_word_to_numeral(self):
        self.assertEqual(number_word_to_numeral('% TWO OR MORE RACES TEACHER - DISTRICT'),
            '% 2 OR MORE RACES TEACHER - DISTRICT')
       
