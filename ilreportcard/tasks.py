"""
Command line tasks for working with report card data
"""
import csv
import logging
import os

from invoke import task

from sqlalchemy import (create_engine, MetaData)

from ilreportcard.schema import get_assessment_schema
from ilreportcard.load import get_assessment_loader
from ilreportcard.query import summary_query 

logging.basicConfig(level=logging.INFO)

DEFAULT_DATABASE = "postgresql://localhost:5432/school_report_card"

# TODO: Is invoke the best task runner to use? I like that it has
# dependencies between tasks, but its discovery mechanism for the
# tasks module is kind of annoying.

# TODO: Document arguments to these task functions.  For now, see
# the examples in the README

@task
def create_assessment_schema(year, layout, database=DEFAULT_DATABASE):
    with open(layout, 'rb') as f:
        schema = get_assessment_schema(int(year))
        schema.from_file(f)

        engine = create_engine(database)
        metadata = MetaData()

        for tabledef in schema.tables:
            table = tabledef.as_sqlalchemy(metadata)
            logging.info("Creating database table {}".format(tabledef.name))
            table.create(engine, checkfirst=True)


@task
def load_assessment_data(year, layout, data,
        flush=False,
        database=DEFAULT_DATABASE):
    with open(layout, 'rb') as f:
        schema = get_assessment_schema(int(year))
        schema.from_file(f)

    with open(data, 'r') as f:
        engine = create_engine(database)
        metadata = MetaData()
        with engine.connect() as connection:
            loader = get_assessment_loader(int(year))
            loader.set_schema(schema)
            loader.load(f, metadata, connection, flush)


def _district_result(result):
    """Remove school fields from a result row, leaving only the district ones"""
    out = result.copy()
    for k in result.keys():
        if 'school' in k:
            del out[k]

    return out


# TODO: Document this
@task
def generate_print_tables(year, papermap, papercol, rcdtscol,
        outputdir=os.getcwd(), outputfilename='print_tables.csv', database=DEFAULT_DATABASE):
    """Generate CSVs for school/district test information in print"""
    filename_prefix = outputfilename.split('.')[0]
    filename_suffix = '.'.join(outputfilename.split('.')[1:])

    fieldnames = [
      'school_name',
      'district_name',
      'school_pct_proficiency_in_ela_parcc_2015_ela',
      'total_school_enrollment_in_ela_grade_3_8_hs_all',
      'pct_not_taking_ela_tests_school_all',
      'school_pct_proficiency_in_math_parcc_2015_math',
      'total_school_enrollment_in_math_grade_3_8_hs_all',
      'pct_not_taking_math_tests_school_all',
      'district_pct_proficiency_in_ela_parcc_2015_ela',
      'total_district_enrollment_in_ela_grade_3_8_hs_all',
      'pct_not_taking_ela_tests_district_all',
      'district_pct_proficiency_in_math_parcc_2015_math',
      'total_district_enrollment_in_math_grade_3_8_hs_all',
      'pct_not_taking_math_tests_district_all',
    ]

    with open(papermap) as f:
        rcdts_codes = []
        paper_rcdts_ids = {}

        reader = csv.DictReader(f)

        for row in reader:
            paper = row[papercol].strip()
            if paper == "":
                continue

            rcdts_code = row[rcdtscol].strip()

            paper_codes = [p.strip() for p in paper.split(',')]
            for paper_code in paper_codes:
                paper_ids = paper_rcdts_ids.setdefault(paper_code, [])
                paper_ids.append(rcdts_code)

                if not rcdts_code.endswith('0000'):
                    rcdts_codes.append(rcdts_code)

        results_by_rcdts = {}
                
        engine = create_engine(database)

        with engine.connect() as connection:
            results = summary_query(connection, year, rcdts_codes)
            for row in results:
                rcdts_id = row['school_id']
                district_id = rcdts_id[:-4] + "0000"
                results_by_rcdts[rcdts_id] = row
                results_by_rcdts[district_id] = _district_result(row)

        fieldnames.insert(0, 'paper')

        for paper_code, rcdts_ids_for_paper in paper_rcdts_ids.items():
            output_filename = "{}__{}.{}".format(filename_prefix, paper_code,
                filename_suffix)
            output_path = os.path.join(outputdir, output_filename)
            with open(output_path, 'w') as fout:
                writer = csv.DictWriter(fout, fieldnames=fieldnames,
                    extrasaction='ignore')
                writer.writeheader()

                for rcdts_id in rcdts_ids_for_paper:
                    row = results_by_rcdts[rcdts_id].copy()
                    row['paper'] = paper_code
                    writer.writerow(row)
