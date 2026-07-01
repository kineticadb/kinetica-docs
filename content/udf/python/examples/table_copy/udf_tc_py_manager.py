import argparse
import gpudb
import random
import sys

PROC_NAME = 'udf_tc_py_proc'
PROC_FILE_NAME = PROC_NAME + '.py'
CSV_FILE_NAME = 'rank_tom.csv'
MAX_RECORDS = 10000


def udf_init(kinetica, schema, input_table, output_table):

    print("")
    print("PYTHON UDF TABLE COPY INITIALIZATION")
    print("====================================")
    print("")

    if schema:
        # Create the Python UDF tutorial schema, if it doesn't exist
        kinetica.create_schema(schema, options={"no_error_if_exists": "true"})

    # Create input data table
    columns = [
        ["id", "int", "int16", "primary_key"],
        ["x", "float"],
        ["y", "float"]
    ]

    if kinetica.has_table(table_name=input_table)['table_exists']:
        kinetica.clear_table(table_name=input_table)

    input_table_obj = gpudb.GPUdbTable(
        _type = columns,
        name = input_table,
        db = kinetica
    )

    print("Input table successfully created: ")
    print(input_table_obj)

    records = []
    for val in range(1, MAX_RECORDS+1):
        records.append([val, random.gauss(1, 1), random.gauss(1, 2)])
    input_table_obj.insert_records(records)

    print("Number of records inserted into the input table: {}".format(input_table_obj.size()))

    # Create output data table
    columns = [
        ["id", "int", "int16", "primary_key"],
        ["a", "float"],
        ["b", "float"]
    ]

    if kinetica.has_table(table_name=output_table)['table_exists']:
        kinetica.clear_table(table_name=output_table)

    output_table_obj = gpudb.GPUdbTable(
        _type = columns,
        name = output_table,
        db = kinetica
    )

    print("")
    print("Output table successfully created: ")
    print(output_table_obj)
    print("")

# end udf_init()


def udf_exec(kinetica, input_table, output_table):

    print("")
    print("PYTHON UDF TABLE COPY EXECUTION")
    print("===============================")

    print("")
    print(f'Reading in the <{PROC_FILE_NAME}> and <{CSV_FILE_NAME}> files as bytes...')
    print("")

    file_names = (CSV_FILE_NAME, PROC_FILE_NAME)
    files = {}
    for file_name in file_names:
        with open(file_name, 'rb') as file:
            files[file_name] = file.read()

    # Remove proc if it exists from a prior registration
    if kinetica.has_proc(proc_name=PROC_NAME)["proc_exists"]:
        kinetica.delete_proc(proc_name=PROC_NAME)

    print("Registering distributed proc...")
    response = kinetica.create_proc(
        proc_name = PROC_NAME,
        execution_mode = "distributed",
        files = files,
        command = "python",
        args = [PROC_FILE_NAME],
        options = {}
    )
    print("Proc created successfully:")
    print(response)
    print("")

    print("Executing proc...")
    response = kinetica.execute_proc(
        proc_name = PROC_NAME,
        params = {},
        bin_params = {},
        input_table_names = [input_table],
        input_column_names = {},
        output_table_names = [output_table],
        options = {}
    )
    print("Proc executed successfully:")
    print(response)
    print("Check the system log or 'gpudb.log' for execution information")
    print("")

# end udf_exec()


if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Perform a task of the Python UDF table copy example.')
    parser.add_argument('task', choices=['init','exec'], help='UDF task to run; "init" to initialize the UDF environment, "exec" to run the UDF')
    parser.add_argument('url', default='http://127.0.0.1:9191', help='Kinetica URL to run example against')
    parser.add_argument('username', default='', help='Username of user to run example with')
    parser.add_argument('password', default='', help='Password of user')
    parser.add_argument('--schema', default='', help='Schema in which to create tutorial tables')

    args = parser.parse_args()

    input_table = 'udf_tc_py_in_table'
    output_table = 'udf_tc_py_out_table'

    if args.schema:
        input_table = args.schema + '.' + input_table
        output_table = args.schema + '.' + output_table

    # Establish connection with an instance of Kinetica
    kinetica = gpudb.GPUdb(host=[args.url], username=args.username, password=args.password)

    if args.task == 'init':
        udf_init(kinetica, args.schema, input_table, output_table)
    elif args.task == 'exec':
        # Execute defined functions
        udf_exec(kinetica, input_table, output_table)
    else:
        print(f'Unknown task <{args.task}>')
