import logging

from invoke import task

from sqlalchemy import (create_engine, MetaData)

from ilreportcard.schema import get_assessment_schema
from ilreportcard.load import get_assessment_loader

logging.basicConfig(level=logging.INFO)

@task
def create_assessment_schema(year, layout, database="postgresql://localhost:5432/school_report_card"):
    with open(layout, 'rb') as f:
        schema = get_assessment_schema(int(year))
        schema.from_file(f)

        engine = create_engine(database)
        metadata = MetaData()

        for tabledef in schema.tables:
            table = tabledef.as_sqlalchemy(metadata) 

        metadata.create_all(engine)


@task
def load_assessment_data(year, layout, data,
        database="postgresql://localhost:5432/school_report_card"):
    with open(layout, 'rb') as f:
        schema = get_assessment_schema(int(year))
        schema.from_file(f)

    with open(data, 'r') as f:
        engine = create_engine(database)
        metadata = MetaData()
        with engine.connect() as connection:
            loader = get_assessment_loader(int(year))
            loader.set_schema(schema)
            loader.load(f, metadata, connection)

        
