import argparse
import collections
import gpudb
import sys
import random

SCHEMA = 'example_udf_python'
INPUT_TABLE = SCHEMA + '.udf_cublas_in_table'

OPTION_NO_CREATE_ERROR = {"no_error_if_exists": "true"}

def python_cublas_udf_init():

    # Create the Python UDF example schema, if it doesn't exist
    kinetica.create_schema(SCHEMA, options=OPTION_NO_CREATE_ERROR)

    ## Create input data table
    kinetica.clear_table(table_name = INPUT_TABLE, options = OPTION_NO_DROP_ERROR)
    input_table = gpudb.GPUdbTable(
        _type = [
            ["x", "float"],
            ["y", "float"],
            ["z", "float"]
        ],
        name = INPUT_TABLE,
        db = kinetica,
        options = gpudb.GPUdbTableOptions.default().is_replicated(True)
    )

    ## Insert input data
    records = []
    for val in range(10):
        records.append([random.uniform(0,10), random.uniform(0,10), random.uniform(0,10)])
    input_table.insert_records(records)

# end python_cublas_udf_init()

if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Initialize table for Python UDF CUBLAS example.')
    parser.add_argument('--url', default='http://127.0.0.1:9191', help='Kinetica URL to run example against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')

    args = parser.parse_args()

    # Establish connection with an instance of Kinetica
    kinetica = gpudb.GPUdb(host=[args.url], username=args.username, password=args.password)

    # Execute defined functions
    python_cublas_udf_init()
