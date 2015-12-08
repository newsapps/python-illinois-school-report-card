"""Define and create relational database tables based on the record layout"""
from copy import copy
from enum import Enum
import re

from sqlalchemy import Column as SQAColumn, Table as SQATable, String, Integer, Float
import xlrd
from xlrd import XL_CELL_NUMBER

class COLUMN_TYPES(Enum):
    """
    Constants for column types in the data
    
    Reflects what we care about, which is the type of database column to 
    create and the Python data type to convert a field.
    """
    INTEGER = 1
    FLOAT = 2
    STRING = 3


def get_column_type(column_type_string):
    """
    Get the enumerated column type based on the column type string in the
    record layout
    """
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
    """Convert a string to a valid PostgreSQL column name"""
    s_valid = s.encode('ascii', errors='replace')

    s_valid = s.strip()

    s_valid = re.sub(r'^\d+ ', '', s_valid)

    return slugify(s_valid)


class Column(object):
    """Data column definition"""
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
    """Data table representation"""
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
        """
        Get an SQLAlchemy Table instance for this table definition

        See
        http://docs.sqlalchemy.org/en/latest/core/metadata.html#accessing-tables-and-columns

        """
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
    """Column and table definitions for the 2015 report card assessment data"""

    # Schema name.  This will also be used to prefix tables when created
    # in the database.  We decided to create separate tables for each year
    # rather than trying to normalize the data into one table, though that
    # might be possible in the future once we see a few years worth of data
    name = 'assessment_2015'

    # Headings and subheadings in the record layout file. 

    # These will be used to break columns into separate tables in a way that
    # reflects the way the data is organized instead of along arbitrary numeric
    # breaks.
    
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

    # Table name to hold basic metadata about schools (RCDTS id, name, etc) 
    SCHOOLS_TABLE_NAME = "schools"

    # Map between headings and table names
    #
    # These will be used to determine which table to assign columns to as we
    # iterate through the column definitions in the record layout spreadsheet
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

    # The school RCDTS id is the primary key in the dataset.  Instead of using
    # the auto-generated name based on the description in the record layout,
    # use something explicit and clear.
    SCHOOL_ID_COLUMN_NAME = "school_id"

    def __init__(self, *args, **kwargs):
        self._tables = []
        self._columns = []

    @classmethod
    def get_column_name(cls, row):    
        """
        Get a valid database column name
        
        Get a valid database column name based on a row in the record layout
        spreadsheet. It rougly reflects the column description in the 
        record layout.
        
        """
        # TODO: Should we include the column number from the record layout as
        # part of the column name?  It would make the names uglier, but maybe
        # easier to differentiate between columns and build queries when 
        # looking at the record layout.

        # We'll build the column name based on three pieces of information in
        # the record layout

        # This will be something like "TOTAL SCHOOL ENROLLMENT IN ELA FOR GRADE 3-8 AND HS"
        description = row[5].value
        # This will be something like "LOW INCOME". It usaully reflects a
        # demographic
        modifier = row[2].value
        # This will be something like "PARCC"
        test = row[1].value

        # Always use our canonical column name for the primary key
        if description.startswith("SCHOOL ID"):
            return cls.SCHOOL_ID_COLUMN_NAME 

        # Use a clear, simple name for the school type code as well
        if description.startswith("SCHOOL TYPE CODE"):
            return "school_type_code"

        # Much of the rest of this code is to try to shorten the value
        # because just slugifying/concatinating the bits creates column
        # names that exceed the maximum length allowed by PostgreSQL

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

        # This particular case, e.g.
        # "# of LEP students who have attended schools in the U.S. for less than 12 months and are not assessed on the State's ELA test (SCHOOL)"
        # makes super long column names. 
        pattern = (r'# of.*\(([A-Z]+)\)')
        m = re.match(pattern, description)
        if m is not None:
            column_name = 'lep_1st_year_in_us_' + m.group(1).lower()
        else:    
            # In general, we can just slugify the bits and concatenate them
            # together
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
        """
        Load schema from a file-like object
        
        Args:

            f: File-like object containing a Microsoft Excel spreadsheet
               describing the record layout of the assessment data.

        """
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
        # The first few columns are metadata for the school itself rather than
        # anything related to assesment
        table = Table(self.name + "_" + self.SCHOOLS_TABLE_NAME)

        for i in range(sheet.nrows):
            row = sheet.row(i)
            # The first column is not a number, that means it's a heading
            # or a subheading
            if row[0].ctype != XL_CELL_NUMBER:
                cell_value = row[0].value.strip()

                if cell_value in self.HEADINGS:
                    # It's a top-level heading.  Save it, and clear out the
                    # previous subheading
                    heading = cell_value 
                    subheading = None

                if cell_value in self.SUBHEADINGS:
                    subheading = cell_value 

                try:
                    # Look up the table name for the given heading,
                    # subheading combination
                    table_name = self.SECTION_TO_TABLE[(heading, subheading)]
                    # Add the current table to the schema's list of tables
                    self._tables.append(table)
                    # And construct a new table
                    table = Table(self.name + '_' + table_name) 

                    if table_name != self.SCHOOLS_TABLE_NAME:
                        table.add_column(copy(school_id_column))

                except KeyError:
                    # Items under this subheading are just part of the current
                    # table
                    pass
                
                # This is just a heading, so there's no further processing
                # of a column definition needed.  Keep going.
                continue
          
            column_name = self.get_column_name(row)
               
            col = Column(
               column_index=column_index,
               name=column_name,
               column_type=get_column_type(row[6].value)
            )

            # Add this column to the tables list of columns
            # and an overall list of columns
            table.add_column(col)
            self._columns.append(col)

            # TODO: Should we build a lookup table of columns based on column
            # descriptions or indices in the record layout? 

            if column_name == self.SCHOOL_ID_COLUMN_NAME:
                school_id_column = col

            column_index += 1

        # Add the last discovered table to the schema's list
        # of tables
        self._tables.append(table)

    @property
    def columns(self):
        return self._columns

    @property
    def tables(self):
        return self._tables


def get_assessment_schema(year):
    """Get a schema class for a particular year's data"""
    if year == 2015:
        return AssessmentSchema2015()

    raise ValueError("No schema found for {}".format(year))
