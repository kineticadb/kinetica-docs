"""This script walks through how to use the Python API.

Covered here: importing GPUdb, instantiating Kinetica, creating types, creating
tables, inserting records, retrieving records, updating records, altering
tables, filtering records, aggregating/grouping records, joining tables,
projections, unioning tables, and deleting records/tables.

"""

import argparse
import collections
import json
import gpudb
import csv


def gpudb_example(data_dir):

    print("")
    print("TUTORIAL OUTPUT")
    print("===============")

    CSV_FILE = "taxi_trip_data.csv"

    schema = "tutorial_python"

    # All tables/views used in examples below
    agg_grpby_union_all_src1 = schema + ".agg_passcount_tripdist_btw_apr1_apr15"
    agg_grpby_union_all_src2 = schema + ".agg_passcount_tripdist_btw_apr16_apr23"

    join_table_inner = schema + ".pay_info_rides_gt_3_pass"
    join_table_left = schema + ".all_vendor_transactions"
    join_table_outer = schema + ".vendors_w_no_transactions"

    projection_example1 = schema + ".credit_payment"
    projection_example2 = schema + ".long_lunch_time_rides"
    projection_except_src1 = schema + ".vendors_operating_before_noon"
    projection_except_src2 = schema + ".vendors_operating_after_noon"

    table_payment = schema + ".payment"
    table_taxi = schema + ".taxi_trip_data"
    table_taxi_replicated = schema + ".taxi_trip_data_replicated"
    table_vendor = schema + ".vendor"

    union_all_table = schema + ".passcount_tripdist_stats_apr"
    union_intersect_table = schema + ".shared_pickup_dropoff_points"
    union_except_table = schema + ".vendors_operating_btw_midnight_noon"

    view_example1 = schema + ".null_payments"
    view_example2 = schema + ".null_payments_gt_8"
    view_example3 = schema + ".nyc_ycab_vendors"
    view_example4 = schema + ".passenger_count_btw_1_3"


    print("\nCREATING SCHEMA, TYPES, & TABLES")
    print("--------------------------------\n")

    print("Tutorial Schema")
    print("***************")

    # Create a schema to house all tutorial database objects
    kdb.create_schema(schema)
    print("Tutorial schema successfully created\n")


    print("Vendor Table")
    print("************")

    # Create a type from a list of lists. Each list below is an individual
    # column. Each column comprises at least two values: a column name (always
    # the first value) and a base type (always the second value). Any
    # subsequent values are column properties. The order of the columns defines
    # the order in which values must be inserted into the table, e.g., a
    # "vendor_name" value cannot be inserted before a "vendor_id" value
    vendor_columns = [
        # column types and properties can be listed as strings
        ["vendor_id", "string", "char4", "primary_key"],
        ["vendor_name", "string", "char64"],
        ["phone", "string", "char16", "nullable"],
        ["email", "string", "char64", "nullable"],
        ["hq_street", "string", "char64"],
        # column properties can also be listed using the GPUdbColumnProperty
        # object
        [
            "hq_city",
            "string",
            gpudb.GPUdbColumnProperty.CHAR8,
            gpudb.GPUdbColumnProperty.DICT
        ],
        [
            "hq_state",
            "string",
            gpudb.GPUdbColumnProperty.CHAR8,
            gpudb.GPUdbColumnProperty.DICT
        ],
        ["hq_zip", "int"],
        ["num_emps", "int"],
        ["num_cabs", "int"]
    ]

    # Clear any existing table with the same name (otherwise we won"t be able
    # to create the table)
    no_error_option = {"no_error_if_not_exists": "true"}
    kdb.clear_table(table_name=table_vendor, options=no_error_option)

    # Create the table from the type and place it in a schema
    try:
        table_vendor_obj = gpudb.GPUdbTable(
            _type = vendor_columns,
            name = table_vendor,
            options = {"is_replicated": "true"},
            db = kdb
        )
        print("Vendor table successfully created")
    except gpudb.GPUdbException as e:
        print("Vendor table creation failure: {}".format(str(e)))
    print("")

    # Creation options could have been passed in as a GPUdbTableOptions object
    # instead:
    creation_options = gpudb.GPUdbTableOptions.default().is_replicated(True)

    # Demonstrate the way of acquiring a table object for an existing table
    table_vendor_obj = gpudb.GPUdbTable(_type=None, name=table_vendor, db=kdb)


    print("Payment Table")
    print("*************")

    payment_columns = [
        ["payment_id", "long", "primary_key"],
        ["payment_type", "string", "char16", "nullable"],
        ["credit_type", "string", "char16", "nullable"],
        ["payment_timestamp", "long", "timestamp", "nullable"],
        ["fare_amount", "double", "nullable"],
        ["surcharge", "double", "nullable"],
        ["mta_tax", "double", "nullable"],
        ["tip_amount", "double", "nullable"],
        ["tolls_amount", "double", "nullable"],
        ["total_amount", "double", "nullable"]
    ]

    # Clear any existing table with the same name (otherwise we won't be able
    # to create the table)
    kdb.clear_table(table_name=table_payment, options=no_error_option)

    # Create the table from the type and place it in a schema
    try:
        table_payment_obj = gpudb.GPUdbTable(_type=payment_columns, name=table_payment, db=kdb)
        print("Payment table successfully created")
    except gpudb.GPUdbException as e:
        print("Payment table creation failure: {}".format(str(e)))
    print("")

    print("Taxi Table")
    print("**********")

    taxi_columns = [
        ["transaction_id", "long", "primary_key"],
        ["payment_id", "long", "primary_key", "shard_key"],
        ["vendor_id", "string", "char4"],
        ["pickup_datetime", "long", "timestamp"],
        ["dropoff_datetime", "long", "timestamp"],
        ["passenger_count", "int", "int8"],
        ["trip_distance", "float"],
        ["pickup_longitude", "float"],
        ["pickup_latitude", "float"],
        ["dropoff_longitude", "float"],
        ["dropoff_latitude", "float"]
    ]

    # Clear any existing table with the same name (otherwise we won't be able
    # to create the table)
    kdb.clear_table(table_name=table_taxi, options=no_error_option)

    # Create the table from the type and place it in a schema
    try:
        table_taxi_obj = gpudb.GPUdbTable(_type=taxi_columns, name=table_taxi, db=kdb)
        print("Taxi table successfully created")
    except gpudb.GPUdbException as e:
        print("Taxi table creation failure: {}".format(str(e)))

    print("")
    print("\nINSERTING DATA")
    print("--------------\n")

    # Insert single record example
    # Create ordered dictionary for keys & values of record
    payment_datum = collections.OrderedDict()
    payment_datum["payment_id"] = 189
    payment_datum["payment_type"] = "No Charge"
    payment_datum["credit_type"] = None
    payment_datum["payment_timestamp"] = None
    payment_datum["fare_amount"] = 6.5
    payment_datum["surcharge"] = 0
    payment_datum["mta_tax"] = 0.6
    payment_datum["tip_amount"] = 0
    payment_datum["tolls_amount"] = 0
    payment_datum["total_amount"] = 7.1

    # Insert the record into the table
    table_payment_obj.insert_records(payment_datum)
    print("Number of records inserted into the Payment table:  {}".format(table_payment_obj.size()))
    payment_table_size_after_first_insert = table_payment_obj.size()

    # Insert multiple records examples
    # Create a list of in-line records. The order of the values must match the
    # column order in the type
    vendor_records = [
        ["VTS", "Vine Taxi Service", "9998880001", "admin@vtstaxi.com",
         "26 Summit St.", "Flushing", "NY", 11354, 450, 400],
        ["YCAB", "Yes Cab", "7895444321", None, "97 Edgemont St.", "Brooklyn",
         "NY", 11223, 445, 425],
        ["NYC", "New York City Cabs", None, "support@nyc-taxis.com",
         "9669 East Bayport St.", "Bronx", "NY", 10453, 505, 500],
        ["DDS", "Dependable Driver Service", None, None,
            "8554 North Homestead St.", "Bronx", "NY", 10472, 200, 124],
        ["CMT", "Crazy Manhattan Taxi", "9778896500",
         "admin@crazymanhattantaxi.com", "950 4th Road Suite 78", "Brooklyn",
         "NY", 11210, 500, 468],
        ["TNY", "Taxi New York", None, None, "725 Squaw Creek St.", "Bronx",
         "NY", 10458, 315, 305],
        ["NYMT", "New York Metro Taxi", None, None, "4 East Jennings St.",
         "Brooklyn", "NY", 11228, 166, 150],
        ["5BTC", "Five Boroughs Taxi Co.", "4566541278", "mgmt@5btc.com",
         "9128 Lantern Street", "Brooklyn", "NY", 11229, 193, 175]
    ]

    # Insert the records into the Vendor table
    table_vendor_obj.insert_records(vendor_records)

    print("Number of records inserted into the Vendor table:  {}".format(table_vendor_obj.size()))

    # Create another list of in-line records
    payment_records = [
        [136, "Cash", None, 1428716521000, 4, 0.5, 0.5, 1, 0, 6.3],
        [148, "Cash", None, 1430124581000, 9.5, 0, 0.5, 1, 0, 11.3],
        [114, "Cash", None, 1428259673000, 5.5, 0, 0.5, 1.89, 0, 8.19],
        [180, "Cash", None, 1428965823000, 6.5, 0.5, 0.5, 1, 0, 8.8],
        [109, "Cash", None, 1428948513000, 22.5, 0.5, 0.5, 4.75, 0, 28.55],
        [132, "Cash", None, 1429472779000, 6.5, 0.5, 0.5, 1.55, 0, 9.35],
        [134, "Cash", None, 1429472668000, 33.5, 0.5, 0.5, 0, 0, 34.8],
        [176, "Cash", None, 1428403962000, 9, 0.5, 0.5, 2.06, 0, 12.36],
        [100, "Cash", None, None, 9, 0, 0.5, 2.9, 0, 12.7],
        [193, "Cash", None, None, 3.5, 1, 0.5, 1.59, 0, 6.89],
        [140, "Credit", "Visa", None, 28, 0, 0.5, 0, 0, 28.8],
        [161, "Credit", "Visa", None, 7, 0, 0.5, 0, 0, 7.8],
        [199, "Credit", "Visa", None, 6, 1, 0.5, 1, 0, 8.5],
        [159, "Credit", "Visa", 1428674487000, 7, 0, 0.5, 0, 0, 7.8],
        [156, "Credit", "MasterCard", 1428672753000, 12.5, 0.5, 0.5, 0, 0, 13.8],
        [198, "Credit", "MasterCard", 1429472636000, 9, 0, 0.5, 0, 0, 9.8],
        [107, "Credit", "MasterCard", 1428717377000, 5, 0.5, 0.5, 0, 0, 6.3],
        [166, "Credit", "American Express", 1428808723000, 17.5, 0, 0.5, 0, 0, 18.3],
        [187, "Credit", "American Express", 1428670181000, 14, 0, 0.5, 0, 0, 14.8],
        [125, "Credit", "Discover", 1429869673000, 8.5, 0.5, 0.5, 0, 0, 9.8],
        [119, None, None, 1430431471000, 9.5, 0, 0.5, 0, 0, 10.3],
        [150, None, None, 1430432447000, 7.5, 0, 0.5, 0, 0, 8.3],
        [170, "No Charge", None, 1430431502000, 28.6, 0, 0.5, 0, 0, 28.6],
        [123, "No Charge", None, 1430136649000, 20, 0.5, 0.5, 0, 0, 21.3],
        [181, None, None, 1430135461000, 6.5, 0.5, 0.5, 0, 0, 7.8]
    ]

    # Insert the records into the Payment table
    for record in payment_records:
        table_payment_obj.insert_records(record)

    print("Number of records inserted into the Payment table:  {}".format(
        table_payment_obj.size() - payment_table_size_after_first_insert
    ))

    # Insert records from a CSV File into the Taxi table via KiFS
    csv_path = data_dir + "/" + CSV_FILE

    kdb.create_directory("data", {"no_error_if_exists":"true"});
    kdb.upload_files("/data/" + CSV_FILE, open(csv_path, "rb").read())
    kdb.insert_records_from_files(table_taxi, ["kifs://data/" + CSV_FILE])

    print("Number of records inserted into the Taxi table:  {}".format(table_taxi_obj.size()))

    print("")
    print("\nRETRIEVING DATA")
    print("---------------\n")

    # Retrieve no more than 10 records from the Payment table using the
    # GPUdbTable interface with binary encoding
    print("{:>10s} {:<12s} {:<11s} {:<17s} {:<11s} {:<9s} {:<7s} {:<10s} {:<12s} {:<12s}".format(
            "Payment ID", "Payment Type", "Credit Type", "Payment Timestamp", "Fare Amount",
            "Surcharge", "MTA Tax", "Tip Amount", "Tolls Amount", "Total Amount"
    ))
    print("{:=>10s} {:=<12s} {:=<11s} {:=<17s} {:=<11s} {:=<9s} {:=<7s} {:=<10s} {:=<12s} {:=<12s}".format(
            "", "", "", "", "", "", "", "", "", ""
    ))
    for record in table_payment_obj.get_records(
        offset = 0,
        limit = 10,
        encoding = "binary",
        options = {"sort_by": "payment_id"}
    ):
        print("{payment_id:>10d} {payment_type:<12s} {credit_type:<11s} {payment_timestamp:>17} " \
            "{fare_amount:11.2f} {surcharge:9.2f} {mta_tax:7.2f} {tip_amount:10.2f} " \
            "{tolls_amount:12.2f} {total_amount:12.2f}".format(
                payment_id=record["payment_id"],
                payment_type=(record["payment_type"] or ""),
                credit_type=(record["credit_type"] or ""),
                payment_timestamp=(record["payment_timestamp"] or ""),
                fare_amount=record["fare_amount"],
                surcharge=record["surcharge"],
                mta_tax=record["mta_tax"],
                tip_amount=record["tip_amount"],
                tolls_amount=record["tolls_amount"],
                total_amount=record["total_amount"]
        ))
    print("")

    # Retrieve all records from the Vendor table using the GPUdb interface with JSON encoding
    print("{:<9s} {:<26s} {:<11s} {:<29s} {:<24s} {:<8s} {:<8s} {:<6s} {:<11s} {:<6s}".format(
            "Vendor ID", "Vendor Name", "Phone", "Email", "HQ Street",
            "HQ City", "HQ State", "HQ Zip", "# Employees", "# Cabs"
    ))
    print("{:=<9s} {:=<26s} {:=<11s} {:=<29s} {:=<24s} {:=<8s} {:=<8s} {:=<6s} {:=<11s} {:=<6s}".format(
            "", "", "", "", "", "", "", "", "", ""
    ))
    vendor_records_gpudb = kdb.get_records(
        table_name = table_vendor,
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        encoding = "json",
        options = {"sort_by": "vendor_id"}
    )["records_json"]
    for record in vendor_records_gpudb:
        rec = json.loads(record)
        rec["phone"] = rec["phone"] or ""
        rec["email"] = rec["email"] or ""
        print("{vendor_id:<9s} {vendor_name:<26s} {phone:<11} {email:<29s} {hq_street:<24s} " \
            "{hq_city:<8s} {hq_state:<8s} {hq_zip:<6d} {num_emps:11d} {num_cabs:6d}".format(**rec))

    print("")
    print("\nUPDATING RECORDS")
    print("----------------\n")

    # Update the e-mail of, and add two employees and one cab to, the DDS vendor
    table_vendor_obj.update_records(
        expressions = ["vendor_id = 'DDS'"],
        new_values_maps = {
            "email": "'management@ddstaxico.com'",
            "num_emps": "num_emps + 2",
            "num_cabs": "num_cabs + 1"
        },
        options = {"use_expressions_in_new_values_maps":"true"}
    )

    # Print the updated table
    print("Updated DDS vendor information:")
    print("{:<9s} {:<25s} {:<5s} {:<24s} {:<24} {:<7s} {:<8s} {:<6s} {:<11s} {:<6s}".format(
            "Vendor ID",
            "Vendor Name",
            "Phone",
            "Email",
            "HQ Street",
            "HQ City",
            "HQ State",
            "HQ Zip",
            "# Employees",
            "# Cabs"
    ))
    print("{:=<9s} {:=<25s} {:=<5s} {:=<24s} {:=<24s} {:=<7s} {:=<8s} {:=<6s} {:=<11s} {:=<6s}".format(
            "", "", "", "", "", "", "", "", "", ""
    ))
    for vendor_record in table_vendor_obj.get_records(
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        options = {"expression": "vendor_id = 'DDS'"}
    ):
        print("{vendor_id:<9s} {vendor_name:<25s} {phone:<5s} {email:<24s} {hq_street:<24s} " \
            "{hq_city:<7s} {hq_state:<8s} {hq_zip:<6d} {num_emps:11d} {num_cabs:6d}".format(
                vendor_id=vendor_record["vendor_id"],
                vendor_name=vendor_record["vendor_name"],
                phone=(vendor_record["phone"] or ""),
                email=vendor_record["email"],
                hq_street=vendor_record["hq_street"],
                hq_city=vendor_record["hq_city"],
                hq_state=vendor_record["hq_state"],
                hq_zip=vendor_record["hq_zip"],
                num_emps=vendor_record["num_emps"],
                num_cabs=vendor_record["num_cabs"]
        ))

    print("")
    print("\nDELETING RECORDS")
    print("----------------\n")

    # Delete payment 189
    pre_delete = table_payment_obj.size()
    print("Records in the payment table (before delete): {}".format(pre_delete))
    delete_expr = ["payment_id = 189"]
    print("Deleting record where " + delete_expr[0])
    table_payment_obj.delete_records(expressions=delete_expr)
    post_delete = table_payment_obj.size()
    print("Records in the payment table (after delete): {}".format(post_delete))

    print("")
    print("\nALTER TABLE")
    print("-----------\n")

    print("Indexes")
    print("*******")

    # Add column indexes on:
    #   - payment table, fare_amount (for query-chaining filter example)
    #   - taxi table, passenger_count (for filter-by-range example)
    table_payment_obj.alter_table(action="create_index", value="fare_amount")
    table_taxi_obj.alter_table(action="create_index", value="passenger_count")

    print("Indexes added successfully\n")

    print("Dictionary Encoding")
    print("*******************")

    # Display memory usage before dictionary encoding
    pre_dict_mem_usage = json.loads(table_taxi_obj.show_table(
        options = {"get_column_info": "true"}
    )["additional_info"][0]["column_info"])["vendor_id"]["memory_usage"]

    print("Memory usage (in bytes) for 'vendor_id' column before adding " \
        "dictionary encoding: {}".format(pre_dict_mem_usage))

    # Apply dictionary encoding to the vendor_id column
    at_resp = table_taxi_obj.alter_table(
        action = "change_column",
        value = "vendor_id",
        options = {"column_properties": "char4,dict"}
    )

    print("Dictionary encoding added to 'vendor_id' column properties " \
        "list:  [{}]".format(", ".join(at_resp["properties"]["vendor_id"])))

    # Display memory usage after dictionary encoding
    post_dict_mem_usage = json.loads(table_taxi_obj.show_table(
        options = {"get_column_info": "true"}
    )["additional_info"][0]["column_info"])["vendor_id"]["memory_usage"]

    print("Memory usage (in bytes) for 'vendor_id' column after adding " \
        "dictionary encoding: {}".format(post_dict_mem_usage))

    print("")
    print("\nFILTERING")
    print("---------\n")

    # Clear any existing views with the same name (otherwise we won't be able
    # to create the views)
    kdb.clear_table(table_name=view_example1, options=no_error_option)
    kdb.clear_table(table_name=view_example2, options=no_error_option)
    kdb.clear_table(table_name=view_example3, options=no_error_option)
    kdb.clear_table(table_name=view_example4, options=no_error_option)

    # Filter Example 1
    # Filter for only payments with no corresponding payment type, returning the
    # count of records found; allow Kinetica to assign a random name to the view
    f1_count = table_payment_obj.filter(expression="IS_NULL(payment_type)").size()

    print("Number of null payments:  {}".format(f1_count))

    # Filter Example 2
    # Using GPUdbTable query chaining, filter null payment type records with a fare amount greater than 8
    f2_count = table_payment_obj.filter(
        view_name = view_example1, expression = "IS_NULL(payment_type)"
    ).filter(
        view_name = view_example2, expression = "fare_amount > 8"
    ).size()

    print("Number of null payments with a fare amount greater than $8.00 (with query chaining):  {}".format(f2_count))

    # Filter Example 3
    # Filter by list where vendor ID is either NYC or YCAB
    f3_count = table_taxi_obj.filter_by_list(
        view_name = view_example3, column_values_map = {"vendor_id": ["NYC", "YCAB"]}
    ).size()

    print("Number of records where vendor is either NYC or YCAB:  {}".format(f3_count))

    # Filter Example 4
    # Filter by range trip with passenger count between 1 and 3
    f4_count = table_taxi_obj.filter_by_range(
        view_name = view_example4, column_name = "passenger_count", lower_bound = 1, upper_bound = 3
    ).size()

    print("Number of trips with a passenger count between 1 and 3:  {}".format(f4_count))

    print("")
    print("\nAGGREGATING, GROUPING, & HISTOGRAMS")
    print("-----------------------------------\n")

    # Aggregate Example 1
    # Aggregate count, min, mean, and max on the trip distance
    a1_resp = table_taxi_obj.aggregate_statistics(
        column_name = "trip_distance",
        stats = "count,min,max,mean"
    )["stats"]

    print("Statistics of values in the trip_distance column:")
    print("\tCount: {count:5.0f}\n\tMin:   {min:5.2f}\n\tMean:  {mean:5.2f}\n\tMax:   {max:5.2f}\n" \
        "".format(**a1_resp))

    # Aggregate Example 2
    # Find unique taxi vendor IDs
    a2_resp = table_taxi_obj.aggregate_unique(
        column_name = "vendor_id",
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        encoding = "json"
    )["data"]["vendor_id"]

    print("Unique vendor IDs in the taxi trip table:")
    for vendor in a2_resp:
        print("\t* {}".format(vendor))
    print("")

    # Aggregate Example 3
    # Find number of trips per vendor
    a3_resp = table_taxi_obj.aggregate_group_by(
        column_names = ["vendor_id", "COUNT(vendor_id)"],
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        options = {"sort_by": "key"}
    )["data"]

    print("Trips per vendor:")
    for vendor in zip(a3_resp["vendor_id"], a3_resp["COUNT(vendor_id)"]):
        print("\t{:<6s} {:3d}".format(vendor[0] + ":", vendor[1]))
    print("")

    # Aggregate Example 4
    # Create a histogram for the different groups of passenger counts
    a4_resp = table_taxi_obj.aggregate_histogram(
        column_name = "passenger_count",
        start = 1,
        end = 6,
        interval = 1
    )["counts"]

    print("Passenger count groups by size:")
    print("{:<10s} {:<11s}".format("Passengers", "Total Trips"))
    print("{:=<10s} {:=<11s}".format("", ""))

    for histo_group in zip([1, 2, 3, 4, '>5'], a4_resp):
        print("{:>10} {:11.0f}".format(*histo_group))

    print("")
    print("\nJOINS")
    print("-----\n")

    # Clear any existing join views with the same name (otherwise we won't be
    # able to create the join views)
    kdb.clear_table(table_name=join_table_inner, options=no_error_option)
    kdb.clear_table(table_name=join_table_left, options=no_error_option)
    kdb.clear_table(table_name=table_taxi_replicated, options=no_error_option)
    kdb.clear_table(table_name=join_table_outer, options=no_error_option)

    # Join Example 1 (Inner Join)
    # Retrieve payment information for rides having more than three passengers
    gpudb.GPUdbTable.create_join_table(
        join_table_name = join_table_inner,
        table_names = [
            schema + ".taxi_trip_data as t",
            schema + ".payment as p"
        ],
        column_names = [
            "t.payment_id",
            "payment_type",
            "total_amount",
            "passenger_count",
            "vendor_id",
            "trip_distance"
        ],
        expressions = [
            "t.payment_id = p.payment_id",
            "passenger_count > 3"
        ],
        db = kdb
    )

    join_table_inner_obj = gpudb.GPUdbTable(_type = None, name = join_table_inner, db = kdb)

    j1_resp = join_table_inner_obj.get_records_by_column(
        column_names = [
            "payment_id",
            "payment_type",
            "total_amount",
            "passenger_count",
            "vendor_id",
            "trip_distance"
        ],
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        options = {"order_by":"payment_id"}
    )

    print("Payment information for rides having more than three passengers:")
    print("Payment ID Payment Type Total Amount Passenger Count Vendor ID Trip Distance")
    print("========== ============ ============ =============== ========= =============")
    for record in zip(
            j1_resp["payment_id"],
            j1_resp["payment_type"],
            j1_resp["total_amount"],
            j1_resp["passenger_count"],
            j1_resp["vendor_id"],
            j1_resp["trip_distance"]
    ):
        print("{:>10d} {:<12} {:12.2f} {:15d} {:<9s} {:13.2f}".format(
            record[0],
            record[1],
            round(record[2], 2),
            record[3],
            record[4],
            round(record[5], 2)
        ))
    print("")

    # Join Example 2 (Left Join)
    # Retrieve cab ride transactions and the full name of the associated vendor
    # (if available--blank if vendor name is unknown) for transactions with
    # associated payment data, sorting by increasing values of transaction ID.
    gpudb.GPUdbTable.create_join_table(
        join_table_name = join_table_left,
        table_names = [
            schema + ".taxi_trip_data as t",
            schema + ".vendor as v"
        ],
        column_names = [
            "transaction_id",
            "pickup_datetime",
            "trip_distance",
            "t.vendor_id",
            "vendor_name"
        ],
        expressions = [
            "LEFT JOIN t, v ON (t.vendor_id = v.vendor_id)",
            "payment_id <> 0"
        ],
        db = kdb
    )

    join_table_left_obj = gpudb.GPUdbTable(_type = None, name = join_table_left, db = kdb)

    j2_resp = join_table_left_obj.get_records_by_column(
        column_names = [
            "transaction_id",
            "pickup_datetime",
            "trip_distance",
            "vendor_id",
            "vendor_name"
        ],
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        options = {"order_by":"transaction_id"}
    )

    print("Transaction, trip, and vendor information where Payment ID is not null:")
    print("Transaction ID Pickup (in secs since Epoch) Trip Distance Vendor ID Vendor Name")
    print("============== ============================ ============= ========= ==================")
    for record in zip(
            j2_resp["transaction_id"],
            j2_resp["pickup_datetime"],
            j2_resp["trip_distance"],
            j2_resp["vendor_id"],
            j2_resp["vendor_name"]
    ):
        print("{:<14d} {:>28d} {:>13.2f} {:<9s} {:18s}".format(
            record[0],
            record[1],
            record[2],
            record[3],
            record[4] or ""
        ))
    print("")

    # Full outer joins require both tables to be replicated. Set merges like
    # Union Distinct, Intersect, and Except need to use replicated tables to
    # ensure the correct results. Create a replicated version of the taxi trip
    # data using create_projection.
    kdb.create_projection(
        table_name = table_taxi,
        projection_name = table_taxi_replicated,
        column_names = [
            "transaction_id",
            "payment_id",
            "vendor_id",
            "pickup_datetime",
            "dropoff_datetime",
            "passenger_count",
            "trip_distance",
            "pickup_longitude",
            "pickup_latitude",
            "dropoff_longitude",
            "dropoff_latitude"
        ],
        options = {"is_replicated": "true"}
    )
    table_taxi_replicated_obj = gpudb.GPUdbTable(_type = None, name = table_taxi_replicated, db = kdb)


    # Join Example 3 (Full Outer Join)
    # Retrieve the vendor IDs of known vendors with no recorded cab ride
    # transactions, as well as the vendor ID and number of transactions for
    # unknown vendors with recorded cab ride transactions
    gpudb.GPUdbTable.create_join_table(
        join_table_name = join_table_outer,
        table_names = [
            schema + ".taxi_trip_data_replicated as t",
            schema + ".vendor as v"
        ],
        column_names = [
            "t.vendor_id as vendor_id",
            "v.vendor_id as vendor_id_1"
        ],
        expressions = ["FULL_OUTER JOIN t,v ON ((v.vendor_id = t.vendor_id))"],
        db = kdb
    )
    join_table_outer_obj = gpudb.GPUdbTable(_type = None, name = join_table_outer, db = kdb)

    # Aggregate the join table results by vendor ID and count the amount of
    # records
    j3_resp = join_table_outer_obj.aggregate_group_by(
        column_names = [
            "vendor_id_1 as vend_table_vendors",
            "vendor_id as taxi_table_vendors",
            "COUNT(*) as total_records"
        ],
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        options = {
            "expression": "(IS_NULL(vendor_id_1) OR IS_NULL(vendor_id))",
            "sort_by": "key"
        }
    )["data"]

    print("Known vendors with no transactions and unknown vendors with transactions:")
    print("Vend. Table Vendors Taxi Table Vendors Total Records")
    print("=================== ================== =============")
    for record in zip(
        j3_resp["vend_table_vendors"],
        j3_resp["taxi_table_vendors"],
        j3_resp["total_records"]
    ):
        print("{:<19s} {:<18s} {:13d}".format(
            record[0] or "<Unknown Vendor>",
            record[1] or "<No Transactions>",
            record[2]
        ))

    print("")
    print("\nPROJECTIONS")
    print("-----------\n")

    # Clear any existing projections with the same name (otherwise we won't be
    # able to create the projections)
    kdb.clear_table(table_name=projection_example1, options=no_error_option)
    kdb.clear_table(table_name=projection_example2, options=no_error_option)

    # Projection Example 1
    # Create a projection containing all payments by credit card
    table_payment_obj.create_projection(
        projection_name = projection_example1,
        column_names = [
            "payment_id",
            "payment_type",
            "credit_type",
            "payment_timestamp",
            "fare_amount",
            "surcharge",
            "mta_tax",
            "tip_amount",
            "tolls_amount",
            "total_amount"
        ],
        options = {"expression": "payment_type = 'Credit'"}
    )

    projection_example1_obj = gpudb.GPUdbTable(_type = None, name = projection_example1, db = kdb)

    p1_resp = projection_example1_obj.get_records_by_column(
        column_names = [
            "payment_id",
            "payment_type",
            "credit_type",
            "payment_timestamp",
            "fare_amount",
            "surcharge",
            "mta_tax",
            "tip_amount",
            "tolls_amount",
            "total_amount"
        ],
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        options = {"order_by": "payment_id"}
    )

    print("Projection of only credit payment types:")
    print("Payment ID Payment Type Credit Type      Timestamp     Fare  Surcharge MTA Tax Tip   Tolls Total")
    print("========== ============ ================ ============= ===== ========= ======= ===== ===== =====")
    for record in zip(
        p1_resp["payment_id"],
        p1_resp["payment_type"],
        p1_resp["credit_type"],
        p1_resp["payment_timestamp"],
        p1_resp["fare_amount"],
        p1_resp["surcharge"],
        p1_resp["mta_tax"],
        p1_resp["tip_amount"],
        p1_resp["tolls_amount"],
        p1_resp["total_amount"]
    ):
        print("{:>10} {:<12} {:<16} {:<13} {:5.2f} {:9.2f} {:7.2f} {:5.2f} {:5.2f} {:5.2f}".format(
                record[0],
                record[1],
                record[2],
                record[3] or "",
                record[4],
                record[5],
                record[6],
                record[7],
                record[8],
                record[9]
        ))
    print("")

    # Projection Example 2
    # Create a persisted table with cab ride transactions greater than 5 miles
    # whose trip started during lunch hours
    table_taxi_obj.create_projection(
        projection_name = projection_example2,
        column_names = [
            "HOUR(pickup_datetime) as hour_of_day",
            "vendor_id",
            "passenger_count",
            "trip_distance"
        ],
        options = {
            "expression":
                "(HOUR(pickup_datetime) >= 11) AND "
                "(HOUR(pickup_datetime) <= 14) AND "
                "(trip_distance > 5)",
            "persist": "true"
        }
    )

    projection_example2_obj = gpudb.GPUdbTable(_type=None, name=projection_example2, db=kdb)

    p2_resp = projection_example2_obj.get_records_by_column(
        column_names = [
            "hour_of_day",
            "vendor_id",
            "passenger_count",
            "trip_distance"
        ],
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        options = {"order_by": "hour_of_day, vendor_id, passenger_count, trip_distance"}
    )

    print("Projection of long trips taken during lunch hours:")
    print("Hour of Day Vendor ID Passenger Count Trip Distance")
    print("=========== ========= =============== =============")
    for record in zip(
        p2_resp["hour_of_day"],
        p2_resp["vendor_id"],
        p2_resp["passenger_count"],
        p2_resp["trip_distance"]
    ):
        print("{:>11} {:<9} {:15} {:13.2f}".format(
            record[0],
            record[1],
            record[2],
            record[3]
        ))

    print("")
    print("\nUNION, INTERSECT, & EXCEPT")
    print("--------------------------\n")

    # Clear any existing tables with the same name (otherwise we won't be able
    # to create the tables)
    kdb.clear_table(table_name=agg_grpby_union_all_src1, options=no_error_option)
    kdb.clear_table(table_name=agg_grpby_union_all_src2, options=no_error_option)
    kdb.clear_table(table_name=projection_except_src1, options=no_error_option)
    kdb.clear_table(table_name=projection_except_src2, options=no_error_option)
    kdb.clear_table(table_name=union_all_table, options=no_error_option)
    kdb.clear_table(table_name=union_except_table, options=no_error_option)
    kdb.clear_table(table_name=union_intersect_table, options=no_error_option)

    # Union Example 1 (Union All)
    # Calculate the average number of passengers, as well as the shortest,
    # average, and longest trips for all trips in
    # each of the two time periods--from April 1st through the 15th, 2015 and
    # from April 16th through the 23rd, 2015--and return those two sets of
    # statistics in a single result set.
    table_taxi_obj.aggregate_group_by(
        column_names = [
            "AVG(passenger_count) as avg_pass_count",
            "AVG(trip_distance) as avg_trip_dist",
            "MIN(trip_distance) as min_trip_dist",
            "MAX(trip_distance) as max_trip_dist"
        ],
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        options = {
            "expression":
                "(pickup_datetime >= '2015-04-01') AND "
                "(pickup_datetime <= '2015-04-15 23:59:59.999')",
            "result_table": agg_grpby_union_all_src1
        }
    )
    table_taxi_obj.aggregate_group_by(
        column_names = [
            "AVG(passenger_count) as avg_pass_count",
            "AVG(trip_distance) as avg_trip_dist",
            "MIN(trip_distance) as min_trip_dist",
            "MAX(trip_distance) as max_trip_dist"
        ],
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        options = {
            "expression":
                "(pickup_datetime >= '2015-04-16') AND "
                "(pickup_datetime <= '2015-04-23 23:59:59.999')",
            "result_table": agg_grpby_union_all_src2
        }
    )
    gpudb.GPUdbTable.create_union(
        table_name = union_all_table,
        table_names = [
            agg_grpby_union_all_src1,
            agg_grpby_union_all_src2
        ],
        input_column_names = [
            ["'2015-04-01 - 2015-04-15'", "avg_pass_count", "avg_trip_dist", "min_trip_dist", "max_trip_dist"],
            ["'2015-04-16 - 2015-04-23'", "avg_pass_count", "avg_trip_dist", "min_trip_dist", "max_trip_dist"]
        ],
        output_column_names = [
            "pickup_window_range",
            "avg_pass_count",
            "avg_trip",
            "min_trip",
            "max_trip"
        ],
        options = {"mode": "union_all"},
        db = kdb
    )

    union_all_table_obj = gpudb.GPUdbTable(_type=None, name=union_all_table, db=kdb)

    u1_resp = union_all_table_obj.get_records_by_column(
        column_names = [
            "pickup_window_range",
            "avg_pass_count",
            "avg_trip",
            "min_trip",
            "max_trip"
        ],
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET
    )

    print("Passenger statistics for each half of April:")
    print("Pickup Window Range     Avg. Pass. Count Avg. Trip Min. Trip Max. Trip")
    print("======================= ================ ========= ========= =========")
    for record in zip(
        u1_resp["pickup_window_range"],
        u1_resp["avg_pass_count"],
        u1_resp["avg_trip"],
        u1_resp["min_trip"],
        u1_resp["max_trip"]
    ):
        print("{:<23} {:16.1f} {:9.2f} {:9.2f} {:9.2f}".format(
            record[0],
            round(record[1], 3),
            round(record[2], 3),
            round(record[3], 3),
            round(record[4], 3)
        ))
    print("")

    # Union Example 2 (Intersect)
    # Retrieve locations (as lat/lon pairs) that were both pick-up and drop-off points
    gpudb.GPUdbTable.create_union(
        table_name = union_intersect_table,
        table_names = [
            table_taxi_replicated,
            table_taxi_replicated
        ],
        input_column_names = [
            ["pickup_latitude", "pickup_longitude"],
            ["dropoff_latitude", "dropoff_longitude"]
        ],
        output_column_names = ["latitude", "longitude"],
        options = {"mode": "intersect"},
        db = kdb
    )

    union_intersect_table_obj = gpudb.GPUdbTable(_type=None, name=union_intersect_table, db=kdb)

    u2_resp = union_intersect_table_obj.get_records_by_column(
        column_names = ["latitude", "longitude"],
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET,
        options = {
            "expression": "(latitude <> 0) AND (longitude <> 0)",
            "order_by": "latitude, longitude"
        }
    )

    print("Latitude/Longitude pairs that were both pick-up and drop-off points:")
    print("Latitude    Longitude")
    print("=========== ============")
    for record in zip(u2_resp["latitude"], u2_resp["longitude"]):
        print("{:>11.8f} {:>12.8f}".format(
            round(record[0], 8),
            round(record[1], 8)
        ))
    print("")

    # Union Example 3 (Except)
    # Show vendors that operate before noon, but not after noon: retrieve the
    # unique list of IDs of vendors who provided cab rides between midnight
    # and noon, and remove from that list the IDs of any vendors who provided
    # cab rides between noon and midnight
    table_taxi_replicated_obj.create_projection(
        projection_name = projection_except_src1,
        column_names = ["vendor_id"],
        options = {
            "expression":
                "(HOUR(pickup_datetime) >= 0) AND "
                "(HOUR(pickup_datetime) <= 11)"
        }
    )
    table_taxi_replicated_obj.create_projection(
        projection_name = projection_except_src2,
        column_names = ["vendor_id"],
        options = {
            "expression":
                "(HOUR(pickup_datetime) >= 12) AND "
                "(HOUR(pickup_datetime) <= 23)"
        }
    )
    gpudb.GPUdbTable.create_union(
        table_name = union_except_table,
        table_names = [
            projection_except_src1,
            projection_except_src2
        ],
        input_column_names = [
            ["vendor_id"],
            ["vendor_id"]
        ],
        output_column_names = ["vendor_id"],
        options = {"mode": "except"},
        db = kdb
    )

    union_except_table_obj = gpudb.GPUdbTable(_type=None, name=union_except_table, db=kdb)

    u3_resp = union_except_table_obj.get_records_by_column(
        column_names = ["vendor_id"],
        offset = 0,
        limit = gpudb.GPUdb.END_OF_SET
    )

    print("Vendors that operate between midnight and noon:")
    print("Vendor ID")
    print("=========")
    for record in zip(u3_resp["vendor_id"]):
        print("{:<9}".format(record[0]))

# end gpudb_example()


if __name__ == "__main__":

    # Set up args
    parser = argparse.ArgumentParser(description='Run Python tutorial.')
    parser.add_argument('--url', default='http://127.0.0.1:9191', help='Kinetica host to run examples against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')
    parser.add_argument('--data_dir', default='./', help='Data file directory')

    args = parser.parse_args()

    # Establish connection with an instance of Kinetica, given a URL and credentials
    kdb = gpudb.GPUdb(host = args.url, username = args.username, password = args.password)

    gpudb_example(args.data_dir)
