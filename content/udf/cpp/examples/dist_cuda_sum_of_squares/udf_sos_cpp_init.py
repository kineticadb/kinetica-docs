import argparse
import collections
import gpudb
import sys

SCHEMA = 'example_udf_cpp'
INPUT_TABLE = SCHEMA + '.udf_sos_in_table'
OUTPUT_TABLE = SCHEMA + '.udf_sos_out_table'
MAX_RECORDS = 10000

OPTION_NO_CREATE_ERROR = {"no_error_if_exists": "true"}

def cpp_sos_udf_init():

    # Create the C++ UDF example schema, if it doesn't exist
    kinetica.create_schema(SCHEMA, options=OPTION_NO_CREATE_ERROR)

   # Create input data table
    columns = []
    columns.append(gpudb.GPUdbRecordColumn("id", gpudb.GPUdbRecordColumn._ColumnType.INT, [gpudb.GPUdbColumnProperty.PRIMARY_KEY, gpudb.GPUdbColumnProperty.INT16]))
    columns.append(gpudb.GPUdbRecordColumn("x1", gpudb.GPUdbRecordColumn._ColumnType.FLOAT))
    columns.append(gpudb.GPUdbRecordColumn("x2", gpudb.GPUdbRecordColumn._ColumnType.FLOAT))

    if kinetica.has_table(table_name = INPUT_TABLE)['table_exists']:
       kinetica.clear_table(table_name = INPUT_TABLE)
    input_table = gpudb.GPUdbTable(columns, INPUT_TABLE, db = kinetica)


    # Insert input data
    import random

    records = []
    for val in range(1, MAX_RECORDS+1):
       records.append([val, random.gauss(1,1), random.gauss(1,2)])
    input_table.insert_records(records)


    # Create output data table
    columns = []
    columns.append(gpudb.GPUdbRecordColumn("id", gpudb.GPUdbRecordColumn._ColumnType.INT, [gpudb.GPUdbColumnProperty.PRIMARY_KEY, gpudb.GPUdbColumnProperty.INT16]))
    columns.append(gpudb.GPUdbRecordColumn("y", gpudb.GPUdbRecordColumn._ColumnType.FLOAT))

    if kinetica.has_table(table_name = OUTPUT_TABLE)['table_exists']:
       kinetica.clear_table(table_name = OUTPUT_TABLE)
    gpudb.GPUdbTable(columns, OUTPUT_TABLE, db = kinetica)

# end cpp_sos_udf_init()

if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Initialize tables for C++ UDF sum of squares example.')
    parser.add_argument('--host', default='127.0.0.1', help='Kinetica host to run example against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')

    args = parser.parse_args()

    # Establish connection with a locally-running instance of Kinetica
    kinetica = gpudb.GPUdb(host = ['http://' + args.host + ':9191'], username = args.username, password = args.password)

    # Execute defined functions
    cpp_sos_udf_init()
