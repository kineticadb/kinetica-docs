############################################################################
#                                                                          #
# Imports & Constants                                                      #
#                                                                          #
############################################################################

import argparse
import gpudb
import sys
import json
from kinetica_tabulate import tabulate


CSV_FILE = "road_weights.csv"

OPTION_NO_DROP_ERROR = {"no_error_if_not_exists": "true"}
OPTION_NO_CREATE_ERROR = {"no_error_if_exists": "true"}

SCHEMA = "graph_s_seattle_multi_route"
TABLE_SRN = SCHEMA + ".seattle_road_network"

GRAPH_S = SCHEMA + ".seattle_road_network_graph"
TABLE_GRAPH_S_MRSOLVED = GRAPH_S + "_multiple_routing_solved"


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

    # Insert records from a CSV file into the Seattle road network table
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
        print("{} creation success!".format(GRAPH_S))
        print("Number of nodes: {}".format(create_s_graph_response["num_nodes"]))
        print("Number of edges: {}".format(create_s_graph_response["num_edges"]))
    else:
        print("{} creation failure: \n\t{}".format(
            GRAPH_S, 
            create_s_graph_response["status_info"]["message"]
        ))
        print("Exiting...")
        sys.exit()

# end graph_setup()


############################################################################
#                                                                          #
# Multiple Routing Solving Function                                        #
#                                                                          #
############################################################################

def multiple_routing_example():
    """Demonstrate creating and solving a graph using the MULTIPLE_ROUTING
    method (Traveling Salesman).
    """

    print("\n===============================")
    print("MULTIPLE ROUTING SOLVER EXAMPLE")
    print("===============================\n")

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_GRAPH_S_MRSOLVED, options=OPTION_NO_DROP_ERROR)

    # Solve GRAPH_S for Multiple Routing using the given source node and routing
    # to the given destination nodes
    print("Solving {} using MULTIPLE_ROUTING solver type.".format(GRAPH_S))
    source_node = "POINT(-122.1792501 47.2113606)"
    destination_nodes = [
        "POINT(-122.2221 47.5707)", 
        "POINT(-122.541017 47.809121)",
        "POINT(-122.520440 47.624725)", 
        "POINT(-122.467915 47.427280)"
    ]
    kinetica.solve_graph(
        graph_name = GRAPH_S,
        solver_type = "MULTIPLE_ROUTING",
        source_nodes = [source_node],
        destination_nodes = destination_nodes,
        solution_table = TABLE_GRAPH_S_MRSOLVED
    )

    print("Cost for source node {} to visit destination nodes {}:".format(source_node, destination_nodes))

    aggregate_records(
            kinetica,
            TABLE_GRAPH_S_MRSOLVED,
            ["SUM(SOLVERS_NODE_COSTS) / 60"],
            ["Cost (in minutes)"],
            tblfmt = "psql"
    )

# end multiple_routing_example()


def aggregate_records(database, table_name, column_names, column_headers = None, order_by = None, tblfmt = "grid"):
    """ Aggregate and tabulate a set of records from the given table, displaying
    the given columns with optional column headers and optionally sorted by the
    given ordering.

    Parameters:

        database (str)
            :class:`GPUdb` database connection object

        table_name (str)
            Name of the table whose records will be displayed

        column_names (list of str)
            Names of the columns or column aggregates whose values will be
            displayed

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
    resp = database.aggregate_group_by(
        table_name,
        column_names,
        encoding = 'json',
        options = options
    )
    
    if 'json_encoded_response' not in resp:
        print("[{}] Can't retrieve records: {}".format(resp['status_info']['status'], resp['status_info']['message']))
    else:
        resp = json.loads(resp['json_encoded_response'])

        records = zip(*(resp['column_' + str(i)] for i in range(1, len(column_names) + 1)))

        headers = "keys" if column_headers is None else column_headers

        print(tabulate(records, headers=headers, tablefmt=tblfmt))

# end aggregate_records()


if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Run Seattle multiple route solve graph example.')
    parser.add_argument('--url', default='http://127.0.0.1:9191', help='Kinetica URL to run example against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')
    parser.add_argument('--data_dir', default='./', help='Data file directory')

    args = parser.parse_args()

    # Establish connection with an instance of Kinetica, given a URL and credentials
    kinetica = gpudb.GPUdb(host = [args.url], username = args.username, password = args.password)

    # Execute defined functions
    table_setup(args.data_dir)
    graph_setup()
    multiple_routing_example()
