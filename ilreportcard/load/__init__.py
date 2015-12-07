import csv

class AssessmentLoader2015(object):
    def set_schema(self, schema):
        self._schema = schema

    def load(self, f, metadata, connection):
        table_data = {t.name: [] for t in self._schema.tables}

        reader = csv.reader(f, delimiter=';')
        for row in reader:
            for tabledef in self._schema.tables:
                insert_row = self.get_row_values(tabledef, row) 
                table_data[tabledef.name].append(insert_row)

        for tabledef in self._schema.tables:
            table = tabledef.as_sqlalchemy(metadata)
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
