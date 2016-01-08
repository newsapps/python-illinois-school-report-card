python-illinois-school-report-card
==================================

Python package for working with Illinois Board of Education School Report Card data, Chicago Tribune-style.

This is an attempt to make a reproducible data loading and analysis pipeline as well
as provide an interface to the data that can be used both for reporting and to
drive news applications.  In particular, it was used for [2015 Illinois PARCC scores](http://apps.chicagotribune.com/news/local/parcc-scores-2015/).

Previously, this data was loaded into MongoDB for use by http://schools.chicagotribune.com.  While this allowed us to use the long strings in the layout spreadsheet as the field names, and probably avoids hitting the column limits on tables in a RDBMS, a NoSQL store doesn't seem like the best format for reporting.

This was written for the 2015 release.  We'll definitely want to revisit this and refactor the code to minimize the amount of code that has to be written from year-to-year. 2015's data was a bit strange since the assessment data and other pieces of the report card were released at different times and in different files.  This might not be the case in the future. 

Design decisions
----------------

These might not be great decisions, but they're decisions.

### Get the data into a database as quickly as possible

Reporters need to be able to work with the data quickly and can't wait for us to do fancy cleaning/normalizing.

### Stick closely with the structure of the raw data 

The main reason for this is to offer the additional power of a relational database while giving a similar view to the one that a reporter is used to seeing if they load the raw data straight into Excel.  This means that there's considerable data that is replecated.  This isn't ideal, but this year it felt like normalizing the data should be a separate, next step.  The loader does split the data into multiple tables to work around the limitations on the number of columns imposed by PostgreSQL.

###  SQL > ORM

Though the query code will have more repeated bits, SQL is the most commonly spoken language between reporters and devs with different backgrounds and skillsets.  Deal with it.

### Things change

Anticipate changes in schema and in which files contain certain data.  For example, in 2015, the test scores were shipped later and in a separate file from the rest of the report card data.

Make separate classes to load each year's data and for each year's schema to try to abstract differences.  We'll see how well this works next year.

Future refinements
------------------ 

* Column names that include the column index.  While the column names are fairly readable, some of them are very similar.  Someone writing their own queries will likely be looking at the record layout spreadsheet which clearly indicates column numbers. 
* Tasks to fetch the data

Other work
----------

[Datamade's](https://github.com/datamade/) [school-report-cards](https://github.com/datamade/school-report-cards) is another project working with the same data.  It appears to load data from multiple years and tries to normalize the data in order to do longitudinal analysis.


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

The 2015 data is available from an FTP server at: ftp://ftp.isbe.net/SchoolReportCard/2015%20School%20Report%20Card/

Prior years' data is available at ftp://ftp.isbe.net/SchoolReportCard/ 

Prior to the public release, the data was available on an embargoed bases to news organizations via an SFTP server.

Data loading
------------

Create a database:

    createdb school_report_card

Create database tables for assessment data:

    invoke create_assessment_schema --layout=./data/2015\ School\ Report\ Card/RC15_assessment_layout.xlsx --year=2015 --database='postgresql://localhost:5432/school_report_card'

Load assessment data:

    invoke load_assessment_data --year=2015 --layout=./data/2015\ School\ Report\ Card/RC15_assessment_layout.xlsx --data=./data/2015\ School\ Report\ Card/rc15_assessment.txt --flush --database='postgresql://localhost:5432/school_report_card'

Create the database table for the PARCC participation data:

    invoke --root=./ilreportcard/ create_parcc_participation_schema --year=2015 --database='postgresql://localhost:5432/school_report_card'

Load PARCC participation data:

    invoke --root=./ilreportcard/ load_parcc_participation_data --year=2015 --data=./data/2015_PARCC_participation.xlsx --flush --database='postgresql://localhost:5432/school_report_card'

Create the database table for the report card data:

    invoke create_report_card_schema --layout=./data/2015\ School\ Report\ Card/RC15_layout.xlsx --year=2015 --database='postgresql://localhost:5432/school_report_card'

Load the report card data:

    invoke load_report_card_data --layout=./data/2015\ School\ Report\ Card/RC15_layout.xlsx --data=./data/2015\ School\ Report\ Card/rc15.txt --year=2015 --flus --database='postgresql://localhost:5432/school_report_card'h
    
Updating for a new year's data
------------------------------

### Create a new schema class

Add a new schema class to `ilreports.schema` and update `ilreports.schema.get_assessment_schema` to return that class.

TODO: Describe how to modify the class to handle different parts.

Add a new loader class to `ilreports.load` and update `ilreports.load.get_assessment_loader` to return that class.

TODO: Describe things to look out for in the new class, but most of the differences should appear in the schema class.

Contributors
------------

* Geoff Hing <geoffhing@gmail.com>
