import argparse
import gpudb
import random

PROC_NAME = 'udf_sos_py_proc'
PROC_FILE_NAME = 'udf_sos_proc.py'
MAX_RECORDS = 10000


def udf_init(kinetica, schema, input_table, output_table):

    if schema:
        # Create the Python UDF example schema, if it doesn't exist
        kinetica.create_schema(schema, options={"no_error_if_exists": "true"})

    ## Create input data table
    if kinetica.has_table(table_name=input_table)['table_exists']:
        kinetica.clear_table(table_name=input_table)

    input_table_obj = gpudb.GPUdbTable(
        _type = [
            ["id", "int", gpudb.GPUdbColumnProperty.INT16, gpudb.GPUdbColumnProperty.PRIMARY_KEY],
            ["x1", "float"],
            ["x2", "float"]
        ],
        name = input_table,
        db = kinetica
    )

    ## Insert input data
    records = []
    for val in range(1, MAX_RECORDS+1):
        records.append([val, random.gauss(1, 1), random.gauss(1, 2)])
    input_table_obj.insert_records(records)

    ## Create output data table
    if kinetica.has_table(table_name=output_table)['table_exists']:
        kinetica.clear_table(table_name=output_table)

    gpudb.GPUdbTable(
        _type = [
            ["id", "int", gpudb.GPUdbColumnProperty.INT16, gpudb.GPUdbColumnProperty.PRIMARY_KEY],
            ["y", "float"]
        ],
        name = output_table,
        db = kinetica
    )

# end udf_init()


def udf_exec(kinetica, input_table, output_table):

    # Read proc code in as bytes and add to a file data array
    files = {}
    with open(PROC_FILE_NAME, 'rb') as file:
        files[PROC_FILE_NAME] = file.read()

    # Remove proc if it exists from a prior registration
    if kinetica.has_proc(PROC_NAME)['proc_exists']:
        kinetica.delete_proc(PROC_NAME)

    print("Registering UDF...")
    response = kinetica.create_proc(PROC_NAME, 'distributed', files, 'python3', [PROC_FILE_NAME], {})
    print(response)

    print("Executing UDF...")
    response = kinetica.execute_proc(PROC_NAME, {}, {}, [input_table], {}, [output_table], {})
    print(response)

# udf_exec()


if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Perform a task of the Python UDF sum-of-squares example.')
    parser.add_argument('task', choices=['init','exec'], help='UDF task to run; "init" to initialize the UDF environment, "exec" to run the UDF')
    parser.add_argument('url', default='http://127.0.0.1:9191', help='Kinetica URL to run example against')
    parser.add_argument('username', default='', help='Username of user to run example with')
    parser.add_argument('password', default='', help='Password of user')
    parser.add_argument('--schema', default='', help='Schema in which to create tutorial tables')

    args = parser.parse_args()

    input_table = 'udf_sos_py_in_table'
    output_table = 'udf_sos_py_out_table'

    if args.schema:
        input_table = args.schema + '.' + input_table
        output_table = args.schema + '.' + output_table

    # Establish connection with an instance of Kinetica
    kinetica = gpudb.GPUdb(host=[args.url], username=args.username, password=args.password)

    if args.task == 'init':
        udf_init(kinetica, args.schema, input_table, output_table)
    elif args.task == 'exec':
        udf_exec(kinetica, input_table, output_table)
    else:
        print(f'Unknown task <{args.task}>')
