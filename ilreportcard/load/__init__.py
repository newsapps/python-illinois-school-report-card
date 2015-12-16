import csv
import logging
import re

import xlrd


class BaseLoader(object):
    def set_schema(self, schema):
        self._schema = schema

    @classmethod
    def get_column_value(cls, column, val):
        stripped = val
        try:
            stripped = val.strip()
        except AttributeError:
            # Not string
            pass

        return column.convert_value(stripped)

    @classmethod
    def get_row_values(cls, tabledef, row):
        return tuple(cls.get_column_value(c, row[c.column_index])
            for c in tabledef.columns)


class DelimitedLoader2015(BaseLoader):
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



def get_assessment_loader(year):
    if year == 2015:
        return DelimitedLoader2015()

    raise ValueError("No loader found for {}".format(year))


def get_report_card_loader(year):
    if year == 2015:
        return DelimitedLoader2015()

    raise ValueError("No loader found for {}".format(year))


class PARCCParticipationLoader2015(BaseLoader):
    def set_schema(self, schema):
        self._schema = schema

    # We have to override the get_row_values and get_column_value
    # methods to deal with a quirk in the data.
    # When the tested_enrollment_ela and tested_enrollment_math values
    # are a number less than 10, the law requires that they are not reported.
    # We need to add a synthetic column for this.
    @classmethod
    def get_column_index(cls, columndef):
        if columndef.column_index >= 13:
            column_index = columndef.column_index - 2
        elif columndef.column_index >= 6:
            column_index = columndef.column_index - 1
        else:
            column_index = columndef.column_index

        return column_index

    @classmethod
    def get_row_values(cls, tabledef, row):
        updated_row = []

        for columndef in tabledef.columns:
            column_index = cls.get_column_index(columndef)

            updated_row.append(cls.get_column_value(columndef, row[column_index]))

        return tuple(updated_row)

    @classmethod
    def get_column_value(cls, column, val):
        stripped = val
        try:
            stripped = val.strip()
        except AttributeError:
            # Not string
            pass

        if (column.name in ("tested_enrollment_ela", "tested_enrollment_math")):
            try:
                if stripped[0] == "<":
                    return None
            except TypeError:
                pass
            except IndexError:
                pass

        if (column.name.startswith("tested_enrollment_masked")):
            try:
                return stripped[0] == "<"
            except TypeError:
                return False
            except IndexError:
                return False

        return column.convert_value(stripped)

    def load(self, f, metadata, connection, flush=False):
        tabledef = self._schema.tables[0]
        table = tabledef.as_sqlalchemy(metadata)

        workbook = xlrd.open_workbook(file_contents=f.read())
        sheet = workbook.sheet_by_index(0)

        data = []
        for i in range(sheet.nrows):
            # Extract values from Excel cells so row is just a list of values
            row = [c.value for c in sheet.row(i)]
            if re.match(r'[\dA-Z]{15}', row[0]) is None:
                # Skip header rows
                continue

            data.append(self.get_row_values(tabledef, row))

        if flush:
            logging.info("Deleting existing data from {}".format(tabledef.name))
            connection.execute(table.delete())

        logging.info("Inserting {} rows into {}".format(
            len(data), tabledef.name))
        insert = table.insert().values(data)
        connection.execute(insert)


def get_parcc_participation_loader(year):
    if year == 2015:
        return PARCCParticipationLoader2015()

    raise ValueError("No loader found for {}".format(year))
