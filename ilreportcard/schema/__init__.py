from copy import copy
from enum import Enum
import re

from sqlalchemy import Column as SQAColumn, Table as SQATable, String, Integer, Float
import xlrd
from xlrd import XL_CELL_NUMBER

class COLUMN_TYPES(Enum):
    INTEGER = 1
    FLOAT = 2
    STRING = 3

def get_column_type(column_type_string):
    column_types = (
        (r'A\d+', COLUMN_TYPES.STRING),
        (r'COMMA\d\.0', COLUMN_TYPES.INTEGER),
        (r'F\d+\.\d+', COLUMN_TYPES.FLOAT),
    )

    for pattern, column_type in column_types:
        if re.match(pattern, column_type_string) is not None:
            return column_type

    raise ValueError("Could not determine column type for '{}'".format(
        column_type_string))


def slugify(s):    
    s_valid = s.strip()

    # Replace '-' with '_'
    s_valid = re.sub(r'\s*-\s*', '_', s_valid)

    # Remove invalid characters
    s_valid = re.sub(r'[^a-zA-Z0-9\$_ ]', '', s_valid)

    # Replace spaces with underscores
    s_valid = re.sub(r'\s+', '_', s_valid)

    # Make the whole thing lowercase
    s_valid = s_valid.lower()

    # Remove any leading or tailing '_'s added by other transforms
    s_valid = s_valid.strip('_')

    return s_valid


def valid_column_name(s):
    "Convert a string to a valid SQL column name"
    s_valid = s.encode('ascii', errors='replace')

    s_valid = s.strip()

    s_valid = re.sub(r'^\d+ ', '', s_valid)

    return slugify(s_valid)

    return s_valid


class Column(object):
    def __init__(self, column_index, name, column_type, primary_key=False, table=None):
        self.column_index = column_index
        self.name = name
        self.column_type = column_type
        self.table = table
        self.primary_key = primary_key

    def __repr__(self):
        return 'Column(column_index={}, name="{}", column_type={}, primary_key={})'.format(
            self.column_index,
            self.name,
            self.column_type,
            self.primary_key
        )

    def set_table(self, table):
        self.table = table

    def __copy__(self):
        return type(self)(
            column_index=self.column_index,
            name=self.name,
            column_type=self.column_type,
            primary_key=self.primary_key,
            table=self.table,
        )

    def convert_value(self, value):
        try:
            if self.column_type == COLUMN_TYPES.INTEGER:
                if value == '':
                    return None
                else:
                    return int(value.replace(',', ''))
            elif self.column_type == COLUMN_TYPES.FLOAT:
                if value == '':
                    return None
                else:
                    return float(value)
            elif self.column_type == COLUMN_TYPES.STRING:
                return str(value)
        except ValueError:
            print('"{}"'.format(value))
            print(value == "")
            raise

        return value
        

class Table(object):
    def __init__(self, name):
        self.name = name
        self._columns = []

    def __repr__(self):
        return 'Table(name="{}")'.format(self.name)

    def add_column(self, column):
        column.set_table(self)
        self._columns.append(column)

    @property
    def columns(self):
        return self._columns

    def as_sqlalchemy(self, metadata):
        column_type_map = {
            COLUMN_TYPES.INTEGER: Integer,
            COLUMN_TYPES.FLOAT: Float,
            COLUMN_TYPES.STRING: String
        }

        columns = []

        for columndef in self.columns:
            column = SQAColumn(columndef.name,
                column_type_map[columndef.column_type],
                primary_key=columndef.primary_key)
            columns.append(column)

        return SQATable(self.name, metadata, *columns)


class AssessmentSchema2015(object):
    name = 'assessment_2015'

    # Headings and subheadings in the record layout file. 
    # HACK: Hardcoded values.  There doesn't seem to be
    # any better way to detect these based on the file alone
    HEADINGS = set([
       "ILLINOIS STATE ASSESSMENT INFORMATION",
       "PARTNERSHIP FOR ASSESSMENT OF READINESS FOR COLLEGE AND CAREERS (PARCC)",
       "DYNAMIC LEARNING MAPS ALTERNATE ASSESSMENT (DLM)",
       "ACCOUNTABILITY"
    ])

    SUBHEADINGS = set([
        "TOTAL ENROLLMENT AND PERCENT NOT TESTED IN ENGLISH LANGUAGE ARTS/LITERACY (ELA)",
        "TOTAL ENROLLMENT AND PERCENT NOT TESTED IN MATH",
        "OVERALL ACHIEVEMENT PERFORMANCE (PARCC/DLM)",
        "OVERALL ACHIEVEMENT BY 5 PERFORMANCE LEVELS (PARCC/DLM)",
        "GRADE 3",
        "GRADE 4",
        "GRADE 5",
        "GRADE 6",
        "GRADE 7",
        "GRADE 8",
        "GRADE 9-12 HIGH SCHOOL SUJECTS COMBINED",
        "HIGH SCHOOL - ENGLISH LANGUAGE ARTS/LITERACY (ELA)",
        "HIGH SCHOOL - MATH",
        "ALGEBRA I, ALGEBRA II, AND GEOMETRY (ALG1, ALG II, GEO)",
        "MATHEMATICS I, II, AND III (MATH1, MATH II, MATH III)",
        "GRADE 11",
        "SCHOOL",
        "DISTRICT",
        "STATE",
    ])

    SCHOOLS_TABLE_NAME = "schools"

    SECTION_TO_TABLE = {
        (None, None): SCHOOLS_TABLE_NAME, 
        ("ILLINOIS STATE ASSESSMENT INFORMATION",
         "TOTAL ENROLLMENT AND PERCENT NOT TESTED IN ENGLISH LANGUAGE ARTS/LITERACY (ELA)"): "participation",
        ("ILLINOIS STATE ASSESSMENT INFORMATION",
         "OVERALL ACHIEVEMENT PERFORMANCE (PARCC/DLM)"): "overall_achievement_parcc_dlm_performance",
        ("ILLINOIS STATE ASSESSMENT INFORMATION",
         "OVERALL ACHIEVEMENT BY 5 PERFORMANCE LEVELS (PARCC/DLM)"): "overall_achievement_parcc_dlm_levels",
        ("PARTNERSHIP FOR ASSESSMENT OF READINESS FOR COLLEGE AND CAREERS (PARCC)",
         "GRADE 3"): "parcc_grade_3",
        ("PARTNERSHIP FOR ASSESSMENT OF READINESS FOR COLLEGE AND CAREERS (PARCC)",
         "GRADE 4"): "parcc_grade_4",
        ("PARTNERSHIP FOR ASSESSMENT OF READINESS FOR COLLEGE AND CAREERS (PARCC)",
         "GRADE 5"): "parcc_grade_5",
        ("PARTNERSHIP FOR ASSESSMENT OF READINESS FOR COLLEGE AND CAREERS (PARCC)",
         "GRADE 6"): "parcc_grade_6",
        ("PARTNERSHIP FOR ASSESSMENT OF READINESS FOR COLLEGE AND CAREERS (PARCC)",
         "GRADE 7"): "parcc_grade_7",
        ("PARTNERSHIP FOR ASSESSMENT OF READINESS FOR COLLEGE AND CAREERS (PARCC)",
         "GRADE 8"): "parcc_grade_8",
        ("PARTNERSHIP FOR ASSESSMENT OF READINESS FOR COLLEGE AND CAREERS (PARCC)",
         "GRADE 9-12 HIGH SCHOOL SUJECTS COMBINED"): "parcc_high_school_combined",
        ("PARTNERSHIP FOR ASSESSMENT OF READINESS FOR COLLEGE AND CAREERS (PARCC)",
         "HIGH SCHOOL - ENGLISH LANGUAGE ARTS/LITERACY (ELA)"): "parcc_high_school_ela",
        ("PARTNERSHIP FOR ASSESSMENT OF READINESS FOR COLLEGE AND CAREERS (PARCC)",
         "ALGEBRA I, ALGEBRA II, AND GEOMETRY (ALG1, ALG II, GEO)"): "parcc_high_school_math_algebra_geometry",
        ("PARTNERSHIP FOR ASSESSMENT OF READINESS FOR COLLEGE AND CAREERS (PARCC)",
         "MATHEMATICS I, II, AND III (MATH1, MATH II, MATH III)"): "parcc_high_school_math_i_ii_iii",
        ("DYNAMIC LEARNING MAPS ALTERNATE ASSESSMENT (DLM)", "GRADE 3"): "dlm_grade_3",
        ("DYNAMIC LEARNING MAPS ALTERNATE ASSESSMENT (DLM)", "GRADE 4"): "dlm_grade_4",
        ("DYNAMIC LEARNING MAPS ALTERNATE ASSESSMENT (DLM)", "GRADE 5"): "dlm_grade_5",
        ("DYNAMIC LEARNING MAPS ALTERNATE ASSESSMENT (DLM)", "GRADE 6"): "dlm_grade_6",
        ("DYNAMIC LEARNING MAPS ALTERNATE ASSESSMENT (DLM)", "GRADE 7"): "dlm_grade_7",
        ("DYNAMIC LEARNING MAPS ALTERNATE ASSESSMENT (DLM)", "GRADE 8"): "dlm_grade_8",
        ("DYNAMIC LEARNING MAPS ALTERNATE ASSESSMENT (DLM)", "GRADE 11"): "dlm_high_school",
        ("ACCOUNTABILITY", "SCHOOL"): "accountability"
    }

    SCHOOL_ID_COLUMN_NAME = "school_id"

    def __init__(self, *args, **kwargs):
        self._tables = []
        self._columns = []

    @classmethod
    def get_column_name(cls, row):    
        description = row[5].value
        modifier = row[2].value
        test = row[1].value

        if description.startswith("SCHOOL ID"):
            return cls.SCHOOL_ID_COLUMN_NAME 

        if description.startswith("SCHOOL TYPE CODE"):
            return "school_type_code"

        # Replace some characters in the various components of the column
        # name to make them shorter or using alphanumeric characters
        description = re.sub(r'^%( OF){0,1}', 'PCT', description)
        description = description.replace('PERCENTAGE OF', 'PCT')
        description = description.replace('AND', '')
        description = description.replace('and', '')
        description = description.replace('FOR', '')
        description = description.replace('PERCENT OF', 'PCT')
        description = description.replace('YET', '')
        # Composite also shows up in modifier, so we can get rid of it
        # in description
        description = description.replace('COMPOSITE', '')
        description = description.replace('PARTICIALLY', 'PARTIALLY')
        description = description.replace('EXPECTATIONS', 'EXPECTNS')
        description = description.replace('SUBREGION', 'SUBRGN')
        description = description.replace('STUDENTS', "")

        modifier = modifier.replace('NATIVE HAWAIIAN AND OTHERS',
            'HAWAIIAN')
        modifier = modifier.replace('TWO', '2')

        # This particular case makes super long column names 
        pattern = (r'# of.*\(([A-Z]+)\)')
        m = re.match(pattern, description)
        if m is not None:
            column_name = 'lep_1st_year_in_us_' + m.group(1).lower()
        else:    
            bits = [valid_column_name(description)]

            if test.strip():
                bits.append(slugify(test))

            if modifier.strip():
                bits.append(slugify(modifier))

            column_name = '_'.join(bits)    

        assert len(column_name) <= 64, "'{}' is too long at {} characters".format(
                column_name, len(column_name))

        return column_name


    def from_file(self, f):
        """Load schema from a file-like object"""
        # Layout:
        #
        # 0: field number
        # 1: test name (e.g. ALL TESTS, PARCC, DLM) 
        # 2: modifier (e.g. ALL, MALE, FEMALE, WHITE)
        # 3: character range (e.g. 120-125)
        # 4: width
        # 5: description
        # 6: type
        # 7: start index
        # 8: end index
        #
        # Some rows act as headings, which can be identified when the first
        # column is not a number
        workbook = xlrd.open_workbook(file_contents=f.read())
        sheet = workbook.sheet_by_index(0)

        column_index = 0
        table = None
        heading = None
        subheading = None
        school_id_column = None
        table = Table(self.name + "_" + self.SCHOOLS_TABLE_NAME)

        for i in range(sheet.nrows):
            row = sheet.row(i)
            # The first column is not a number, that means it's a heading
            # or a subheading
            if row[0].ctype != XL_CELL_NUMBER:
                cell_value = row[0].value.strip()
                if cell_value in self.HEADINGS:
                    heading = cell_value 
                    subheading = None

                if cell_value in self.SUBHEADINGS:
                    subheading = cell_value 

                try:
                    table_name = self.SECTION_TO_TABLE[(heading, subheading)]
                    self._tables.append(table)
                    table = Table(self.name + '_' + table_name) 

                    if table_name != self.SCHOOLS_TABLE_NAME:
                        table.add_column(copy(school_id_column))

                except KeyError:
                    pass
                
                continue
            
            column_name = self.get_column_name(row)
               
            col = Column(
               column_index=column_index,
               name=column_name,
               column_type=get_column_type(row[6].value)
            )

            try:
                table.add_column(col)
            except AttributeError:
                print(row)
                raise
            self._columns.append(col)

            if column_name == self.SCHOOL_ID_COLUMN_NAME:
                school_id_column = col

            column_index += 1


    @property
    def columns(self):
        return self._columns

    @property
    def tables(self):
        return self._tables


def get_assessment_schema(year):
    if year == 2015:
        return AssessmentSchema2015()

    raise ValueError("No schema found for {}".format(year))
