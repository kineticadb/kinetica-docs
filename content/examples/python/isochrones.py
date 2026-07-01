############################################################################
#                                                                          #
# Imports                                                                  #
#                                                                          #
############################################################################

import argparse
import csv
import gpudb
import requests
import sys
import urllib

# Hack for urllib library parameter quoting in Python2/3
# WMS currently does not accept '+' as a proper URL encoding of ' '
try:
    urllib.quote_plus = urllib.quote
except:
    def urlencode(payload):
        return urllib.parse.urlencode(payload, quote_via=urllib.parse.quote)
    urllib.urlencode = urlencode


############################################################################
#                                                                          #
# Constants                                                                #
#                                                                          #
############################################################################

# Files
CSV_FILE = "dc_shape.csv"
CSV_ROW_SIZE = 192238

# Options
OPTION_NO_ERROR = {"no_error_if_not_exists": "true"}
OPTION_ISO = {"concavity_level": "0.2", "is_replicated": "true"}
OPTION_ISO_CONTOUR = {
    "adjust_grid": "false",
    "adjust_levels": "false",
    "gridding_method": "INV_DST_POW",
    "labels_font_size": "16",
    "labels_font_family": "Sans",
    "labels_search_window": "4",
    "grid_size": str(100),
    "min_grid_size": "10",
    "max_grid_size": "300",
    "search_radius": "9",
    "smoothing_factor": "0.000001",
    "color_isolines": "true",
    "width": "512", "height": "-1"
}
OPTION_ISO_STYLE = {
    "line_size": "2",
    "color": "0xFF000000",
    "bg_color": "0x00000000",
    "colormap": "jet",
    "text_color": "0xFF000000"
}

# Schema
SCHEMA = "tutorial_isochrones"

# Tables
TABLE_DC = SCHEMA + ".dc_shape"
TABLE_D_LVL = SCHEMA + ".dulles_levels"
TABLE_JOIN = SCHEMA + ".isochrones_shared_area"
TABLE_K_ISO_SOLVE = SCHEMA + ".to_kinetica_isochrones_solution"
TABLE_K_LVL1 = SCHEMA + ".from_kinetica_levels"
TABLE_K_LVL2 = SCHEMA + ".to_kinetica_levels"
TABLE_R_LVL = SCHEMA + ".reagan_levels"

# Graphs
GRAPH_DC = TABLE_DC + "_graph"

# Source nodes
D_AIR = "POINT(-77.446831 38.955309)"
K_HQ = "POINT(-77.115203 38.881578)"
R_AIR = "POINT(-77.042295 38.849684)"

# Images
D_AIR_IMG = TABLE_D_LVL + ".png"
K_HQ_IMG1 = TABLE_K_LVL1 + ".png"
K_HQ_IMG2 = TABLE_K_LVL2 + ".png"
R_AIR_IMG = TABLE_R_LVL + ".png"

############################################################################
#                                                                          #
# Table Validation Function                                                #
#                                                                          #
############################################################################


def table_validation():

    print("TABLE VALIDATION")
    print("================\n")

    # Check to see if TABLE_DC exists already; if it does, skip ingesting from
    # CSV.
    print("Checking to see if {} table exists:".format(TABLE_DC))
    has_table_dc_resp = kinetica.has_table(table_name=TABLE_DC)
    if has_table_dc_resp["table_exists"]:

        print("{} table exists!".format(TABLE_DC))

        # If the table exists, check its size to ensure it matches the local CSV
        # file's size.
        show_table_dc_resp = kinetica.show_table(
          table_name=TABLE_DC,
          options={"get_sizes": "true"}
        )

        if show_table_dc_resp["total_size"] == CSV_ROW_SIZE:

            print("Size of {} table is correct. Proceeding with graph "
                  "setup.\n".format(TABLE_DC))
            graph_setup()

        else:

            print("Size of {} table is not correct. Proceeding with "
                  "ingestion.\n".format(TABLE_DC))
            table_setup()

    else:

        print("{} table doesn't exist. Proceeding with "
              "ingestion.\n".format(TABLE_DC))
        table_setup()

# end table_validation()

############################################################################
#                                                                          #
# Table Setup Function                                                     #
#                                                                          #
############################################################################


def table_setup(data_dir):

    print("\n===========")
    print("TABLE SETUP")
    print("===========\n")

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_DC, options=OPTION_NO_ERROR)

    # Create the isochrones tutorial schema
    kinetica.create_schema(SCHEMA, options=OPTION_NO_ERROR)
    
    # Create TABLE_DC
    try:
        table_dc_obj = gpudb.GPUdbTable(
            _type = [
                ["link_id", "long", "shard_key"],
                ["direction", "int"],
                ["speed", "double"],
                ["road_type", "string", "char1"],
                ["seg", "string", "wkt"],
                ["shape", "string", "wkt"]
            ],
            name = TABLE_DC,
            db = kinetica,
            options = {}
        )
        print("{} table object successfully created.\n".format(TABLE_DC))
    except gpudb.GPUdbException as e:
        print("{} table object creation failure: \n\t{} \nExiting".format(TABLE_DC, str(e)))
        sys.exit()

    # Insert records from a CSV File into the TABLE_DC table via KiFS
    csv_path = data_dir + "/" + CSV_FILE
    print("Creating records from the " + csv_path + " file.")
    kinetica.create_directory("data", {"no_error_if_exists":"true"});
    kinetica.upload_files("/data/" + CSV_FILE, open(csv_path, "rb").read())
    kinetica.insert_records_from_files(TABLE_DC, ["kifs://data/" + CSV_FILE])

    print("{} records inserted into {} table.".format(table_dc_obj.size(), TABLE_DC))

# end table_setup()

############################################################################
#                                                                          #
# Graph Setup Function                                                     #
#                                                                          #
############################################################################


def graph_setup():

    print("\n===========")
    print("GRAPH SETUP")
    print("===========\n")

    # Create a graph from TABLE_DC
    print("Creating {}".format(GRAPH_DC))
    create_graph_dc_resp = kinetica.create_graph(
        graph_name = GRAPH_DC,
        directed_graph = True,
        nodes = [],
        edges = [
            TABLE_DC + ".direction AS DIRECTION",
            TABLE_DC + ".shape AS WKTLINE"
        ],
        weights = [
            TABLE_DC + ".direction AS EDGE_DIRECTION",
            TABLE_DC + ".shape AS EDGE_WKTLINE",
            "ST_LENGTH(" + TABLE_DC + ".shape,1)/" + TABLE_DC + ".speed AS VALUESPECIFIED"
        ],
        restrictions = [],
        options = {"recreate": "true"}
    )
    if create_graph_dc_resp["status_info"]["status"] == "OK":
        print("{} creation success!".format(GRAPH_DC))
        print("Number of nodes: {}".format(create_graph_dc_resp["num_nodes"]))
        print("Number of edges: {}".format(create_graph_dc_resp["num_edges"]))
    else:
        print("{} creation failure: \n\t{}".format(
            GRAPH_DC,
            create_graph_dc_resp["status_info"]["message"]
        ))
        print("Exiting...")
        sys.exit()
  
# end graph_setup()

############################################################################
#                                                                          #
# Visualize Isochrone Example Function                                     #
#                                                                          #
############################################################################


def visualize_isochrone_example():

    print("\n===========================")
    print("VISUALIZE ISOCHRONE EXAMPLE")
    print("===========================\n")

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_D_LVL, options=OPTION_NO_ERROR)
    kinetica.clear_table(table_name=TABLE_K_LVL1, options=OPTION_NO_ERROR)
    kinetica.clear_table(table_name=TABLE_R_LVL, options=OPTION_NO_ERROR)
    kinetica.clear_table(table_name=TABLE_JOIN, options=OPTION_NO_ERROR)

    # Contour options parameters
    OPTION_ISO_CONTOUR["add_labels"] = "true"
    OPTION_ISO_CONTOUR["projection"] = "web_mercator"

    # Isochrone options parameters
    OPTION_ISO["solve_direction"] = "to_source"

    # Visualize isochrones leading to D_AIR
    print("Visualizing isochrones leading to {} using {} and outputting the "
          "results as an image:".format(D_AIR, GRAPH_DC))
    vis_isochrone_d_resp = kinetica.visualize_isochrone(
        graph_name = GRAPH_DC,
        source_node = D_AIR + " AS NODE_WKTPOINT",
        max_solution_radius = 40 * 60,
        num_levels = 1,
        generate_image = True,
        levels_table = TABLE_D_LVL,
        style_options = OPTION_ISO_STYLE,
        contour_options = OPTION_ISO_CONTOUR,
        options = OPTION_ISO
    )
    img = vis_isochrone_d_resp["image_data"]
    img_isochrones_to_dulles = open(D_AIR_IMG, "wb")
    img_isochrones_to_dulles.write(img)
    img_isochrones_to_dulles.close()
    print("Generated PNG file: {}\n".format(D_AIR_IMG))

    # Visualize isochrones leading to R_AIR
    print("Visualizing isochrones leading to {} using {} and outputting the "
          "results as an image:".format(R_AIR, GRAPH_DC))
    vis_isochrone_r_resp = kinetica.visualize_isochrone(
        graph_name = GRAPH_DC,
        source_node = R_AIR + " AS NODE_WKTPOINT",
        max_solution_radius = 25 * 60,
        num_levels = 1,
        generate_image = True,
        levels_table = TABLE_R_LVL,
        style_options = OPTION_ISO_STYLE,
        contour_options = OPTION_ISO_CONTOUR,
        options = OPTION_ISO
    )
    img = vis_isochrone_r_resp["image_data"]
    img_isochrones_to_reagan = open(R_AIR_IMG, "wb")
    img_isochrones_to_reagan.write(img)
    img_isochrones_to_reagan.close()
    print("Generated PNG file: {}\n".format(R_AIR_IMG))

    # Visualize isochrones leading out of K_HQ
    OPTION_ISO["solve_direction"] = "from_source"
    print("Visualizing isochrones leading from {} using {} and outputting the "
          "results as an image:".format(K_HQ, GRAPH_DC))
    vis_isochrone_k1_resp = kinetica.visualize_isochrone(
        graph_name = GRAPH_DC,
        source_node = K_HQ + " AS NODE_WKTPOINT",
        max_solution_radius = 10 * 60,
        num_levels = 1,
        generate_image = True,
        levels_table = TABLE_K_LVL1,
        style_options = OPTION_ISO_STYLE,
        contour_options = OPTION_ISO_CONTOUR,
        options = OPTION_ISO
    )
    img = vis_isochrone_k1_resp["image_data"]
    img_isochrones_from_kinetica = open(K_HQ_IMG1, "wb")
    img_isochrones_from_kinetica.write(img)
    img_isochrones_from_kinetica.close()
    print("Generated PNG file: {}\n".format(K_HQ_IMG1))

    print("Joining the isochrone solutions using ST_INTERSECTION to determine"
          " the shared area between them.")
    create_join_resp = kinetica.create_join_table(
        join_table_name = TABLE_JOIN,
        table_names = [
            TABLE_D_LVL + " AS DULLES",
            TABLE_K_LVL1 + " AS KINETICA",
            TABLE_R_LVL + " AS REAGAN"
        ],
        column_names = [
            "ST_INTERSECTION(REAGAN.Isochrones, ST_INTERSECTION(KINETICA.Isochrones, DULLES.Isochrones)) AS shared_isochrones"
        ],
        expressions = [],
        options = {}
    )
    if create_join_resp["status_info"]["status"] == "OK":
        print("{} creation success!".format(TABLE_JOIN))
    else:
        print("{} creation failure: \n\t{}".format(
            TABLE_JOIN,
            create_join_resp["status_info"]["message"]
        ))
        print("Exiting...")
        sys.exit()

# end visualize_isochrone_example()

############################################################################
#                                                                          #
# WMS Isochrone Example Function                                           #
#                                                                          #
############################################################################


def wms_isochrone_example(username, password):

    print("\n=====================")
    print("WMS ISOCHRONE EXAMPLE")
    print("=====================\n")

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_K_ISO_SOLVE, options=OPTION_NO_ERROR)
    kinetica.clear_table(table_name=TABLE_K_LVL2, options=OPTION_NO_ERROR)

    # Prepare WMS payload dictionary
    payload = {
        # Standard WMS Parameters
        "request": "GetMap",
        "version": "1.1.1",
        "format": "image/png",
        "styles": "isochrone",
        "image_width": 512,
        "image_height": -1,

        # Isochrone parameters
        "graph_name": GRAPH_DC,
        "source_node": K_HQ + " AS NODE_WKTPOINT",
        "max_solution_radius": "900",
        "num_levels": "10",
        "generate_image": "true",
        "levels_table": TABLE_K_LVL2,

        # Isochrone style options parameters
        "line_size": OPTION_ISO_STYLE["line_size"],
        "color": OPTION_ISO_STYLE["color"][2:],  # remove the 0x
        "bg_color": OPTION_ISO_STYLE["bg_color"][2:],  # remove the 0x
        "colormap": OPTION_ISO_STYLE["colormap"],

        # Isochrone contour options parameters
        "projection": "plate_carree",
        "search_radius": OPTION_ISO_CONTOUR["search_radius"],
        "color_isolines": OPTION_ISO_CONTOUR["color_isolines"],
        "add_labels": "false",
        
        # Contour parameters
        "gridding_method": OPTION_ISO_CONTOUR["gridding_method"],
        "smoothing_factor": OPTION_ISO_CONTOUR["smoothing_factor"],
        "max_search_cells": "100",
        "min_grid_size": OPTION_ISO_CONTOUR["min_grid_size"],
        "max_grid_size": OPTION_ISO_CONTOUR["max_grid_size"],

        # Isochrone options parameters
        "solve_table": TABLE_K_ISO_SOLVE,
        "is_replicated": OPTION_ISO["is_replicated"],
        "concavity_level": OPTION_ISO["concavity_level"],
        "solve_direction": "to_source"
    }
    print("Calling the isochrone style via the /wms endpoint and outputting the results as an image:")
    params = urllib.urlencode(payload)
    call_wms_request = requests.get(WMS_URL, auth=(username, password), params=params)
    wms_img = call_wms_request.content
    if wms_img[1:4] != "PNG" and wms_img[1:4] != b"PNG":     # Python2/3 compensation
        print("WMS call failure: \n\t{}".format(call_wms_request.content))
        print("Exiting...")
        sys.exit()
    else:
        print("WMS call success!")
        img_isochrones_to_kinetica = open(K_HQ_IMG2, "wb")
        img_isochrones_to_kinetica.write(wms_img)
        img_isochrones_to_kinetica.close()
        print("Generated PNG file: {}\n".format(K_HQ_IMG2))

# end wms_isochrone_example()


if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Run isochrones examples.')
    parser.add_argument('--url', default='http://127.0.0.1:9191', help='Kinetica URL to run examples against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')
    parser.add_argument('--data_dir', default='./', help='Data file directory')

    args = parser.parse_args()


    INTRO = """
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+                                                                              +
+                             ISOCHRONES EXAMPLES                              +                             
+                                                                              +
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    """
    print(INTRO)

    # Establish connection with an instance of Kinetica, given a URL and credentials
    try:
        kinetica = gpudb.GPUdb(host = [args.url], username = args.username, password = args.password)
        WMS_URL = args.url + "/wms"
    except gpudb.GPUdbException as connect_error:
        print("Error: \n\t{} \nExiting".format(str(connect_error)))
        sys.exit()

    # Execute
    table_setup(args.data_dir)
    graph_setup()
    visualize_isochrone_example()
    wms_isochrone_example(args.username, args.password)
