'use strict';



function main(url, user, pass) {

	console.log("Establishing a connection with Kinetica...");
	var db = new GPUdb([url], {"username": user, "password": pass});

	var schema_name = "tutorial_js";
	var table_name = schema_name + ".my_table";
	var view1_name = schema_name + ".view_1";
	var view2_name = schema_name + ".view_2";
	var view3_name = schema_name + ".view_3";
	
	// (Re)create schema
	db.drop_schema(schema_name, {"no_error_if_not_exists": "true", "cascade": "true"});
	db.create_schema(schema_name);

	var show_table_rsp = db.show_table( "", {} );
	console.log( JSON.stringify( show_table_rsp ) );

	// Declare the data type for the table
	var my_type = {
		"type": "record",
		"name": "my_type",
		"fields": [
			{"name":"col1","type":"double"},
			{"name":"col2","type":"string"},
			{"name":"group_id","type":"string"}
		]
	};

	// Register the data type with GPUdb and get the type's ID
	var create_type_rsp = db.create_type( JSON.stringify( my_type ), "my_type" );
	var type_id = create_type_rsp.type_id;

	// Create a table
	var create_table_rsp = db.create_table( table_name, type_id );

	// Generate records to be inserted 
	var records = [];
	for (var i = 0; i < 10; i++) {
		var record = {
			col1 : (i + 0.1),
			col2 : ("string " + i),
			group_id : "Group 1"
		};
		records.push( record );
	}

	// This option will return IDs per record with which we can refer
	// to particular records later as needed
	var insert_options = { "return_record_ids" : "true" }
	var insert_records_rsp = db.insert_records( table_name, records, insert_options );
	console.log( "Record IDs for newly inserted records: " + insert_records_rsp["record_ids"] );

	// Fetch the records from the table
	var get_records_rsp = db.get_records( table_name );
	console.log( "Retrieved records: " );
	console.log( JSON.stringify( get_records_rsp["data"] ) );

	// Perform a filter operation on the table
	var filter_rsp = db.filter( table_name, view1_name, "col1 = 1.1" );
	console.log( "Number of filtered records: " + filter_rsp["count"] );

	// Fetch the records from the view (like reading from a regular table)
	var get_records_rsp = db.get_records( view1_name );
	console.log( "Filtered records: " );
	console.log( JSON.stringify( get_records_rsp["data"] ) );

	// Drop the view
	db.clear_table( view1_name );

	// Perform a filter operation on the table on two columns
	filter_rsp = db.filter( table_name, view1_name, "col1 <= 9 and group_id = 'Group 1'" );
	console.log( "Number of records filtered by the second expression: " + filter_rsp["count"] );

	// Fetch the records from the view
	get_records_rsp = db.get_records( view1_name );
	console.log( "Second set of filtered records: " );
	console.log( JSON.stringify( get_records_rsp["data"] ) );

	// Perform a filter by list operation
	var column_values_map = {
			col1 : [ "1.1", "2.1", "5.1" ]
	};

	var filter_by_list_rsp = db.filter_by_list( table_name, view2_name, column_values_map );
	console.log( "Number of records filtered by list: " + filter_by_list_rsp["count"] );

	// Fetch the records from the second view
	get_records_rsp = db.get_records( view2_name );
	console.log( "Records filtered by a list: " );
	console.log( JSON.stringify( get_records_rsp["data"] ) );

	// Perform a filter by range operation
	var filter_by_range_rsp = db.filter_by_range(table_name, view3_name, "col1", 1, 5);
	console.log( "Number of records filtered by range: " + filter_by_range_rsp["count"] );

	// Fetch the records from the second view
	get_records_rsp = db.get_records( view3_name );
	console.log( "Records filtered by a range: " );
	console.log( JSON.stringify( get_records_rsp["data"] ) );

	// Perform an aggregate operation (statistics: sum, mean, count)
	var stats_rsp = db.aggregate_statistics( table_name, "col1", "sum,mean,count" )
	console.log( "Statistics of values in 'col1': " + stats_rsp['stats'] );

	// Insert some more records
	console.log( "Inserting more records into the table..." );
	var records = [];
	for (var i = 1; i < 8; i++) {
		var record = {
			col1 : (i + 10.1),
			col2 : ("string " + i),
			group_id : "Group 2" // unique from the first group of records
		};
		records.push( record );
	}
	db.insert_records( table_name, records );

	// Find all unique values of a given column
	var unique_rsp = db.aggregate_unique( table_name, "group_id", 0 )
	console.log( "Unique of values in 'group_id': " );
	console.log( JSON.stringify( unique_rsp['data'] ) );

	// Aggregate values of a given column by grouping by its values
	var column_names = [ "col2" ];
	var group_by_rsp = db.aggregate_group_by( table_name, column_names, 0 )
	console.log( "Group by results: " );
	console.log( JSON.stringify( group_by_rsp['data'] ) );

	// Second group by
	var column_names = [ "group_id", "count(*)", "sum(col1)", "avg(col1)" ];
	group_by_rsp = db.aggregate_group_by( table_name, column_names, 0 )
	console.log( "Second group by results: " );
	console.log( JSON.stringify( group_by_rsp['data'] ) );

	// Third group by
	var column_names = [ "group_id", "sum(col1*col1)" ];
	group_by_rsp = db.aggregate_group_by( table_name, column_names, 0 )
	console.log( "Third group by results: " );
	console.log( JSON.stringify( group_by_rsp['data'] ) );

	// Insert some more records
	console.log( "Inserting more records into the table..." );
	var records = [];
	for (var i = 4; i < 10; i++) {
		var record = {
			col1 : (i + 0.6),
			col2 : ("string 2" + i),
			group_id : "Group 1"
		};
		records.push( record );
	}
	db.insert_records( table_name, records );

	// Perform a histogram calculation
	var start = 1.1;
	var end = 2;
	var interval = 1;

	var histogram_rsp = db.aggregate_histogram(table_name, "col1", start, end, interval)
	console.log( "Histogram results: " );
	console.log( JSON.stringify( histogram_rsp ) );

	// Drop the original table (will automatically drop all views of it)
	db.clear_table( table_name );

	// Check that no view of that table is available anymore.
	// Using a callback function to check the error status of the query.
	db.show_table(
			view3_name,
			"",
			function( err, data ) { // callback function
				if (err !== null) {
					console.log( "View <" + view3_name + "> not available as expected." );
				}
			}
	);

};
