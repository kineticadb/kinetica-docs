import argparse
import gpudb
import sys

SCHEMA = 'example_udf_python'
INPUT_TABLE = SCHEMA + '.udf_cublas_in_table'
proc_name = 'udf_cublas_py_proc'
file_name = proc_name + '.py'

def python_cublas_udf_exec():

    # Read proc code in as bytes and add to a file data array
    files = {}
    with open(file_name, 'rb') as file:
        files[file_name] = file.read()

    # Remove proc if it exists from a prior registration
    if kinetica.has_proc(proc_name)['proc_exists']:
        kinetica.delete_proc(proc_name)

    print "Registering proc..."
    response = kinetica.create_proc(proc_name, 'distributed', files, 'python', [file_name], {})
    print response

    print "Executing proc..."
    response = kinetica.execute_proc(proc_name, {}, {}, [INPUT_TABLE], {}, [], {})
    print response

# end python_cublas_udf_exec()

if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Execute the CUBLAS Python UDF example.')
    parser.add_argument('--url', default='http://127.0.0.1:9191', help='Kinetica URL to run example against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')

    args = parser.parse_args()

    # Establish connection with an instance of Kinetica
    kinetica = gpudb.GPUdb(host=[args.url], username=args.username, password=args.password)

    # Execute defined functions
    python_cublas_udf_exec()
