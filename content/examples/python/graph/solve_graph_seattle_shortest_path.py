############################################################################
#                                                                          #
# Imports & Constants                                                      #
#                                                                          #
############################################################################

import argparse
import gpudb
from kinetica_tabulate import tabulate
from collections import OrderedDict
import sys

CSV_FILE = "road_weights.csv"

OPTION_NO_DROP_ERROR = {"no_error_if_not_exists": "true"}
OPTION_NO_CREATE_ERROR = {"no_error_if_exists": "true"}

SCHEMA = "graph_s_seattle_shortest_path"
TABLE_SRN = SCHEMA + ".seattle_road_network"

GRAPH_S = SCHEMA + ".seattle_road_network_graph"
TABLE_GRAPH_S_SPSOLVED = GRAPH_S + "_shortest_path_solved"
TABLE_GRAPH_S_SPSOLVED2 = GRAPH_S + "_shortest_path_solved2"
TABLE_GRAPH_S_SPSOLVED3 = GRAPH_S + "_shortest_path_solved3"


############################################################################
#                                                                          #
# Table Setup Function                                                     #
#                                                                          #
############################################################################

def table_setup(data_dir):
    """ Setup necessary source tables for graph solver examples. """

    print("\n===========")
    print("TABLE SETUP")
    print("===========\n")

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_SRN, options=OPTION_NO_DROP_ERROR)

    # Create the graph example schema, if it doesn't exist
    kinetica.create_schema(SCHEMA, options=OPTION_NO_CREATE_ERROR)

    # Create the Seattle road network table
    try:
        table_srn_obj = gpudb.GPUdbTable(
            _type = [
                ["OriginalEdgeID", "long"],
                ["TwoWay", "int"],
                ["WKTLINE", "string", "wkt"],
                ["time", "float"]
            ],
            name = TABLE_SRN,
            db = kinetica,
            options = {}
        )
        print("{} table object successfully created.".format(TABLE_SRN))
    except gpudb.GPUdbException as e:
        print("{} table object creation failure: {}".format(TABLE_SRN, str(e)))

    # Insert records from a local CSV file into the Seattle road network table
    csv_path = data_dir + "/" + CSV_FILE
    print("Creating records from the " + CSV_FILE + " file.")
    kinetica.create_directory("data", {"no_error_if_exists":"true"});
    kinetica.upload_files("/data/" + CSV_FILE, open(csv_path, "rb").read())
    kinetica.insert_records_from_files(TABLE_SRN, ["kifs://data/" + CSV_FILE])

    print("{} records inserted into {} table.\n".format(table_srn_obj.size(), TABLE_SRN))

# end table_setup()


############################################################################
#                                                                          #
# Graph Setup Function                                                     #
#                                                                          #
############################################################################

def graph_setup():
    """ Setup graphs to be used in solver examples. """

    print("\n===========")
    print("GRAPH SETUP")
    print("===========\n")

    # Create a graph from TABLE_SRN
    print("Creating {}".format(GRAPH_S))
    create_s_graph_response = kinetica.create_graph(
        graph_name = GRAPH_S,
        directed_graph = True,
        nodes = [],
        edges = [
            TABLE_SRN + ".WKTLINE AS WKTLINE",
            TABLE_SRN + ".TwoWay AS DIRECTION"
        ],
        weights = [
            TABLE_SRN + ".WKTLINE AS EDGE_WKTLINE",
            TABLE_SRN + ".TwoWay AS EDGE_DIRECTION",
            TABLE_SRN + ".time AS VALUESPECIFIED"
        ],
        restrictions = [],
        options = {
            "recreate": "true"
        }
    )
    if create_s_graph_response["status_info"]["status"] == "OK":
        print("{} created: {}".format(GRAPH_S, create_s_graph_response["status_info"]["status"]))
        print("Number of nodes: {}".format(create_s_graph_response["num_nodes"]))
        print("Number of edges: {}".format(create_s_graph_response["num_edges"]))
    else:
        print("{} creation failure: \n\t{}".format(GRAPH_S, create_s_graph_response["status_info"]["message"]))
        print("Exiting...")
        sys.exit()

# end graph_setup()


############################################################################
#                                                                          #
# Shortest Path Solving Function                                           #
#                                                                          #
############################################################################

def shortest_path_example():
    """Demonstrate creating and solving a graph using the SHORTEST_PATH method."""

    print("\n==============================")
    print("SHORTEST PATH SOLVER EXAMPLE 1")
    print("==============================\n")

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_GRAPH_S_SPSOLVED, options=OPTION_NO_DROP_ERROR)

    # Solve GRAPH_S for Shortest Path using a single given source node and 
    # routing to a single given destination node
    source_nodes = ["POINT(-122.1792501 47.2113606)"]
    destination_nodes = ["POINT(-122.2221 47.5707)"]
    kinetica.solve_graph(
        graph_name = GRAPH_S,
        solver_type = "SHORTEST_PATH",
        source_nodes = source_nodes,
        destination_nodes = destination_nodes,
        solution_table = TABLE_GRAPH_S_SPSOLVED
    )

    print("Cost per destination node when source node = {}: ".format(source_nodes))

    tabulate_records(
            kinetica,
            TABLE_GRAPH_S_SPSOLVED,
            ["ST_ENDPOINT(wktroute)", "SOLVERS_NODE_COSTS / 60"],
            ["Destination Node", "Cost (in minutes)"],
            ["SOLVERS_NODE_COSTS"],
            "psql"
    )

    print("\n==============================")
    print("SHORTEST PATH SOLVER EXAMPLE 2")
    print("==============================\n")

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_GRAPH_S_SPSOLVED2, options=OPTION_NO_DROP_ERROR)

    # Solve GRAPH_S for Shortest Path using the given source node and routing to
    # the given destination nodes
    source_nodes = ["POINT(-122.1792501 47.2113606)"]
    destination_nodes = [
        "POINT(-122.222100 47.570700)", 
        "POINT(-122.541017 47.809121)",
        "POINT(-122.520440 47.624725)", 
        "POINT(-122.467915 47.427280)"
    ]
    kinetica.solve_graph(
        graph_name = GRAPH_S,
        solver_type = "SHORTEST_PATH",
        source_nodes = source_nodes,
        destination_nodes = destination_nodes,
        solution_table = TABLE_GRAPH_S_SPSOLVED2
    )
    print("Cost per destination node when source node = {}: ".format(source_nodes))

    tabulate_records(
            kinetica,
            TABLE_GRAPH_S_SPSOLVED2,
            ["ST_ENDPOINT(wktroute)", "SOLVERS_NODE_COSTS / 60"],
            ["Destination Node", "Cost (in minutes)"],
            ["SOLVERS_NODE_COSTS"],
            "psql"
    )

    print("\n==============================")
    print("SHORTEST PATH SOLVER EXAMPLE 3")
    print("==============================\n")

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_GRAPH_S_SPSOLVED3, options=OPTION_NO_DROP_ERROR)

    # Solve GRAPH_S for Shortest Path using the given source nodes and routing 
    # to the given destination nodes
    source_nodes = [
        "POINT(-122.1792501 47.2113606)",
        "POINT(-122.1792501 47.2113606)",
        "POINT(-122.375180125237 47.8122103214264)",
        "POINT(-122.375180125237 47.8122103214264)"
    ]
    destination_nodes = [
        "POINT(-122.222100 47.570700)",
        "POINT(-122.541017 47.809121)",
        "POINT(-122.520440 47.624725)",
        "POINT(-122.467915 47.427280)"
    ]
    kinetica.solve_graph(
        graph_name = GRAPH_S,
        solver_type = "SHORTEST_PATH",
        source_nodes = source_nodes,
        destination_nodes = destination_nodes,
        solution_table = TABLE_GRAPH_S_SPSOLVED3
    )

    print("Cost per destination node: ")

    tabulate_records(
            kinetica,
            TABLE_GRAPH_S_SPSOLVED3,
            ["SOURCE", "TARGET", "COST / 60"],
            ["Source Node", "Destination Node", "Cost (in minutes)"],
            ["COST"],
            "psql"
    )

# end shortest_path_example()


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
    parser = argparse.ArgumentParser(description='Run Seattle shortest path solve graph example.')
    parser.add_argument('--url', default='http://127.0.0.1:9191', help='Kinetica URL to run example against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')
    parser.add_argument('--data_dir', default='./', help='Data file directory')

    args = parser.parse_args()

    # Establish connection with a locally-running instance of Kinetica
    kinetica = gpudb.GPUdb(host = [args.url], username = args.username, password = args.password)

    # Execute defined functions
    table_setup(args.data_dir)
    graph_setup()
    shortest_path_example()
