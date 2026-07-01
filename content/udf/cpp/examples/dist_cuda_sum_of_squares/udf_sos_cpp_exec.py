import argparse
import gpudb
import sys

SCHEMA = 'example_udf_cpp'
INPUT_TABLE = SCHEMA + '.udf_sos_in_table'
OUTPUT_TABLE = SCHEMA + '.udf_sos_out_table'
proc_name = 'udf_sos_cpp_proc'
file_name = proc_name

def cpp_sos_udf_exec():
    # Read proc code in as bytes and add to a file data array
    files = {}
    with open(file_name, 'rb') as file:
        files[file_name] = file.read()

    # Remove proc if it exists from a prior registration
    if kinetica.has_proc(proc_name)['proc_exists']:
        kinetica.delete_proc(proc_name)

    print "Registering proc..."
    response = kinetica.create_proc(proc_name, 'distributed', files, './' + file_name, [], {})
    print response

    print "Executing proc..."
    response = kinetica.execute_proc(proc_name, {}, {}, [INPUT_TABLE], {}, [OUTPUT_TABLE], {})
    print response

# end cpp_sos_udf_exec()

if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Execute the sum of squares C++ UDF example.')
    parser.add_argument('--host', default='127.0.0.1', help='Kinetica host to run example against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')

    args = parser.parse_args()

    # Establish connection with a locally-running instance of Kinetica
    kinetica = gpudb.GPUdb(host = ['http://' + args.host + ':9191'], username = args.username, password = args.password)

    # Execute defined functions
    cpp_sos_udf_exec()
