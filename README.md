python-illinois-school-report-card
==================================

Python package for working with Illinois Board of Education School Report Card data.

Assumptions
-----------

* Python 2.7

For data loading:

* PostgreSQL

Installation
------------

    mkvirtualenv python-illinois-school-report-card
    git clone git@tribune.unfuddle.com:tribune/python-illinois-school-report-card.git
    cd python-illinois-school-report-card
    pip install -e .

Data loading
------------

Download data somewhere.  You'll need to specify a

Create a database:

    createdb school_report_card

Create database tables for assessment data:

    invoke --root ./ilreportcard/ create_assessment_schema --layout=./data/2015\ School\ Report\ Card/RC15_assessment_layout.xlsx --year=2015 --database='postgresql://localhost:5432/school_report_card'

Load assessment data:

    invoke --root ./ilreportcard/ load_assessment_data --year=2015 --layout=./data/2015\ School\ Report\ Card/RC15_assessment_layout.xlsx --data=./data/2015\ School\ Report\ Card/rc15_assessment.txt --flush --database='postgresql://localhost:5432/school_report_card'

Updating for a new year's data
------------------------------

### Create a new schema class

Add a new schema class to `ilreports.schema` and update `ilreports.schema.get_assessment_schema` to return that class.

TODO: Describe how to modify the class to handle different parts.

Add a new loader class to `ilreports.load` and update `ilreports.load.get_assessment_loader` to return that class.

TODO: Describe things to look out for in the new class, but most of the differences should appear in the schema class.


Data export
-----------

### Generate CSVs for print tables

    invoke --root ./ilreportcard/ generate_print_tables --year=2015 --papermap=/Users/ghing/Downloads/PARCC\ -\ schools_districts.csv --papercol=Paper --rcdtscol=RCDTS  --outputdir=./_out/

