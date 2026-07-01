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

CSV_FILE = "nyc_neighborhood.csv"

OPTION_NO_DROP_ERROR = {"no_error_if_not_exists": "true"}
OPTION_NO_CREATE_ERROR = {"no_error_if_exists": "true"}

SCHEMA = "graph_s_pagerank"
TABLE_NYC_N = SCHEMA + ".nyc_neighborhood"
TABLE_TAXI = "demo.nyctaxi"
TABLE_TAXI_E = SCHEMA + ".nyctaxi_edges_id"
TABLE_TAXI_N = SCHEMA + ".nyctaxi_nodes"
TABLE_TAXI_N_S = TABLE_TAXI_N + "_sharded"

JOIN_TAXI = SCHEMA + ".taxi_tables_joined"
JOIN_PR_RESULTS = SCHEMA + ".page_rank_results_joined"

GRAPH_T = SCHEMA + ".nyctaxi_graph_id"
TABLE_GRAPH_T_PRSOLVED = GRAPH_T + "_page_rank_solved"
TABLE_GRAPH_T_PRSOLVED_S = TABLE_GRAPH_T_PRSOLVED + "_sharded"


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
    kinetica.clear_table(table_name=JOIN_TAXI, options=OPTION_NO_DROP_ERROR)
    kinetica.clear_table(table_name=TABLE_NYC_N, options=OPTION_NO_DROP_ERROR)
    kinetica.clear_table(table_name=TABLE_TAXI_E, options=OPTION_NO_DROP_ERROR)
    kinetica.clear_table(table_name=TABLE_TAXI_N, options=OPTION_NO_DROP_ERROR)

    # Create the graph example schema, if it doesn't exist
    kinetica.create_schema(SCHEMA, options=OPTION_NO_CREATE_ERROR)

    # Create the NYC neighborhood table
    try:
        table_nycn_obj = gpudb.GPUdbTable(
            _type = [
                ["gid", "int"],
                ["geom", "string", "wkt"],
                ["CTLabel", "string", "char16"],
                ["BoroCode", "string", "char16"],
                ["BoroName", "string", "char16"],
                ["CT2010", "string", "char16"],
                ["BoroCT2010", "string", "char16"],
                ["CDEligibil", "string", "char16"],
                ["NTACode", "string", "char16"],
                ["NTAName", "string", "char64"],
                ["PUMA", "string", "char16"],
                ["Shape_Leng", "double"],
                ["Shape_Area", "double"]
            ],
            name = TABLE_NYC_N,
            db = kinetica,
            options = {"is_replicated": "true"}
        )
        print("{} table object successfully created.".format(TABLE_NYC_N))
    except gpudb.GPUdbException as e:
        print("{} table object creation failure: {}".format(TABLE_NYC_N, str(e)))

    # Insert records from a CSV file into the NYC neighborhood table
    csv_path = data_dir + "/" + CSV_FILE
    print("Creating records from the " + CSV_FILE + " file.")
    kinetica.create_directory("data", {"no_error_if_exists":"true"});
    kinetica.upload_files("/data/" + CSV_FILE, open(csv_path, "rb").read())
    kinetica.insert_records_from_files(TABLE_NYC_N, ["kifs://data/" + CSV_FILE])

    print("{} records inserted into {} table.\n".format(table_nycn_obj.size(), TABLE_NYC_N))

    # Check to see if 'nyctaxi' table exists
    print("Checking to see if table {} exists.".format(TABLE_TAXI))
    if kinetica.has_table(table_name=TABLE_TAXI)['table_exists']:
        print("Table {} exists.".format(TABLE_TAXI))
    else:
        print("Table {} does not exist. Please ingest the NYCTaxi data set and try again.".format(TABLE_TAXI))
        sys.exit(1)
    print("")

    # Join the TABLE_TAXI table to the TABLE_NYC_N table using STXY_CONTAINS
    # to filter out data that could skew the graph
    print("Joining {} to {} to filter out data that could skew the taxi graphs.".format(TABLE_TAXI, JOIN_TAXI))
    join_taxi_tables_response = kinetica.create_join_table(
        join_table_name = JOIN_TAXI,
        table_names = [TABLE_TAXI + " as t", TABLE_NYC_N + " as n"],
        column_names = [
            "CONCAT(CHAR32(pickup_longitude), CHAR32(pickup_latitude)) as pickup_name",
            "t.pickup_longitude", 
            "t.pickup_latitude",
            "HASH(t.pickup_longitude + t.pickup_latitude) as pickup_id",
            "CONCAT(CHAR32(dropoff_longitude), CHAR32(dropoff_latitude)) as dropoff_name",
            "t.dropoff_longitude", 
            "t.dropoff_latitude",
            "HASH(t.dropoff_longitude + t.dropoff_latitude) as dropoff_id",
            "t.total_amount"
        ],
        expressions = [
            "(STXY_CONTAINS(n.geom, t.pickup_longitude, t.pickup_latitude)) AND"
            "(STXY_CONTAINS(n.geom, t.dropoff_longitude, t.dropoff_latitude)) "
        ]
    )["status_info"]["status"]
    print("{} view created: {}".format(JOIN_TAXI, join_taxi_tables_response))
    print("")

    # Union the JOIN_TAXI view to itself to collapse pickup & dropoff
    # locations into a unified set of endpoint locations to serve as node IDs
    print("Unioning {} to itself contain the graph's nodes.".format(JOIN_TAXI))
    nodes_response = kinetica.execute_sql(
        statement = (
            "CREATE TABLE " + TABLE_TAXI_N + " AS "
            "SELECT "
                  "pickup_id as id, "
                  "pickup_longitude as lon, "
                  "pickup_latitude as lat "
            "FROM " + JOIN_TAXI + " "
            "UNION "
            "SELECT "
                  "dropoff_id, "
                  "dropoff_longitude, "
                  "dropoff_latitude "
            "FROM " + JOIN_TAXI
        ),
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        encoding = "json",
        options = {}
    )["status_info"]["status"]
    print("{} union created: {}".format(TABLE_TAXI_N, nodes_response))
    print("")

    # Create a projection to contain the graph edges (based on NODE_ID)
    print("Creating a projection from {} to contain the graph's edges.".format(JOIN_TAXI))
    edges_id_response = kinetica.create_projection(
        table_name = JOIN_TAXI,
        projection_name = TABLE_TAXI_E,
        column_names = ["pickup_id", "dropoff_id"]
    )["status_info"]["status"]
    print("{} projection created: {}".format(TABLE_TAXI_E, edges_id_response))

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

    # Create a graph from TABLE_TAXI_N and TABLE_TAXI_E using IDs
    print("Creating {}".format(GRAPH_T))
    create_t_graph_response = kinetica.create_graph(
        graph_name = GRAPH_T,
        directed_graph = False,
        nodes = [
            TABLE_TAXI_N + ".id AS ID"
        ],
        edges = [
            TABLE_TAXI_E + ".pickup_id AS NODE1_ID",
            TABLE_TAXI_E + ".dropoff_id AS NODE2_ID"
        ],
        weights = [],
        restrictions = [],
        options = {
            "recreate": "true"
        }
    )
    if create_t_graph_response["status_info"]["status"] == "OK":
        print("{} creation success!".format(GRAPH_T))
        print("Number of nodes: {}".format(create_t_graph_response["num_nodes"]))
        print("Number of edges: {}".format(create_t_graph_response["num_edges"]))
    else:
        print("{} creation failure: \n\t{}".format(
            GRAPH_T, 
            create_t_graph_response["status_info"]["message"]
        ))
        print("Exiting...")
        sys.exit()

# end graph_setup()

def page_rank_example():
    """Demonstrate creating and solving a graph using the PAGE_RANK method.
    """

    print("\n========================")
    print("PAGE RANK SOLVER EXAMPLE")
    print("========================\n")

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_GRAPH_T_PRSOLVED, options=OPTION_NO_DROP_ERROR)
    kinetica.clear_table(table_name=TABLE_TAXI_N_S, options=OPTION_NO_DROP_ERROR)
    kinetica.clear_table(table_name=TABLE_GRAPH_T_PRSOLVED_S, options=OPTION_NO_DROP_ERROR)
    kinetica.clear_table(table_name=JOIN_PR_RESULTS, options=OPTION_NO_DROP_ERROR)

    # Solve the graph
    print("Solving {} using PAGE_RANK solver type.".format(GRAPH_T))
    solve_pr_graph_response = kinetica.solve_graph(
        graph_name = GRAPH_T,
        solver_type = "PAGE_RANK",
        source_nodes = ["129341667930495514"],
        destination_nodes = [],
        solution_table = TABLE_GRAPH_T_PRSOLVED,
        options = {}
    )["status_info"]["status"]
    print("{} graph solved: {}".format(GRAPH_T, solve_pr_graph_response))
    print("")

    # Shard the TABLE_TAXI_N table so it can be joined to the Page Rank results
    # table
    nodes_sharded_response = kinetica.create_projection(
        table_name = TABLE_TAXI_N,
        projection_name = TABLE_TAXI_N_S,
        column_names = ["id", "lon", "lat"],
        options = {"shard_key": "id"}
    )["status_info"]["status"]
    print("{} projection created: {}".format(TABLE_TAXI_N_S, nodes_sharded_response))

    # Shard the Page Rank results table so it can be joined to the TABLE_TAXI_N
    # table
    graph_sharded_response = kinetica.create_projection(
        table_name = TABLE_GRAPH_T_PRSOLVED,
        projection_name = TABLE_GRAPH_T_PRSOLVED_S,
        column_names = ["SOLVERS_NODE_ID", "SOLVERS_NODE_COSTS"],
        options = {"shard_key": "SOLVERS_NODE_ID"}
    )["status_info"]["status"]
    print("{} projection created: {}".format(TABLE_GRAPH_T_PRSOLVED_S, graph_sharded_response))

    # Join the TABLE_TAXI_N_S and TABLE_GRAPH_T_PRSOLVED_S tables to pair the page
    # rank results IDs and costs with the longitude/latitude pair of each node
    join_pr_response = kinetica.create_join_table(
        join_table_name = JOIN_PR_RESULTS,
        table_names = [
            TABLE_TAXI_N_S + " as n",
            TABLE_GRAPH_T_PRSOLVED_S + " as s"
        ],
        column_names = [
            "n.lon", 
            "n.lat", 
            "s.SOLVERS_NODE_ID", 
            "s.SOLVERS_NODE_COSTS"
        ],
        expressions = ["n.id = s.SOLVERS_NODE_ID"],
        options = {}
    )["status_info"]["status"]
    print("{} join view created: {}".format(JOIN_PR_RESULTS, join_pr_response))
    print("")

    # Retrieve the top 10 nodes in terms of most visited point
    print("Top 10 nodes sorted by cost (highest to lowest):")

    tabulate_records(
            kinetica,
            JOIN_PR_RESULTS,
            ["lon", "lat", "SOLVERS_NODE_ID", "SOLVERS_NODE_COSTS"],
            ["Longitude", "Latitude", "ID", "Cost"],
            ["SOLVERS_NODE_COSTS DESC", "lon ASC"],
            "psql",
            10
    )

# end page_rank_example()


def tabulate_records(database, table_name, column_names, column_headers = None, order_by = None, tblfmt = "grid", limit = -9999):
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

        limit (int)
            Maximum number of records to display
    """

    options = {'order_by': ','.join(order_by)} if order_by is not None else {}
    resp = database.get_records_by_column_and_decode(
        table_name,
        column_names,
        limit = limit,
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
    parser = argparse.ArgumentParser(description='Run nyctaxi page rank solve graph example.')
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
    page_rank_example()
