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
from operator import itemgetter


OPTION_NO_DROP_ERROR = {"no_error_if_not_exists": "true"}
OPTION_NO_CREATE_ERROR = {"no_error_if_exists": "true"}


############################################################################
#                                                                          #
# Table Setup Function                                                     #
#                                                                          #
############################################################################

def table_setup(kinetica, schema, people_table, knows_table):
    """ Setup necessary source tables for graph solver examples. """

    print("\n===========")
    print("TABLE SETUP")
    print("===========\n")

    # Clear related tables if they exists
    for t in people_table, knows_table:
        kinetica.clear_table(table_name=t, options=OPTION_NO_DROP_ERROR)

    # Create the graph example schema, if it doesn't exist
    kinetica.create_schema(schema, options=OPTION_NO_CREATE_ERROR)

    # Create the People table
    try:
        table_p_obj = gpudb.GPUdbTable(
            _type = [
                ["name", "string", "char16"],
                ["age", "int"],
                ["interest", "string", "char16"],
                ["gender", "string", "char8"]
            ],
            name = people_table,
            db = kinetica,
            options = {}
        )
        print("{} table object successfully created.".format(people_table))
    except gpudb.GPUdbException as e:
        print("{} table object creation failure: {}".format(people_table, str(e)))

    # Define records and insert them into the People table
    p_records = [
        ["Susan", 22, "dance", "female"],
        ["Bill", 60, "golf", "male"],
        ["Alex", 34, "chess", "male"],
        ["Jane", 40, "business", "female"],
        ["Tom", 29, "chess", "male"]
    ]
    table_p_obj.insert_records(p_records)
    print("{} records inserted into {} table.".format(table_p_obj.size(), people_table))

    # Create the Relation table
    try:
        table_k_obj = gpudb.GPUdbTable(
            _type = [
                ["name1", "string", "char16"],
                ["name2", "string", "char16"],
                ["since", "long"],
                ["relation", "string", "char32"]
            ],
            name = knows_table,
            db = kinetica,
            options = {}
        )
        print("{} table object successfully created.".format(knows_table))
    except gpudb.GPUdbException as e:
        print("{} table object creation failure: {}".format(knows_table, str(e)))

    # Define records and insert them into the Relation table
    k_records = [
        ["Jane", "Bill", 2010, "friend"],
        ["Bill", "Susan", 1990, "friend"],
        ["Bill", "Alex", 2001, "family"],
        ["Alex", "Tom", 2001, "friend"],
        ["Susan", "Alex", 2002, "friend"]
    ]
    table_k_obj.insert_records(k_records)
    print("{} records inserted into {} table.".format(table_k_obj.size(), knows_table))


# end table_setup()


############################################################################
#                                                                          #
# Graph Setup Function                                                     #
#                                                                          #
############################################################################

def graph_setup(kinetica, social_graph, people_table, knows_table):
    """ Setup graphs to be used in query examples. """

    print("\n===========")
    print("GRAPH SETUP")
    print("===========\n")

    # Create a graph from people & knows tables
    print("Creating {}".format(social_graph))
    create_s_graph_response = kinetica.create_graph(
        graph_name = social_graph,
        directed_graph = False,
        nodes = [
            people_table + ".name AS NAME",
            people_table + ".interest AS LABEL",
            "",
            people_table + ".name AS NAME",
            people_table + ".gender AS LABEL"
        ],
        edges = [
            knows_table + ".name1 AS NODE1_NAME",
            knows_table + ".name2 AS NODE2_NAME",
            knows_table + ".relation AS LABEL"
        ],
        weights = [],
        restrictions = [],
        options = {
            "recreate": "true",
            "graph_table": social_graph + "_table"
        }
    )
    if create_s_graph_response["status_info"]["status"] == "OK":
        print("{} creation success!".format(social_graph))
        print("Number of nodes: {}".format(create_s_graph_response["num_nodes"]))
        print("Number of edges: {}".format(create_s_graph_response["num_edges"]))
    else:
        print("{} creation failure: \n\t{}".format(
            social_graph, 
            create_s_graph_response["status_info"]["message"]
        ))
        print("Exiting...")
        sys.exit()

# end graph_setup()


############################################################################
#                                                                          #
# Query Graph Function                                                     #
#                                                                          #
############################################################################

def query_graph_example(kinetica, social_graph):
    """Demonstrate querying a graph using integer IDs."""

    print("\n=====================")
    print("QUERY GRAPH EXAMPLE 1")
    print("=====================\n")

    TABLE_Q1 = social_graph + "_queried_jane_to_chess"
    TABLE_Q1_TARGETS = TABLE_Q1 + "_nodes"

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_Q1, options=OPTION_NO_DROP_ERROR)
    kinetica.clear_table(table_name=TABLE_Q1_TARGETS, options=OPTION_NO_DROP_ERROR)

    # Query graph for nodes connected to 'Jane' where the node has an
    # interest in chess and they are not connected via 'family'
    print(
        "Querying {} for nodes connected to Jane where the node has an "
        "interest in chess and it is not connected via family".format(social_graph)
    )

    query1_s_graph_response = kinetica.query_graph(
        graph_name = social_graph,
        queries = [
            "{'Jane'} AS NODE_NAME",
            "",
            "{'chess'} AS TARGET_NODE_LABEL"
        ],
        restrictions = [
            "{'family'} AS EDGE_LABEL"
        ],
        adjacency_table = TABLE_Q1,
        rings = 4
    )
    if query1_s_graph_response["status_info"]["status"] == "OK":
        print("{} graph queried successfully.".format(social_graph))

        # Pretty print query results and targets
        print("\nQuery results for adjacency table {}:".format(TABLE_Q1))
        tabulate_records(kinetica, TABLE_Q1)
      
        print("\nQuery results for target nodes table {}:".format(TABLE_Q1_TARGETS))
        tabulate_records(kinetica, TABLE_Q1_TARGETS)
    else:
        print("{} graph query failure: \n\t{}".format(
            social_graph,
            query1_s_graph_response["status_info"]["message"]
        ))
        print("Exiting...")
        sys.exit()

    print("\n=====================")
    print("QUERY GRAPH EXAMPLE 2")
    print("=====================\n")

    TABLE_Q2 = social_graph + "_queried_males"
    TABLE_Q2_TARGETS = TABLE_Q2 + "_nodes"

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_Q2, options=OPTION_NO_DROP_ERROR)
    kinetica.clear_table(table_name=TABLE_Q2_TARGETS, options=OPTION_NO_DROP_ERROR)

    # Query graph for the nodes connected directly to 'males'
    print("Querying {} for nodes connected to directly to 'males'".format(social_graph))

    query2_s_graph_response = kinetica.query_graph(
        graph_name = social_graph,
        queries = [
            "{'male'} AS NODE_LABEL"
        ],
        restrictions = [],
        adjacency_table = TABLE_Q2,
        rings = 1
    )
    if query2_s_graph_response["status_info"]["status"] == "OK":
        print("{} graph queried successfully.".format(social_graph))

        # Pretty print query results and targets
        print("\nQuery results for adjacency table {}:".format(TABLE_Q2))
        tabulate_records(kinetica, TABLE_Q2, ["QUERY_NODE1_NAME", "QUERY_NODE2_NAME"])

        print("\nQuery results for target nodes table {}:".format(TABLE_Q2_TARGETS))
        tabulate_records(kinetica, TABLE_Q2_TARGETS, ["QUERY_NODE_NAME_TARGET"])
    else:
        print("{} graph query failure: \n\t{}".format(
            social_graph,
            query2_s_graph_response["status_info"]["message"]
        ))
        print("Exiting...")
        sys.exit()

    print("\n=====================")
    print("QUERY GRAPH EXAMPLE 3")
    print("=====================\n")

    TABLE_Q3 = social_graph + "_queried_females_or_chess"
    TABLE_Q3_TARGETS = TABLE_Q3 + "_nodes"

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_Q3, options=OPTION_NO_DROP_ERROR)
    kinetica.clear_table(table_name=TABLE_Q3_TARGETS, options=OPTION_NO_DROP_ERROR)

    # Query graph for 'female' nodes or nodes interested in 'chess'
    print("Querying {} for 'female' nodes or nodes interested in 'chess'.".format(social_graph))

    query3_s_graph_response = kinetica.query_graph(
        graph_name = social_graph,
        queries = [
            "{'female', 'chess'} AS NODE_LABEL",
        ],
        restrictions = [],
        adjacency_table = TABLE_Q3,
        rings = 0
    )
    if query3_s_graph_response["status_info"]["status"] == "OK":
        print("{} graph queried successfully.".format(social_graph))
        
        # Pretty print query results and targets
        print("\nQuery results for adjacency table {}:".format(TABLE_Q3))
        tabulate_records(kinetica, TABLE_Q3)

        print("\nQuery results for target nodes table {}:".format(TABLE_Q3_TARGETS))
        tabulate_records(kinetica, TABLE_Q3_TARGETS, ["QUERY_NODE_NAME_TARGET"])
    else:
        print("{} graph query failure: \n\t{}".format(
            social_graph,
            query3_s_graph_response["status_info"]["message"]
        ))
        print("Exiting...")
        sys.exit()

    print("\n=====================")
    print("QUERY GRAPH EXAMPLE 4")
    print("=====================\n")

    TABLE_Q4 = social_graph + "_queried_females_to_chess"
    TABLE_Q4_TARGETS = TABLE_Q4 + "_nodes"

    # Clear any related tables in case they already exist
    kinetica.clear_table(table_name=TABLE_Q4, options=OPTION_NO_DROP_ERROR)
    kinetica.clear_table(table_name=TABLE_Q4_TARGETS, options=OPTION_NO_DROP_ERROR)

    # Query graph for nodes connected to 'females' where the node has an
    # interest in chess
    print(
        "Querying {} for nodes connected to 'females' where the node has an "
        "interest in chess".format(social_graph)
    )
    
    query4_s_graph_response = kinetica.query_graph(
        graph_name = social_graph,
        queries = [
            "{'female'} AS NODE_LABEL",
            "",
            "{'chess'} AS TARGET_NODE_LABEL"
        ],
        restrictions = [],
        adjacency_table = TABLE_Q4,
        rings = 2
    )
    if query4_s_graph_response["status_info"]["status"] == "OK":
        print("{} graph queried successfully.".format(social_graph))
        
        # Pretty print query results and targets
        print("\nQuery results for adjacency table {}:".format(TABLE_Q4))
        tabulate_records(kinetica, TABLE_Q4, ["PATH_ID", "RING_ID", "QUERY_NODE1_NAME", "QUERY_NODE2_NAME"])

        print("\nQuery results for target nodes table {}:".format(TABLE_Q4_TARGETS))
        tabulate_records(kinetica, TABLE_Q4_TARGETS, ["QUERY_NODE_ID_SOURCE", "QUERY_NODE_ID_TARGET", "QUERY_NODE_NAME_SOURCE", "QUERY_NODE_NAME_TARGET", "RING_ID"])
    else:
        print("{} graph query failure: \n\t{}".format(
            social_graph,
            query4_s_graph_response["status_info"]["message"]
        ))
        print("Exiting...")
        sys.exit()
    print("")

# end query_graph_example()


def tabulate_records(db, table_name, column_names = ['*']):
    
    # Get records JSON
    t = gpudb.GPUdbTable(name = table_name, db = db)
    records = t.get_records_by_column(
        column_names = column_names,
        encoding = "json",
        get_column_major = False
    )

    if not records:
        print("No records found.")
    else:
        if column_names != ['*']:
            column_names.reverse()
            for column_name in column_names:
                records.sort(key=itemgetter(column_name))

        # Using tabulate, pretty print the 'rows' list with the keys as headers
        print(tabulate(records, headers="keys", tablefmt="grid"))

# end tabulate_records()



if __name__ == '__main__':

    DEFAULT_SCHEMA = "graph_q_social"

    # Set up args
    parser = argparse.ArgumentParser(description='Run query social graph examples.')
    parser.add_argument('--url', default='http://127.0.0.1:9191', help='Kinetica URL to run examples against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')
    parser.add_argument('--schema', default=DEFAULT_SCHEMA, help='Schema in which to create graph objects')

    args, unknown = parser.parse_known_args()

    # Establish connection with a locally-running instance of Kinetica
    kinetica = gpudb.GPUdb(host = [args.url], username = args.username, password = args.password)

    schema = args.schema

    people_table = 'people'
    knows_table = 'knows'
    social_graph = 'social_relationships'

    if schema:
        people_table = schema + '.' + people_table
        knows_table = schema + '.' + knows_table
        social_graph = schema + '.' + social_graph

    # Execute defined functions
    table_setup(kinetica, schema, people_table, knows_table)
    graph_setup(kinetica, social_graph, people_table, knows_table)
    query_graph_example(kinetica, social_graph)
