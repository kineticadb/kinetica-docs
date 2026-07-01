############################################################################
#                                                                          #
# Imports & Constants                                                      #
#                                                                          #
############################################################################

import argparse
import gpudb
import sys
from collections import OrderedDict
from kinetica_tabulate import tabulate



CSV_FILE = "road_weights.csv"

OPTION_NO_DROP_ERROR = {"no_error_if_not_exists": "true"}
OPTION_NO_CREATE_ERROR = {"no_error_if_exists": "true"}

SCHEMA = "graph_s_backhaul"
TABLE_SRN = SCHEMA + ".seattle_road_network"

GRAPH_S = SCHEMA + ".seattle_road_network_graph"
TABLE_GRAPH_S_BSOLVED = GRAPH_S + "_backhaul_routing_solved"


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
# Backhaul Routing Solving Function                                        #
#                                                                          #
############################################################################

def backhaul_example():
    """Demonstrate creating and solving a graph using the BACKHAUL_ROUTING method."""

    print("\n===============================")
    print("BACKHAUL ROUTING SOLVER EXAMPLE")
    print("===============================\n")

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_GRAPH_S_BSOLVED, options=OPTION_NO_DROP_ERROR)

    # Solve GRAPH_S for Backhaul Routing using the given source node and
    # routing to the given destination nodes
    print("Solving {} using BACKHAUL_ROUTING solver type.".format(GRAPH_S))
    fixed_assets = [
        "POINT(-122.37694377950754 47.69058183874783)",
        "POINT(-122.37591381124582 47.6947415132984)",
        "POINT(-122.3635541921052 47.70005617015495)",
        "POINT(-122.35565776876535 47.70583235665686)",
        "POINT(-122.35531444601145 47.72477375603093)",
        "POINT(-122.33540172628489 47.72361898977214)",
        "POINT(-122.32407207540598 47.72408089934756)",
        "POINT(-122.32647533468332 47.73562730759159)",
        "POINT(-122.32922191671457 47.74209217807247)",
        "POINT(-122.31205577901926 47.741399551774876)",
        "POINT(-122.31274242452707 47.737705389219734)",
        "POINT(-122.29935283712473 47.73701270455902)",
        "POINT(-122.2976362233552 47.73262548770682)",
        "POINT(-122.2921430592927 47.73354914302527)",
        "POINT(-122.29179973653879 47.72200227400312)",
        "POINT(-122.30003948263254 47.712531931184785)",
        "POINT(-122.30278606466379 47.701442513285734)",
        "POINT(-122.30518932394114 47.694048257248284)",
        "POINT(-122.30244274190989 47.68827076507089)",
        "POINT(-122.31514568380442 47.68480396253861)",
        "POINT(-122.32750530294504 47.68711518982914)",
        "POINT(-122.3474180226716 47.687577422998146)",
        "POINT(-122.37763042501535 47.686421832395006)",
        "POINT(-122.37694377950754 47.69058183874783)"
    ]
    remote_assets = [
        "POINT(-122.324612 47.725231)", "POINT(-122.362112 47.696131)",
        "POINT(-122.356212 47.741731)", "POINT(-122.341512 47.702631)",
        "POINT(-122.327412 47.737131)", "POINT(-122.344912 47.727531)",
        "POINT(-122.291612 47.657631)", "POINT(-122.324512 47.703831)",
        "POINT(-122.297712 47.731231)", "POINT(-122.317912 47.699431)",
        "POINT(-122.351412 47.713731)", "POINT(-122.295612 47.670531)",
        "POINT(-122.321812 47.672731)", "POINT(-122.295612 47.697531)",
        "POINT(-122.333012 47.689831)", "POINT(-122.298812 47.711731)",
        "POINT(-122.309612 47.684931)", "POINT(-122.359712 47.716431)",
        "POINT(-122.360612 47.659231)", "POINT(-122.299012 47.707431)",
        "POINT(-122.311612 47.666831)", "POINT(-122.315912 47.724631)",
        "POINT(-122.316912 47.709531)", "POINT(-122.313212 47.685731)",
        "POINT(-122.321712 47.721231)", "POINT(-122.339512 47.695031)",
        "POINT(-122.310512 47.692531)", "POINT(-122.326512 47.679731)",
        "POINT(-122.358112 47.705731)", "POINT(-122.352812 47.715931)",
        "POINT(-122.291612 47.677531)", "POINT(-122.295712 47.666731)",
        "POINT(-122.303712 47.681531)", "POINT(-122.362312 47.732231)",
        "POINT(-122.347712 47.740431)", "POINT(-122.343512 47.685231)",
        "POINT(-122.326412 47.730631)", "POINT(-122.357812 47.670031)",
        "POINT(-122.321012 47.694531)", "POINT(-122.353312 47.737131)",
        "POINT(-122.323412 47.679031)", "POINT(-122.351012 47.701731)",
        "POINT(-122.349112 47.735931)", "POINT(-122.361612 47.675031)",
        "POINT(-122.320912 47.701931)", "POINT(-122.345412 47.693331)",
        "POINT(-122.357112 47.669631)", "POINT(-122.352912 47.685131)",
        "POINT(-122.361712 47.681331)", "POINT(-122.346312 47.722231)"
    ]
    kinetica.solve_graph(
        graph_name = GRAPH_S,
        solver_type = "BACKHAUL_ROUTING",
        source_nodes = fixed_assets,
        destination_nodes = remote_assets,
        solution_table = TABLE_GRAPH_S_BSOLVED
    )

    print("Cost for each remote asset to travel to nearest fixed asset:")

    tabulate_records(
            kinetica,
            TABLE_GRAPH_S_BSOLVED,
            ["ST_STARTPOINT(wktroute)", "ST_ENDPOINT(wktroute)", "SOLVERS_NODE_COSTS"],
            ["Remote Asset", "Fixed Asset", "Cost (in seconds)"],
            ["ST_X(ST_ENDPOINT(wktroute))", "ST_Y(ST_ENDPOINT(wktroute))"],
            "psql"
    )

# end backhaul_example()


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
    parser = argparse.ArgumentParser(description='Run backhaul solve graph example.')
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
    backhaul_example()
