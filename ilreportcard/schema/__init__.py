"""Define and create relational database tables based on the record layout"""
from copy import copy
from enum import Enum
import re

from sqlalchemy import (Column as SQAColumn, Table as SQATable, String, Integer,
    Float, Boolean)
import xlrd
from xlrd import XL_CELL_NUMBER

from .column_names import (
    apply_filters,
    replace_number_symbol,
    replace_percent_sign,
    abbreviate_percent,
    remove_and,
    remove_for,
    remove_yet,
    remove_composite,
    fix_averge,
    fix_particially,
    shorten_subregion,
    shorten_average,
    shorten_expectations,
    shorten_physical_education,
    shorten_subregion,
    remove_students,
    shorten_native_hawaiian,
    number_word_to_numeral,
)


class COLUMN_TYPES(Enum):
    """
    Constants for column types in the data

    Reflects what we care about, which is the type of database column to
    create and the Python data type to convert a field.
    """
    INTEGER = 1
    FLOAT = 2
    STRING = 3
    BOOLEAN = 4


def get_column_type(column_type_string):
    """
    Get the enumerated column type based on the column type string in the
    record layout
    """
    column_types = (
        (r'A\d+', COLUMN_TYPES.STRING),
        (r'COMMA\d(\.0){0,1}', COLUMN_TYPES.INTEGER),
        (r'F\d+\.\d+', COLUMN_TYPES.FLOAT),
        (r'DOLLAR\d', COLUMN_TYPES.FLOAT),
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

def default_converter(columndef, value):
    try:
        if columndef.column_type == COLUMN_TYPES.INTEGER:
            if value == '':
                return None
            else:
                try:
                    value = value.replace(',', '')
                except AttributeError:
                    pass

                return int(value)
        elif columndef.column_type == COLUMN_TYPES.FLOAT:
            if value == '':
                return None
            else:
                try:
                    value = value.replace('$', '')
                    value = value.replace(',', '')
                except AttributeError:
                    pass

                return float(value)
        elif columndef.column_type == COLUMN_TYPES.STRING:
            return str(value)
    except ValueError:
        msg = "Could not convert value '{}' to {} for column '{}' (index {})"
        raise ValueError(msg.format(value, columndef.column_type,
            columndef.name, columndef.column_index))

    return value


class Column(object):
    """Data column definition"""
    def __init__(self, column_index, name, column_type, primary_key=False,
            table=None, converter=default_converter):
        self.column_index = column_index
        self.name = name
        self.column_type = column_type
        self.table = table
        self.primary_key = primary_key
        self.converter = converter

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
        return self.converter(self, value)


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
            COLUMN_TYPES.STRING: String,
            COLUMN_TYPES.BOOLEAN: Boolean,
        }

        columns = []

        for columndef in self.columns:
            column = SQAColumn(columndef.name,
                column_type_map[columndef.column_type],
                primary_key=columndef.primary_key)
            columns.append(column)

        return SQATable(self.name, metadata, *columns)


class BaseSchema(object):
    def __init__(self, *args, **kwargs):
        self._tables = []
        self._columns = []

    @property
    def columns(self):
        return self._columns

    @property
    def tables(self):
        return self._tables


class ColumnNaming2015Mixin(object):
    DESCRIPTION_FILTERS = [
        replace_percent_sign,
        replace_number_symbol,
        abbreviate_percent,
        remove_and,
        remove_for,
        remove_yet,
        remove_composite,
        fix_particially,
        fix_averge,
        shorten_expectations,
        shorten_subregion,
        shorten_average,
        shorten_physical_education,
        remove_students,
    ]

    SUBGROUP_SPECIFIER_FILTERS = [
        shorten_native_hawaiian,
        number_word_to_numeral,
    ]


class ReportCardSchema2015(ColumnNaming2015Mixin, BaseSchema):
    name = 'report_card_2015'

    def from_file(self, f):
        # Create the table definition
        table = Table(self.name)
        self._tables.append(table)

        # For every row in the file ...
        workbook = xlrd.open_workbook(file_contents=f.read())
        sheet = workbook.sheet_by_index(0)

        for i in range(sheet.nrows):
            row = sheet.row(i)

            # The first column is not a number, that means it's a heading
            # or a subheading. Ignore it.
            if row[0].ctype != XL_CELL_NUMBER:
                continue

            # Make the column name
            column_name = self.get_column_name(row)

            # Define the column type
            column_type = get_column_type(row[6].value)

            # Determine which columns should be used to create an index
            if row[5].value.strip().startswith("SCHOOL ID"):
                primary_key = True
            else:
                primary_key = False

            # Add the column to a table definition
            columndef = Column(column_index=int(row[0].value) - 1, name=column_name,
                column_type=column_type, primary_key=primary_key)
            table.add_column(columndef)

    @classmethod
    def get_column_name(cls, row):
        # Grab cells needed to make the column name
        subgroup_specifier = str(row[2].value)
        description = row[5].value.strip()
        test = row[1].value

        # Some of the base metadata fields have example values in the
        # description.  We'll just strip those out explicitly.
        # For example:
        # "SCHOOL TYPE CODE (0,1,2,C)" -> school_type_code

        if description.startswith("SCHOOL ID"):
            return 'school_id'

        if description.startswith("SCHOOL TYPE CODE"):
            return 'school_type_code'

        if description.startswith("DISTRICT TYPE CODE"):
            return 'district_type_code'

        if description.startswith("DISTRICT SIZE CODE"):
            return 'district_size_code'

        # Replace/clean individual components of the column name for brevity
        description = apply_filters(description, cls.DESCRIPTION_FILTERS)
        try:
            subgroup_specifier = apply_filters(subgroup_specifier,
                cls.SUBGROUP_SPECIFIER_FILTERS)
        except AttributeError:
            print(subgroup_specifier)
            raise

        bits = [valid_column_name(description)]
        if test != "":
            bits.append(valid_column_name(test))

        if subgroup_specifier != "":
            bits.append(valid_column_name(subgroup_specifier))

        return "_".join(bits)


def get_report_card_schema(year):
    """Get a schema class for a particular year's data"""
    if year == 2015:
        return ReportCardSchema2015()

    raise ValueError("No schema found for {}".format(year))


class AssessmentSchema2015(ColumnNaming2015Mixin, BaseSchema):
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
        subgroup_specifier = row[2].value
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
        description = apply_filters(description, cls.DESCRIPTION_FILTERS)

        # Replace some characters in the various components of the subgroup_specifier column
        subgroup_specifier = apply_filters(subgroup_specifier, cls.SUBGROUP_SPECIFIER_FILTERS)

        # This particular case, e.g.
        # "# of LEP students who have attended schools in the U.S. for less than 12 months and are not assessed on the State's ELA test (SCHOOL)"
        # makes super long column names.
        pattern = (r'# of.*\(([A-Z]+)\)')
        m = re.match(pattern, row[5].value)
        if m is not None:
            column_name = 'lep_1st_year_in_us_' + m.group(1).lower()
        else:
            # In general, we can just slugify the bits and concatenate them
            # together
            bits = [valid_column_name(description)]

            if test.strip():
                bits.append(slugify(test))

            if subgroup_specifier.strip():
                bits.append(slugify(subgroup_specifier))

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
        # 2: subgroup_specifier (e.g. ALL, MALE, FEMALE, WHITE)
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


def get_assessment_schema(year):
    """Get a schema class for a particular year's data"""
    if year == 2015:
        return AssessmentSchema2015()

    raise ValueError("No schema found for {}".format(year))


class PARCCParticipationSchema2015(BaseSchema):
    """
    Schema for data from PARCC participation spreadsheet

    This was provided from Diane Rado as a separate file as the data in
    the report card data dump reflected aggregates of the PARCC and DLM
    participation numbers.

    """
    name = 'parcc_participation_2015'

    def __init__(self):
        self._tables = []

        table = Table(name='parcc_participation_2015')
        self._tables.append(table)

        self._columns = [
            Column(column_index=0, name="rcdts",
                column_type=COLUMN_TYPES.STRING, primary_key=True),
            Column(column_index=1, name="county",
                column_type=COLUMN_TYPES.STRING),
            Column(column_index=2, name="district_number",
                column_type=COLUMN_TYPES.STRING),
            Column(column_index=3, name="district_name_school_name",
                column_type=COLUMN_TYPES.STRING),
            Column(column_index=4, name="city",
                column_type=COLUMN_TYPES.STRING),
            Column(column_index=5, name="tested_enrollment_ela",
                column_type=COLUMN_TYPES.INTEGER),
            Column(column_index=6, name="tested_enrollment_masked_ela",
                column_type=COLUMN_TYPES.BOOLEAN),
            Column(column_index=7, name="tested_ela",
                column_type=COLUMN_TYPES.INTEGER),
            Column(column_index=8, name="absent_ela",
                column_type=COLUMN_TYPES.INTEGER),
            Column(column_index=9, name="refusal_ela",
                column_type=COLUMN_TYPES.INTEGER),
            Column(column_index=10, name="other_ela",
                column_type=COLUMN_TYPES.INTEGER),
            Column(column_index=11, name="invalid_score_ela",
                column_type=COLUMN_TYPES.INTEGER),
            Column(column_index=12, name="tested_enrollment_math",
                column_type=COLUMN_TYPES.INTEGER),
            Column(column_index=13, name="tested_enrollment_masked_math",
                column_type=COLUMN_TYPES.BOOLEAN),
            Column(column_index=14, name="tested_math",
                column_type=COLUMN_TYPES.INTEGER),
            Column(column_index=15, name="absent_math",
                column_type=COLUMN_TYPES.INTEGER),
            Column(column_index=16, name="refusal_math",
                column_type=COLUMN_TYPES.INTEGER),
            Column(column_index=17, name="other_math",
                column_type=COLUMN_TYPES.INTEGER),
            Column(column_index=18, name="invalid_score_math",
                column_type=COLUMN_TYPES.INTEGER),
        ]

        for column in self._columns:
            table.add_column(column)


def get_parcc_participation_schema(year):
    """Get a schema class for a particular year's data"""

    if year == 2015:
        return PARCCParticipationSchema2015()

    raise ValueError("No schema found for {}".format(year))
