################################################################################
#                                                                              #
# Kinetica Python Table Copy UDF Manager Example                               #
# ---------------------------------------------------------------------------- #
# This script manages the initialization, creation, execution, & verification  #
# of the Python Table Copy UDF.  See udf_tc.py for details.                    #
#                                                                              #
################################################################################

import argparse
import random
import sys
import time
from pathlib import Path
from gpudb import GPUdb, GPUdbTable
from gpudb_file_handler import GPUdbFileHandler

PROC_FILE_NAME = 'udf_tc.py'
PROC_NAME = PROC_FILE_NAME.replace('.', '_')
CSV_FILE_NAME = 'rank_tom.csv'
KIFS_DIR = 'udf'
MAX_RECORDS = 10000

def udf_init(kinetica, schema, input_table, output_table):

    print("")
    print("PYTHON UDF INITIALIZATION")
    print("=========================")
    print("")

    if schema:
        # Create the Python UDF schema, if it doesn't exist
        kinetica.create_schema(schema, options={"no_error_if_exists": "true"})

    # Create input data table
    columns = [
        ["id", "int", "int16", "primary_key"],
        ["x", "float"],
        ["y", "float"]
    ]

    if kinetica.has_table(table_name=input_table)['table_exists']:
        kinetica.clear_table(table_name=input_table)

    input_table_obj = GPUdbTable(
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

    print(f"Number of records inserted into the input table: {input_table_obj.size()}")

    # Create output data table
    columns = [
        ["id", "int", "int16", "primary_key"],
        ["a", "float"],
        ["b", "float"]
    ]

    if kinetica.has_table(table_name=output_table)['table_exists']:
        kinetica.clear_table(table_name=output_table)

    output_table_obj = GPUdbTable(
        _type = columns,
        name = output_table,
        db = kinetica
    )

    print("")
    print("Output table successfully created: ")
    print(output_table_obj)
    print("")

# end udf_init()


def udf_create(kinetica):

    print("")
    print("PYTHON UDF CREATION")
    print("===================")

    # Remove proc if it exists from a prior registration
    if kinetica.has_proc(proc_name=PROC_NAME)["proc_exists"]:
        kinetica.delete_proc(proc_name=PROC_NAME)

    print("")
    print(f'Reading in the <{PROC_FILE_NAME}> and <{CSV_FILE_NAME}> files as bytes...')
    print("")

    files = [PROC_FILE_NAME, CSV_FILE_NAME]
    file_map = {}
    for file in files:
        with open(f"{Path(__file__).resolve().parent}/{file}", 'rb') as f:
            file_map[file] = f.read()

    print("Registering distributed proc...")
    response = kinetica.create_proc(
        proc_name = PROC_NAME,
        execution_mode = "distributed",
        files = file_map,
        command = "python",
        args = files,
        options = {}
    )

    if response['status_info']['status'] == 'ERROR':
        print("Proc creation failed: " + response['status_info']['message'])
    else:
        print("Proc created successfully")
    print("")

# end udf_create()


def udf_create_kifs(kinetica):

    print("")
    print("PYTHON UDF CREATION")
    print("===================")

    # Remove proc if it exists from a prior registration
    if kinetica.has_proc(proc_name=PROC_NAME)["proc_exists"]:
        kinetica.delete_proc(proc_name=PROC_NAME)

    print("")
    print(f'Uploading the <{PROC_FILE_NAME}> and <{CSV_FILE_NAME}> files to KiFS...')
    print("")

    # Create UDF directory, upload UDF and rank/tom list, and set parameters:
    # * files - map of files with full KiFS path (kifs://dir/file.ext) to empty bytes
    # * args - file names prefixed with their KiFS directory (dir/file.ext)
    kinetica.create_directory(KIFS_DIR, options={"no_error_if_exists": "true"})

    files = [PROC_FILE_NAME, CSV_FILE_NAME]
    file_map = {}

    fh = GPUdbFileHandler(kinetica)
    for file in files:
        fh.upload_file(f"{Path(__file__).resolve().parent}/{file}", KIFS_DIR)
        file_map[f'kifs://{KIFS_DIR}/{file}'] = b''

    print("Registering distributed proc...")
    response = kinetica.create_proc(
        proc_name = PROC_NAME,
        execution_mode = "distributed",
        files = file_map,
        command = "python",
        args = [f'{KIFS_DIR}/{PROC_FILE_NAME}', f'{KIFS_DIR}/{CSV_FILE_NAME}'],
        options = {}
    )

    if response['status_info']['status'] == 'ERROR':
        print("Proc creation failed: " + response['status_info']['message'])
    else:
        print("Proc created successfully")
    print("")

# end udf_create_kifs()


def udf_exec(kinetica, input_table, output_table):

    print("")
    print("PYTHON UDF EXECUTION")
    print("====================")

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

    if response['status_info']['status'] == 'ERROR':
        print("Proc execution failed: " + response['status_info']['message'])
    else:
        print("Proc executed successfully")
    print("Check the system log or 'gpudb.log' for execution information")
    print("")

# end udf_exec()


def udf_print(kinetica, input_table, output_table):

    print("")
    print("PYTHON UDF RESULTS")
    print("==================")

    result = kinetica.query(f"""
        SELECT
            IF
            (
                o.id IS NULL,
                'No: record not copied',
                IF(i.x = o.a AND i.y = o.b, 'Yes', 'No: <' || i.x || ' vs. ' || o.a || '> and <' || i.y || ' vs. ' || o.b || '>')
            ) AS matched,
            COUNT(*) AS total
        FROM {input_table} i
        LEFT JOIN {output_table} o ON i.id = o.id
        GROUP BY matched
        ORDER BY matched;
    """)

    print(f'Total Matched?')
    print(f'----- --------')
    for record in result:
        print(f'{record[1]:5} {record[0]}')
    print("")

# end udf_print()


def udf_run(kinetica, schema, input_table, output_table):
    
    print("====================================")
    print("PYTHON NON-KIFS-BASED TABLE COPY UDF")
    print("====================================")

    udf_init(kinetica, schema, input_table, output_table)
    udf_create(kinetica)
    udf_exec(kinetica, input_table, output_table)
    time.sleep(1)
    udf_print(kinetica, input_table, output_table)

# end udf_run


def udf_run_kifs(kinetica, schema, input_table, output_table):
    
    print("================================")
    print("PYTHON KIFS-BASED TABLE COPY UDF")
    print("================================")

    udf_init(kinetica, schema, input_table, output_table)
    udf_create_kifs(kinetica)
    udf_exec(kinetica, input_table, output_table)
    time.sleep(1)
    udf_print(kinetica, input_table, output_table)

# end udf_run_kifs


def udf_run_all(kinetica, schema, input_table, output_table):
    
    udf_run(kinetica, schema, input_table, output_table)
    print("\n")
    udf_run_kifs(kinetica, schema, input_table, output_table)

# end udf_run_all



if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Perform a task of the Python UDF table copy example.')
    parser.add_argument(
        'task',
        choices = ['init','create','create_kifs','exec','print','run','run_kifs','run_all'],
        help = 'UDF task to run; '
            '"init" to initialize the UDF environment, '
            '"create" to create the UDF with files read in as bytes, '
            '"create_kifs" to create the UDF with files uploaded to KiFS, '
            '"exec" to run the UDF, '
            '"print" to print the results of the UDF execution, '
            '"run" to run a complete example UDF with files read in as bytes, '
            '"run_kifs" to run a complete example UDF with files uploaded to KiFS, or '
            '"run_all" to run both "run" & "run_kifs"'
    )
    parser.add_argument('url', default='http://127.0.0.1:9191', help='Kinetica URL to run example against')
    parser.add_argument('username', default='', help='Username of user to run example with')
    parser.add_argument('password', default='', help='Password of user')
    parser.add_argument('--schema', default='', help='Schema in which to create example tables')

    args = parser.parse_args()

    input_table = 'udf_tc_in_table'
    output_table = 'udf_tc_out_table'

    if args.schema:
        input_table = args.schema + '.' + input_table
        output_table = args.schema + '.' + output_table

    # Establish connection with an instance of Kinetica
    kinetica = GPUdb(host=[args.url], username=args.username, password=args.password)

    if args.task == 'init':
        udf_init(kinetica, args.schema, input_table, output_table)
    elif args.task == 'create':
        # Create defined function with files read in as bytes
        udf_create(kinetica)
    elif args.task == 'create_kifs':
        # Create defined function with files uploaded to KiFS
        udf_create_kifs(kinetica)
    elif args.task == 'exec':
        # Execute defined function
        udf_exec(kinetica, input_table, output_table)
    elif args.task == 'print':
        # Print results of function execution
        udf_print(kinetica, input_table, output_table)
    elif args.task == 'run':
        # Run UDF tasks with files read in as bytes
        udf_run(kinetica, args.schema, input_table, output_table)
    elif args.task == 'run_kifs':
        # Run UDF tasks with files uploaded to KiFS
        udf_run_kifs(kinetica, args.schema, input_table, output_table)
    elif args.task == 'run_all':
        # Run UDF tasks with both reading in files as bytes and uploading them to KiFS
        udf_run_all(kinetica, args.schema, input_table, output_table)
    else:
        print(f'Unknown task <{args.task}>')
