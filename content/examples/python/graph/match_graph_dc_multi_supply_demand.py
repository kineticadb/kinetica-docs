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



CSV_FILE = "dc_roads.csv"

OPTION_NO_DROP_ERROR = {"no_error_if_not_exists": "true"}
OPTION_NO_CREATE_ERROR = {"no_error_if_exists": "true"}

SCHEMA = "graph_m_multi_supply_demand"
TABLE_DC = SCHEMA + ".dc_roads"
TABLE_D = SCHEMA + ".demands"
TABLE_S = SCHEMA + ".supplies"

GRAPH_DC = SCHEMA + ".dc_roads_graph"
TABLE_GRAPH_DC_S1 = GRAPH_DC + "_solved"
TABLE_GRAPH_DC_S2 = GRAPH_DC + "_solved_w_max_trip"

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
    kinetica.clear_table(table_name=TABLE_DC, options=OPTION_NO_DROP_ERROR)
    kinetica.clear_table(table_name=TABLE_D, options=OPTION_NO_DROP_ERROR)
    kinetica.clear_table(table_name=TABLE_S, options=OPTION_NO_DROP_ERROR)

    # Create the graph example schema, if it doesn't exist
    kinetica.create_schema(SCHEMA, options=OPTION_NO_CREATE_ERROR)

    # Create TABLE_DC
    try:
        table_dc_obj = gpudb.GPUdbTable(
            _type = [
                ["Feature_ID", "long"],
                ["osm_id", "string", "char16", "nullable"],
                ["code", "double", "nullable"],
                ["fclass", "string", "char32", "nullable"],
                ["name", "string", "char256", "nullable"],
                ["ref", "string", "char256", "nullable"],
                ["bidir", "string", "char2", "nullable"],
                ["maxspeed", "double", "nullable"],
                ["layer", "double", "nullable"],
                ["bridge", "string", "char2", "nullable"],
                ["tunnel", "string", "char2", "nullable"],
                ["WKT", "string", "wkt"],
                ["oneway", "int", "int8"],
                ["weight", "float"]
            ],
            name = TABLE_DC,
            db = kinetica,
            options = {}
        )
        print("{} table object successfully created.".format(TABLE_DC))
    except gpudb.GPUdbException as e:
        print("{} table object creation failure: {}".format(TABLE_DC, str(e)))

    # Insert records from a CSV File into the TABLE_DC table via KiFS
    csv_path = data_dir + "/" + CSV_FILE
    print("Creating records from the " + CSV_FILE + " file.")
    kinetica.create_directory("data", {"no_error_if_exists":"true"});
    kinetica.upload_files("/data/" + CSV_FILE, open(csv_path, "rb").read())
    kinetica.insert_records_from_files(TABLE_DC, ["kifs://data/" + CSV_FILE])

    print("{} records inserted into {} table.\n".format(table_dc_obj.size(), TABLE_DC))

    # Create TABLE_D
    try:
        table_d_obj = gpudb.GPUdbTable(
            _type = [
                ["store_id", "int", "int16"],
                ["store_location", "string", "wkt"],
                ["demand_size", "int", "int16"],
                ["supplier_id", "int", "int16"],
                ["priority", "int", "int16"]
            ],
            name = TABLE_D,
            db = kinetica,
            options = {}
        )
        print("{} table object successfully created.".format(TABLE_D))
    except gpudb.GPUdbException as e:
        print("{} table object creation failure: {}".format(TABLE_D, str(e)))

    # Define records and insert them into TABLE_D
    d_records = [
        [11, "POINT(-77.0297975 38.896235)", 35, 1, 0],
        [12, "POINT(-77.0286392 38.9169977)", 15, 1, 0],
        [13, "POINT(-77.00128239999999 38.8748973)", 40, 1, 1],
        [44, "POINT(-76.97952479999999 38.8995292)", 23, 1, 0],
        [45, "POINT(-77.026516 38.9408711)", 28, 1, 2],
        [46, "POINT(-77.0254317 38.8848442)", 25, 1, 3]
    ]
    table_d_obj.insert_records(d_records)
    print("{} records inserted into {} table.\n".format(table_d_obj.size(), TABLE_D))

    # Create TABLE_S
    try:
        table_s_obj = gpudb.GPUdbTable(
            _type = [
                ["supplier_id", "int", "int16"],
                ["supplier_location", "string", "wkt"],
                ["truck_id", "int", "int16"],
                ["truck_size", "int", "int16"]
            ],
            name = TABLE_S,
            db = kinetica,
            options = {}
        )
        print("{} table object successfully created.".format(TABLE_S))
    except gpudb.GPUdbException as e:
        print("{} table object creation failure: {}".format(TABLE_S, str(e)))

    # Define records and insert them into TABLE_S
    s_records = [
        [1, "POINT(-77.0440586 38.9089819)", 21, 50],
        [1, "POINT(-77.0440586 38.9089819)", 22, 50],
        [1, "POINT(-77.0440586 38.9089819)", 23, 30],
        [1, "POINT(-77.0440586 38.9089819)", 24, 20],
        [1, "POINT(-77.0440586 38.9089819)", 25, 16]
    ]
    table_s_obj.insert_records(s_records)
    print("{} records inserted into {} table.".format(table_s_obj.size(), TABLE_S))

# end table_setup()

############################################################################
#                                                                          #
# Graph Setup Function                                                     #
#                                                                          #
############################################################################


def graph_setup():
    """ Setup graph to be used in match example. """

    print("\n===========")
    print("GRAPH SETUP")
    print("===========\n")
    
    # Create a graph from TABLE_DC
    print("Creating {}".format(GRAPH_DC))
    create_dc_graph_response = kinetica.create_graph(
        graph_name = GRAPH_DC,
        directed_graph = True,
        nodes = [],
        edges = [
            TABLE_DC + ".WKT AS WKTLINE",
            TABLE_DC + ".oneway AS DIRECTION"
        ],
        weights = [
            TABLE_DC + ".WKT AS EDGE_WKTLINE",
            TABLE_DC + ".oneway AS EDGE_DIRECTION",
            TABLE_DC + ".weight AS VALUESPECIFIED"
        ],
        restrictions = [],
        options = {
            "recreate": "true"
        }
    )
    if create_dc_graph_response["status_info"]["status"] == "OK":
        print("{} creation success!".format(GRAPH_DC))
        print("Number of nodes: {}".format(create_dc_graph_response["num_nodes"]))
        print("Number of edges: {}".format(create_dc_graph_response["num_edges"]))
    else:
        print("{} creation failure: \n\t{}".format(
            GRAPH_DC,
            create_dc_graph_response["status_info"]["message"]
        ))
        print("Exiting...")
        sys.exit()

# end graph_setup()

############################################################################
#                                                                          #
# Multiple Supply Demand Solving Function                                  #
#                                                                          #
############################################################################


def multiple_supply_demand_example():
    """Demonstrate matching a graph using the MULTIPLE_SUPPLY_DEMAND method."""

    print("\n=========================================")
    print("MULTIPLE SUPPLY DEMAND SOLVER EXAMPLE # 1")
    print("=========================================\n")

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_GRAPH_DC_S1, options=OPTION_NO_DROP_ERROR)

    print("Matching demands to supply with priority via {}.\n".format(GRAPH_DC))
    try:
        match_graph_dc_resp = kinetica.match_graph(
            graph_name = GRAPH_DC,
            sample_points = [
                TABLE_D + ".store_id AS DEMAND_ID",
                TABLE_D + ".store_location AS DEMAND_WKTPOINT",
                TABLE_D + ".demand_size AS DEMAND_SIZE",
                TABLE_D + ".supplier_id AS DEMAND_REGION_ID",
                TABLE_D + ".priority AS PRIORITY",
                "",
                TABLE_S + ".supplier_id AS SUPPLY_REGION_ID",
                TABLE_S + ".supplier_location AS SUPPLY_WKTPOINT",
                TABLE_S + ".truck_id AS SUPPLY_ID",
                TABLE_S + ".truck_size AS SUPPLY_SIZE"
            ],
            solve_method = "match_supply_demand",
            solution_table = TABLE_GRAPH_DC_S1,
            options = {}
        )

        print("Cost for demand to be met by each supplier:")
    
        tabulate_records(
                kinetica,
                TABLE_GRAPH_DC_S1,
                ["SUPPLY_ID", "DEMAND_IDS", "DEMAND_DROPS", "COST"],
                ["Truck ID", "Store IDs", "Store Drops", "Cost"],
                ["COST"],
                "psql"
        )

        print("See {} table for route details.\n".format(TABLE_GRAPH_DC_S1))

    except gpudb.GPUdbException as match_error:
        print("{} graph match failure: \n\t{} \nExiting".format(match_graph_dc_resp, str(match_error)))
        sys.exit()

    print("=========================================")
    print("MULTIPLE SUPPLY DEMAND SOLVER EXAMPLE # 2")
    print("=========================================\n")

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_GRAPH_DC_S2, options=OPTION_NO_DROP_ERROR)

    print("Matching demands to supply with priority & max trip cost via {}.\n".format(GRAPH_DC))
    try:
        match_graph_dc_resp = kinetica.match_graph(
            graph_name = GRAPH_DC,
            sample_points = [
                TABLE_D + ".store_id AS DEMAND_ID",
                TABLE_D + ".store_location AS DEMAND_WKTPOINT",
                TABLE_D + ".demand_size AS DEMAND_SIZE",
                TABLE_D + ".supplier_id AS DEMAND_REGION_ID",
                TABLE_D + ".priority AS PRIORITY",
                "",
                TABLE_S + ".supplier_id AS SUPPLY_REGION_ID",
                TABLE_S + ".supplier_location AS SUPPLY_WKTPOINT",
                TABLE_S + ".truck_id AS SUPPLY_ID",
                TABLE_S + ".truck_size AS SUPPLY_SIZE"
            ],
            solve_method = "match_supply_demand",
            solution_table = TABLE_GRAPH_DC_S2,
            options = {
                "max_trip_cost": "0.6",
                "aggregated_output": "true"
            }
        )

        print("Cost for demand to be met by each supplier:")
    
        tabulate_records(
                kinetica,
                TABLE_GRAPH_DC_S2,
                ["SUPPLY_ID", "DEMAND_IDS", "DEMAND_DROPS", "COST"],
                ["Truck ID", "Store IDs", "Store Drops", "Cost"],
                ["COST"],
                "psql"
        )

        print("See {} table for route details.\n".format(TABLE_GRAPH_DC_S2))

    except gpudb.GPUdbException as match_error:
        print("{} graph match failure: \n\t{} \nExiting".format(match_graph_dc_resp, str(match_error)))
        sys.exit()

# end multiple_supply_demand_example()


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
    multiple_supply_demand_example()
