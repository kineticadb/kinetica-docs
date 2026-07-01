############################################################################
#                                                                          #
# Imports & Constants                                                      #
#                                                                          #
############################################################################

import argparse
import gpudb
import sys



CSV_FILE1 = "road_weights.csv"
CSV_FILE2 = "mm_raw_gps.csv"

OPTION_NO_DROP_ERROR = {"no_error_if_not_exists": "true"}
OPTION_NO_CREATE_ERROR = {"no_error_if_exists": "true"}

SCHEMA = "graph_m_seattle_markov"
TABLE_SRN = SCHEMA + ".seattle_road_network"
TABLE_GPS = SCHEMA + ".raw_gps_samples"
TABLE_SOLUTION1 = TABLE_SRN + "_match_solved"
TABLE_SOLUTION2 = TABLE_SOLUTION1 + "_w_filter_folding"

GRAPH_S = SCHEMA + ".seattle_road_network_graph"


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
    kdb.clear_table(table_name=TABLE_SRN, options=OPTION_NO_DROP_ERROR)
    kdb.clear_table(table_name=TABLE_GPS, options=OPTION_NO_DROP_ERROR)
  
    # Create the graph example schema, if it doesn't exist
    kdb.create_schema(SCHEMA, options=OPTION_NO_CREATE_ERROR)

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
            db = kdb,
            options = {}
        )
        print("{} table object successfully created.".format(TABLE_SRN))
    except gpudb.GPUdbException as e:
        print("{} table object creation failure: {}".format(TABLE_SRN, str(e)))

    # Insert records from a CSV file into the Seattle road network table
    csv_path = data_dir + "/" + CSV_FILE1
    print("Creating records from the " + CSV_FILE1 + " file.")
    kdb.create_directory("data", {"no_error_if_exists":"true"});
    kdb.upload_files("/data/" + CSV_FILE1, open(csv_path, "rb").read())
    kdb.insert_records_from_files(TABLE_SRN, ["kifs://data/" + CSV_FILE1])

    print("{} records inserted into {} table.\n".format(table_srn_obj.size(), TABLE_SRN))


    # Create the raw GPS samples table
    try:
        table_gps_obj = gpudb.GPUdbTable(
            _type = [
                ["datetime", "long"],
                ["lat", "double"],
                ["lon", "double"]
            ],
            name = TABLE_GPS,
            db = kdb,
            options = {}
        )
        print("{} table object successfully created.".format(TABLE_GPS))
    except gpudb.GPUdbException as e:
        print("{} table object creation failure: {}".format(TABLE_GPS, str(e)))

    # Insert records from a CSV file into the raw GPS samples table
    print("Creating records from the " + CSV_FILE2 + " file.")
    csv_path = data_dir + "/" + CSV_FILE2
    kdb.create_directory("data", {"no_error_if_exists":"true"});
    kdb.upload_files("/data/" + CSV_FILE2, open(csv_path, "rb").read())
    kdb.insert_records_from_files(TABLE_GPS, ["kifs://data/" + CSV_FILE2])

    print("{} records inserted into {} table.\n".format(table_gps_obj.size(), TABLE_GPS))

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
    create_s_graph_response = kdb.create_graph(
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
# Match Graph Function                                                     #
#                                                                          #
############################################################################

def match_graph_example():
    """Demonstrate matching a graph ..."""

    print("\n====================")
    print("MATCH GRAPH EXAMPLES")
    print("====================\n")

    # Clear any related tables in case they already exist
    kdb.clear_table(table_name=TABLE_SOLUTION1, options=OPTION_NO_DROP_ERROR)
    kdb.clear_table(table_name=TABLE_SOLUTION2, options=OPTION_NO_DROP_ERROR)

    # Match the samples found in TABLE_GPS to GRAPH_S to determine the mean
    # square error score
    print("Matching {} to {} using the markov_chain solver type.".format(TABLE_GPS, GRAPH_S))
    match_s_graph_response = kdb.match_graph(
        graph_name = GRAPH_S,
        sample_points = [
            TABLE_GPS + ".lon AS X",
            TABLE_GPS + ".lat AS Y",
            TABLE_GPS + ".datetime AS TIME"
        ],
        solve_method = "markov_chain",
        solution_table = TABLE_SOLUTION1,
        options = {}
    )
    print("Score for how well the samples matched to the graph (closer to 0 is better): {:1.15f}\n".format(
        match_s_graph_response["match_score"]
    ))

    print("Matching {} to {} using the markov_chain solver type but filtering out fold-over paths.".format(TABLE_GPS, GRAPH_S))
    match_s_graph_response = kdb.match_graph(
        graph_name = GRAPH_S,
        sample_points = [
            TABLE_GPS + ".lon AS X",
            TABLE_GPS + ".lat AS Y",
            TABLE_GPS + ".datetime AS TIME"
        ],
        solve_method = "markov_chain",
        solution_table = TABLE_SOLUTION2,
        options = {
            "filter_folding_paths": "true"
        }
    )
    print("Score for how well the samples matched to the graph with filter folding (closer to 0 is better): {:1.15f}".format(
        match_s_graph_response["match_score"]
    ))

# end match_graph_example()


if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Run Markov chain match graph example.')
    parser.add_argument('--url', default='http://127.0.0.1:9191', help='Kinetica URL to run example against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')
    parser.add_argument('--data_dir', default='./', help='Data file directory')

    args = parser.parse_args()

    # Establish connection with an instance of Kinetica, given a URL and credentials
    kdb = gpudb.GPUdb(host = [args.url], username = args.username, password = args.password)

    # Execute defined functions
    table_setup(args.data_dir)
    graph_setup()
    match_graph_example()
