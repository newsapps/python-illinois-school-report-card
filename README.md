python-illinois-school-report-card
==================================

Python package for working with Illinois Board of Education School Report Card data.

This is an attempt to make a reproducible data loading and analysis pipeline as well
as provide an interface to the data that can be used both for reporting and to
drive news applications.

Previously, this data was loaded into MongoDB.  While this allowed us to use the long strings in the layout spreadsheet as the field names, and probably avoids hitting the column limits on tables in a RDBMS, a NoSQL store doesn't seem like the best format for reporting.

This was written for the 2015 release.  We'll definitely want to revisit this and refactor the code to minimize the amount of code that has to be written from year-to-year. 2015's data was a bit strange since the assessment data and other pieces of the report card were released at different times and in different files.  This might not be the case in the future. 

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
    pip install -e --process-dependency-links .

Getting the data
----------------

The data is available from an SFTP server:

sftp://RC15:R3port;15@206.166.105.117

### Included data

A few files are included in the data directory as they were emailed to reporters and not published as part of the report card data dump.  Including them in this repo avoids the files getting lost on our hard drives or in our inboxes.

* PARCCParticipation2015.xlsx - 2015 PARCC participation numbers.  The participation numbers in the report card dump includes both PARCC and DLM.

Data loading
------------

Create a database:

    createdb school_report_card

Create database tables for assessment data:

    invoke --root ./ilreportcard/ create_assessment_schema --layout=./data/2015\ School\ Report\ Card/RC15_assessment_layout.xlsx --year=2015 --database='postgresql://localhost:5432/school_report_card'

Load assessment data:

    invoke --root ./ilreportcard/ load_assessment_data --year=2015 --layout=./data/2015\ School\ Report\ Card/RC15_assessment_layout.xlsx --data=./data/2015\ School\ Report\ Card/rc15_assessment.txt --flush --database='postgresql://localhost:5432/school_report_card'

Create the database table for the PARCC participation data:

    invoke --root=./ilreportcard/ create_parcc_participation_schema --year=2015 --database='postgresql://localhost:5432/school_report_card'

Load PARCC participation data:

    invoke --root=./ilreportcard/ load_parcc_participation_data --year=2015 --data=./data/PARCCParticipation2015.xlsx --flush --database='postgresql://localhost:5432/school_report_card'

Create the database table for the report card data:

    invoke --root ./ilreportcard/ create_report_card_schema --layout=./data/2015\ School\ Report\ Card/RC15_layout.xlsx --year=2015 --database='postgresql://localhost:5432/school_report_card'

Load the report card data:

    invoke --root ./ilreportcard/ load_report_card_data --layout=./data/2015\ School\ Report\ Card/RC15_layout.xlsx --data=./data/2015\ School\ Report\ Card/rc15.txt --year=2015 --flus --database='postgresql://localhost:5432/school_report_card'h
    


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

