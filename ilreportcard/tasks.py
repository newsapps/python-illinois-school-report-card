"""
Command line tasks for working with report card data
"""
import logging

from invoke import task

from sqlalchemy import (create_engine, MetaData)

from ilreportcard.schema import (get_assessment_schema,
    get_parcc_participation_schema) 
from ilreportcard.load import (get_assessment_loader,
    get_parcc_participation_loader)    

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


@task
def create_parcc_participation_schema(year, database=DEFAULT_DATABASE):
    schema = get_parcc_participation_schema(int(year))
    engine = create_engine(database)
    metadata = MetaData()

    for tabledef in schema.tables:
        table = tabledef.as_sqlalchemy(metadata)
        logging.info("Creating database table {}".format(tabledef.name))
        table.create(engine, checkfirst=True)


@task
def load_parcc_participation_data(year, data, flush=False,
        database=DEFAULT_DATABASE):
    schema = get_parcc_participation_schema(int(year))

    with open(data, 'r') as f:
        engine = create_engine(database)
        metadata = MetaData()
        with engine.connect() as connection:
            loader = get_parcc_participation_loader(int(year))
            loader.set_schema(schema)
            loader.load(f, metadata, connection, flush)
