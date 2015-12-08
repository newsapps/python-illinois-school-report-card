import csv

import logging

class AssessmentLoader2015(object):
    def set_schema(self, schema):
        self._schema = schema

    def load(self, f, metadata, connection, flush=False):
        table_data = {t.name: [] for t in self._schema.tables}

        reader = csv.reader(f, delimiter=';')
        num_rows = 0

        logging.info("Beginning parsing data file")

        for row in reader:
            num_rows += 1
            for tabledef in self._schema.tables:
                insert_row = self.get_row_values(tabledef, row) 
                table_data[tabledef.name].append(insert_row)

        logging.info("Parsed {} rows".format(num_rows))        

        for tabledef in self._schema.tables:
            table = tabledef.as_sqlalchemy(metadata)

            if flush:
                logging.info("Deleting existing data from {}".format(tabledef.name))
                connection.execute(table.delete())

            logging.info("Inserting {} rows into {}".format(
                len(table_data[tabledef.name]), tabledef.name))

            insert = table.insert().values(table_data[tabledef.name])
            connection.execute(insert)

    @classmethod
    def get_row_values(cls, tabledef, row):
        return tuple(c.convert_value(row[c.column_index].strip())
            for c in tabledef.columns)


def get_assessment_loader(year):
    if year == 2015:
        return AssessmentLoader2015()

    raise ValueError("No loader found for {}".format(year))
