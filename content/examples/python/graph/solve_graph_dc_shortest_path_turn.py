############################################################################
#                                                                          #
# Imports & Constants                                                      #
#                                                                          #
############################################################################

import argparse
import gpudb
import sys
import json
from collections import OrderedDict
from kinetica_tabulate import tabulate


CSV_FILE = "dc_shape.csv"

OPTION_NO_CREATE_ERROR = {"no_error_if_exists": "true"}

SCHEMA = "graph_s_dc_shortest_path_turn"
TABLE_DC = SCHEMA + ".dc_shape"

GRAPH_DC = SCHEMA + ".dc_shape_graph"
SOLUTION_GRAPH_DC_1 = GRAPH_DC + "_solved_sp"
SOLUTION_GRAPH_DC_2 = GRAPH_DC + "_solved_sp_intersection-penalty"
SOLUTION_GRAPH_DC_3 = GRAPH_DC + "_solved_sp_turn-restriction"

############################################################################
#                                                                          #
# Functions                                                                #
#                                                                          #
############################################################################

def table_setup(data_dir):

    print("\n===========")
    print("TABLE SETUP")
    print("===========\n")
    
    # Create the graph example schema, if it doesn't exist
    kinetica.create_schema(SCHEMA, options=OPTION_NO_CREATE_ERROR)

    # Create the D.C. road network table
    table_dc_obj = gpudb.GPUdbTable(
        _type = [
            ["link_id", "long", "shard_key"],
            ["direction", "int"],
            ["speed", "double"],
            ["road_type", "string", "char1"],
            ["seg", "string", "wkt"],
            ["shape", "string", "wkt"],
        ],
        name = TABLE_DC,
        db = kinetica,
        options = {}
    )

    # Insert records from a local CSV file into the D.C. road network table
    csv_path = data_dir + "/" + CSV_FILE
    print("Creating records from the " + CSV_FILE + " file.")
    kinetica.create_directory("data", {"no_error_if_exists":"true"});
    kinetica.upload_files("/data/" + CSV_FILE, open(csv_path, "rb").read())
    kinetica.insert_records_from_files(TABLE_DC, ["kifs://data/" + CSV_FILE])

    print("{} records inserted into {} table.\n".format(table_dc_obj.size(), TABLE_DC))

# end table_setup()

def graph_setup():

    print("\n===========")
    print("GRAPH SETUP")
    print("===========\n")

    # Create a graph from TABLE_DC
    print("Creating graph: {}".format(GRAPH_DC))
    cg = kinetica.create_graph(
        graph_name = GRAPH_DC,
        directed_graph = True,
        nodes = [],
        edges = [
            TABLE_DC + ".link_id AS ID",
            TABLE_DC + ".shape AS WKTLINE",
            TABLE_DC + ".direction AS DIRECTION",
            "(ST_LENGTH(" + TABLE_DC + ".shape,1)/"
            "(ST_NPOINTS(" + TABLE_DC + ".shape)-1))/" + 
            TABLE_DC + ".speed AS WEIGHT_VALUESPECIFIED"
        ],
        weights = [],
        restrictions = [],
        options = {
            "recreate": "true",
            "add_turns": "true"
        }
    )
    print("- {}".format(cg["status_info"]["status"]))

# end graph_setup()

def solve_graph():

    # Set source and destination points for the examples
    src = ["POINT(-77.04489135742188 38.91112899780273)"]
    dest = ["POINT(-77.03193664550781 38.91188049316406)"]

    print("\n====================================")
    print("SOLVE GRAPH - TURN PENALTY EXAMPLE 1")
    print("====================================\n")

    # Solve GRAPH_DC for shortest path between given source_node 'src' and 
    # destination node 'dest'
    kinetica.solve_graph(
        graph_name = GRAPH_DC,
        solver_type = "SHORTEST_PATH",
        source_nodes = src,
        destination_nodes = dest,
        solution_table = SOLUTION_GRAPH_DC_1
    )
    print("Cost for shortest path between source ({}) and destination ({}):".format(src, dest))

    tabulate_records(
            kinetica,
            SOLUTION_GRAPH_DC_1,
            ["SOLVERS_NODE_COSTS"],
            ["Cost (in seconds)"],
            tblfmt = "psql"
    )

    print("\n====================================")
    print("SOLVE GRAPH - TURN PENALTY EXAMPLE 2")
    print("====================================\n")

    # Solve GRAPH_DC for shortest path between given source_node 'src' and
    # destination node 'dest' but with a penalty on using intersections
    kinetica.solve_graph(
        graph_name = GRAPH_DC,
        solver_type = "SHORTEST_PATH",
        source_nodes = src,
        destination_nodes = dest,
        solution_table = SOLUTION_GRAPH_DC_2,
        options = {
            "intersection_penalty": "20"
        }
    )

    print("Cost for shortest path between source ({}) and destination ({}) with intersection penalty:".format(src, dest))

    tabulate_records(
            kinetica,
            SOLUTION_GRAPH_DC_2,
            ["SOLVERS_NODE_COSTS"],
            ["Cost (in seconds)"],
            tblfmt = "psql"
    )

    print("\n====================================")
    print("SOLVE GRAPH - TURN PENALTY EXAMPLE 3")
    print("====================================\n")

    # Solve GRAPH_DC for shortest path between given source_node 'src' and
    # destination node 'dest' with restricting the turn between given edge IDs
    kinetica.solve_graph(
        graph_name = GRAPH_DC,
        restrictions = [
            "{18352169} AS FROM_EDGE_ID",
            "{18352166} AS TO_EDGE_ID",
            "{0} AS ONOFFCOMPARED"
        ],
        solver_type = "SHORTEST_PATH",
        source_nodes = src,
        destination_nodes = dest,
        solution_table = SOLUTION_GRAPH_DC_3
    )

    print("Cost for shortest path between source ({}) and destination ({}) with one turn restriction:".format(src, dest))

    tabulate_records(
            kinetica,
            SOLUTION_GRAPH_DC_3,
            ["SOLVERS_NODE_COSTS"],
            ["Cost (in seconds)"],
            tblfmt = "psql"
    )

# end solve_graph()


def clear_tables():

    # Drop all the tables
    for table_name in [
        TABLE_DC,
        SOLUTION_GRAPH_DC_1,
        SOLUTION_GRAPH_DC_2,
        SOLUTION_GRAPH_DC_3
    ]:
        ct = kinetica.clear_table(table_name, "", {"no_error_if_not_exists": "true"})

# end clear_tables()


def tabulate_records(database, table_name, column_names, column_headers = None, order_by = None, tblfmt = "grid"):
    """ Retrieve and tabulate a set of records from the given table, displaying
    the given columns with optional column headers and optionally sorted by the
    given ordering.

    Parameters:

        database (str)
            :class:`GPUdb` database connection object

        table_name (str)
            Name of the table whose records will be displayed

        column_names (list of str)
            Names of the columns whose values will be displayed

        column_headers (list of str)
            Header text to display at the top of the respective columns; should
            align with the columns specified in `column_names`

        order_by (list of str)
            Name(s) of the column(s) by which the results should be sorted, in
            the sequence they should be sorted; accepts `asc` & `desc` for
            forward/reverse sorting

        tblfmt (str)
            Output style, conforming to `tabulate` supported formats listed
            here:  https://github.com/astanin/python-tabulate#table-format
    """

    options = {'order_by': ','.join(order_by)} if order_by is not None else {}
    resp = database.get_records_by_column_and_decode(
        table_name,
        column_names,
        encoding = 'json',
        get_column_major = False,
        options = options
    )
    
    if 'records' not in resp:
        print("[{}] Can't retrieve records: {}".format(resp['status_info']['status'], resp['status_info']['message']))
    else:
        records = resp['records']

        if column_headers is None:
            headers = "keys"
        else:
            # Create an ordered dictionary of the columns names and
            #    the given column headers to preserve column order;
            #    name & header lists must be the same size
            headers = OrderedDict({column_names[i]: column_headers[i] for i in range(0, len(column_headers))})

        print(tabulate(records, headers=headers, tablefmt=tblfmt))

# end tabulate_records()


if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Run multiple supply & demand match graph example.')
    parser.add_argument('command', nargs="?", help='command to execute (currently only "clear" to remove the example tables')
    parser.add_argument('--url', default='http://127.0.0.1:9191', help='Kinetica URL to run example against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')
    parser.add_argument('--data_dir', default='./', help='Data file directory')

    args = parser.parse_args()

    # Establish connection with a locally-running instance of Kinetica
    kinetica = gpudb.GPUdb(host = [args.url], username = args.username, password = args.password)

    # If command line arg is clear, just clear tables and exit
    if (args.command == "clear"):
        clear_tables()
        quit()

    # Execute defined functions
    clear_tables()
    table_setup(args.data_dir)
    graph_setup()
    solve_graph()
