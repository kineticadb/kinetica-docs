"""This script walks through using geospatial data and expressions with the Python API.

Covered here: creating a table, inserting WKT data, filtering geospatial data, aggregating geospatial
data, joining geospatial data, and comparing different geospatial equality functions
"""

import argparse
import json
import gpudb

# Tables created externally to this script
geo_schema = "example_geospatial"
nyc_nta_table = geo_schema + ".nyc_neighborhood"
taxi_trip_table = geo_schema + ".taxi_trip_data"
taxi_zones_table = geo_schema + ".taxi_zone"

# Tables/Views created within this script
poi_table = geo_schema + ".points_of_interest"
dist_check_view = geo_schema + ".distance_check"
zones_by_area_proj = geo_schema + ".zones_by_area"
queens_agb = geo_schema + ".queens_neighborhoods"
pickup_point_location = geo_schema + ".pickup_point_neighborhood_location"
top_pickup_locations_by_frequency = geo_schema + ".top_pickup_locations_by_frequency"
top_pickup_locations_by_distance = geo_schema + ".top_pickup_locations_by_distance"
pickup_agb = geo_schema + ".top_pickup_location_groups"
poi_comp_table = geo_schema + ".points_of_interest_src_compare"


def geospatial_examples():

    print("GEOSPATIAL EXAMPLES OUTPUT")
    print("==========================\n")


    print("CREATING A TABLE AND INSERTING WKT DATA")
    print("---------------------------------------\n")

    # Create a type using the GPUdbRecordType object
    columns = [gpudb.GPUdbRecordColumn("src1_poi", "string",
                                       [gpudb.GPUdbColumnProperty.WKT]),
               gpudb.GPUdbRecordColumn("src2_poi", "string",
                                       [gpudb.GPUdbColumnProperty.WKT])]
    poi_record_type = gpudb.GPUdbRecordType(columns, label="poi_record_type")
    poi_record_type.create_type(kinetica)
    poi_type_id = poi_record_type.type_id
    # Create a table from the poi_record_type
    response = kinetica.create_table(table_name=poi_table, type_id=poi_type_id)
    print(f"Table created: {response['status_info']['status']}")

    # Prepare the data to be inserted
    pois = [
        "POINT(-73.8455003 40.7577272)",
        "POLYGON((-73.9258506 40.8287493, -73.9258292 40.828723, -73.9257795 40.8287387, -73.925801 40.8287635, "
        "-73.9258506 40.8287493))",
        "LINESTRING(-73.9942208 40.7504289, -73.993856 40.7500753, -73.9932525 40.7499941)",
        "LINESTRING(-73.9760944 40.6833433, -73.9764404 40.6830626, -73.9763761 40.6828897)"
    ]
    pois_compare = [
        "POINT(-73.84550029 40.75772724)",
        "POLYGON((-73.9257795 40.8287387, -73.925801 40.8287635, -73.9258506 40.8287493, -73.9258506 40.8287493, "
        "-73.9258292 40.828723))",
        "LINESTRING(-70.9942208 42.7504289, -72.993856 43.7500753, -73.9932525 44.7499941)",
        "LINESTRING(-70.9761 41.6834, -72.9765 39.6831, -76.9764 38.6829)"
    ]
    # Insert the data into the table using a list
    encoded_obj_list = []
    for val in range(0, 4):
        poi1_val = pois[val]
        poi2_val = pois_compare[val]
        record = gpudb.GPUdbRecord(poi_record_type, [poi1_val, poi2_val])
        encoded_obj_list.append(record.binary_data)
    response = kinetica.insert_records(table_name=poi_table, data=encoded_obj_list, list_encoding="binary")
    print(f"Number of records inserted:  {response['count_inserted']}\n")

    print("SCALAR FUNCTIONS")
    print("----------------\n")

    # Scalar Example 1

    """ Using GEODIST(), calculate the distance between pickup and dropoff points to see where the calculated distance
        is less than the recorded trip distance """
    response = kinetica.filter(
            table_name=taxi_trip_table,
            view_name=dist_check_view,
            expression="GEODIST(pickup_longitude, pickup_latitude, dropoff_longitude, dropoff_latitude) "
                        "< trip_distance"
    )
    print(f"Number of trips where geographic distance < recorded distance: {response['count']}\n")

    # Scalar Example 2

    # Calculate the area of each taxi zone and copy the selected data to a projection
    kinetica.create_projection(
            table_name=taxi_zones_table,
            projection_name=zones_by_area_proj,
            column_names=["objectid", "zone", "ST_AREA(geom,1) / 1000000 AS area"],
            options={"order_by": "area desc", "limit": "5"}
    )
    # Display the top 5 largest taxi zones
    large_zones = kinetica.get_records(
            table_name=zones_by_area_proj,
            offset=0, limit=gpudb.GPUdb.END_OF_SET,
            encoding="json",
            options={"sort_by":"area", "sort_order": "descending"}
    )['records_json']
    print("Top 5 largest taxi zones:")
    print("{:<7s} {:<27s} {:<30s}".format("Zone_ID", "Zone_Name", "Zone_Area_in_Square_Kilometers"))
    print("{:=<7s} {:=<27s} {:=<30s}".format("", "", ""))
    for zone in large_zones:
        print("{objectid:>7d} {zone:<27s} {area:>30.4f}".format(**json.loads(zone)))

    print("\nGEOSPATIAL AGGREGATIONS")
    print("-----------------------\n")

    # Dissolve the boundaries between Queens neighborhood tabulation areas to create a single borough boundary
    response = kinetica.aggregate_group_by(
            table_name=nyc_nta_table,
            column_names=["ST_DISSOLVE(geom) AS neighborhoods"],
            offset=0, limit=1,
            encoding="json",
            options={
                    "expression": "BoroName = 'Queens'",
                    "result_table": queens_agb
            }
    )
    print(f"Queens neighborhood boundaries dissolved:  {response['status_info']['status']}")

    print("\nGEOSPATIAL JOINS")
    print("----------------\n")

    # Join Example 1

    # Locate which borough and neighborhood taxi pickup points occurred
    kinetica.create_join_table(
            join_table_name=pickup_point_location,
            table_names=[taxi_trip_table + " AS t", nyc_nta_table + " AS n"],
            column_names=[
                    "t.vendor_id", "t.passenger_count",
                    "t.pickup_longitude", "t.pickup_latitude",
                    "n.BoroName", "n.NTAName"
            ],
            expressions=["STXY_CONTAINS(n.geom, t.pickup_longitude, t.pickup_latitude)"]
    )
    # Display a subset of the pickup point locations
    pickup_points = kinetica.get_records(
            table_name=pickup_point_location,
            offset=0, limit=25,
            encoding="json",
            options={"sort_by":"pickup_longitude"}
    )['records_json']
    print("Subset of pickup point neighborhood locations:")
    print("{:<10s} {:<12s} {:<13s} {:<12s} {:<11s} {:<43s}".format("Vendor ID", "Pass. Count", "Pickup Long.",
                                                                   "Pickup Lat.", "Borough", "NTA"))
    print("{:=<10s} {:=<12s} {:=<13s} {:=<12s} {:=<11s} {:=<43s}".format("", "", "", "", "", ""))
    for point in pickup_points:
        print("{vendor_id:<10s} {passenger_count:<12d} {pickup_longitude:<13f} {pickup_latitude:<12f} "
              "{BoroName:<11s} {NTAName:<43s}".format(**json.loads(point)))
    print("")

    # Join Example 2

    # Find the top neighborhood pickup locations
    kinetica.create_join_table(
            join_table_name=top_pickup_locations_by_frequency,
            table_names=[taxi_trip_table + " AS t", nyc_nta_table + " AS n"],
            column_names=["n.NTAName AS NTAName"],
            expressions=["((STXY_INTERSECTS(t.pickup_longitude, t.pickup_latitude, n.geom) = 1))"]
    )
    # Aggregate the neighborhoods and the count of records per neighborhood
    kinetica.aggregate_group_by(
            table_name=top_pickup_locations_by_frequency,
            column_names=["NTAName AS Pickup_NTA", "COUNT(*) AS Total_Pickups"],
            offset=0, limit=gpudb.GPUdb.END_OF_SET,
            options={"result_table": pickup_agb}
    )
    # Display the top 10 neighborhood pickup locations
    response = kinetica.get_records_by_column(
            table_name=pickup_agb,
            column_names=["Pickup_NTA", "Total_Pickups"],
            offset=0, limit=10,
            encoding="json",
            options={"order_by": "Total_Pickups desc"}
    )
    data = kinetica.parse_dynamic_response(response)['response']
    print("Top 10 neighborhood pickup locations:")
    print("{:<43s} {:<14s}".format("Pickup NTA", "Total Pickups"))
    print("{:=<43s} {:=<14s}".format("", ""))
    for pickupLocs in zip(data["Pickup_NTA"], data["Total_Pickups"]):
        print("{:<43s} {:<14d}".format(*pickupLocs))
    print("")

    # Join Example 3

    # Find the geospatial objects representing the top 10 neighborhoods by
    # distance covered over all taxi trips originating in them
    response = kinetica.create_join_table(
            join_table_name=top_pickup_locations_by_distance,
            table_names=[taxi_trip_table + " AS t", nyc_nta_table + " AS n"],
            column_names=["n.geom AS geom", "t.trip_distance AS trip_distance"],
            expressions=["((STXY_INTERSECTS(t.pickup_longitude, t.pickup_latitude, n.geom) = 1))"]
    )
    # Aggregate the neighborhoods and the count of records per neighborhood
    response = kinetica.aggregate_group_by(
            table_name=top_pickup_locations_by_distance,
            column_names=["geom AS Pickup_Geo", "SUM(trip_distance) AS Total_Trip_Distance"],
            encoding = "json",
            offset = 0, limit = 10,
            options = {"sort_by":"value", "sort_order":"descending"}
    )

    # Display the top 10 neighborhood pickup neighborhood geos
    data = json.loads(response["json_encoded_response"])
    print("Top 10 neighborhood pickup geos:")
    print("{:<19s} {:<50s}".format("Total Trip Distance", "Pickup Geo"))
    print("{:=<19s} {:=<50s}".format("", ""))
    for record in zip(data["column_2"], data["column_1"]):
        print("{:>19.2f} {:<50s}".format(record[0], record[1][0:47] + "..."))

    print("\nGEOSPATIAL EQUALITY")
    print("-------------------\n")

    # Calculate types of geospatial equality for differing sources of geometry
    kinetica.create_projection(
        table_name=poi_table,
        projection_name=poi_comp_table,
        column_names=[
            "ST_GEOMETRYTYPE(src1_poi) AS src1type",
            "ST_GEOMETRYTYPE(src2_poi) AS src2type",
            "ST_ALMOSTEQUALS(src1_poi, src2_poi, 7) AS almostequals",
            "ST_EQUALS(src1_poi, src2_poi) AS equals",
            "ST_EQUALSEXACT(src1_poi, src2_poi, 4) AS equalsexact"
        ]
    )
    equality_comps = kinetica.get_records(
            table_name=poi_comp_table,
            offset=0, limit=10,
            encoding="json",
            options={"sort_by":"src1type"}
    )['records_json']
    print("Comparing ST_ALMOSTEQUALS(), ST_EQUALS(), and ST_EQUALSEXACT():")
    print("{:<13s} {:<13s} {:<13s} {:<6s} {:<12s}".format(
            "Source_1_Type", "Source_2_Type", "Almost_Equals", "Equals", "Equals_Exact"
    ))
    print("{:=<13s} {:=<13s} {:=<13s} {:=<6s} {:=<12s}".format("", "", "", "", ""))
    for comp in equality_comps:
        print("{src1type:<13s} {src2type:<13s} {almostequals:>13d} {equals:>6d} {equalsexact:>12d}".format(**json.loads(comp)))

# end geospatial_examples()


def clear_tables():

    # Drop all the tables
    for table_name in reversed([
        poi_table,
        dist_check_view,
        zones_by_area_proj,
        queens_agb,
        pickup_point_location,
        top_pickup_locations_by_frequency,
        pickup_agb,
        top_pickup_locations_by_distance,
        poi_comp_table

    ]):
        kinetica.clear_table(table_name)

# end clear_tables()


if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Run geospatial function examples.')
    parser.add_argument('--url', default='http://127.0.0.1:9191', help='Kinetica URL to run example against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')

    args = parser.parse_args()

    """ Establish connection with an instance of Kinetica,
        using binary encoding to save memory """
    kinetica = gpudb.GPUdb(host = [args.url], username = args.username, password = args.password)

    clear_tables()
    geospatial_examples()
