import com.gpudb.*;
import com.gpudb.filesystem.GPUdbFileHandler;
import com.gpudb.protocol.*;

import java.util.*;
import java.io.*;
import com.fasterxml.jackson.databind.ObjectMapper;

/*
 * Java API Programming Tutorial
 *
 * Covered here: importing GPUdb, instantiating Kinetica, creating a type,
 * creating a table, managing records, retrieving records, filtering records,
 * aggregating/grouping records, joins, projections, and set operations. */

public class Tutorial
{
	public static class Vendor extends RecordObject
	{
		/* Create column(s), establish its ordering, give it property
		 * sub-type(s), give it a column type, and give it a name. */
		@RecordObject.Column(order = 0, properties = { "char4", "primary_key" })
		public String vendor_id;
		@RecordObject.Column(order = 1, properties = { "char64" })
		public String vendor_name;
		@RecordObject.Column(order = 2, properties = { "char16", "nullable" })
		public String phone;
		@RecordObject.Column(order = 3, properties = { "char64", "nullable" })
		public String email;
		@RecordObject.Column(order = 4, properties = { "char64" })
		public String hq_street;
		@RecordObject.Column(order = 5, properties = { "char8", "dict" })
		public String hq_city;
		@RecordObject.Column(order = 6, properties = { "char2", "dict" })
		public String hq_state;
		@RecordObject.Column(order = 7)
		public Integer hq_zip;
		@RecordObject.Column(order = 8)
		public Integer num_emps;
		@RecordObject.Column(order = 9)
		public Integer num_cabs;

		public Vendor() {}

		/* Create a constructor for the class that will take parameters so that
		 * Bulk Inserting is easier */
		public Vendor(
				String vendor_id, String vendor_name, String phone,
				String email, String hq_street, String hq_city, String hq_state,
				Integer hq_zip, Integer num_emps, Integer num_cabs
		)
		{
			this.vendor_id = vendor_id;
			this.vendor_name = vendor_name;
			this.phone = phone;
			this.email = email;
			this.hq_street = hq_street;
			this.hq_city = hq_city;
			this.hq_state = hq_state;
			this.hq_zip = hq_zip;
			this.num_emps = num_emps;
			this.num_cabs = num_cabs;
		}
	}


	public static class Payment extends RecordObject
	{
		@RecordObject.Column(order = 0, properties = { "primary_key" })
		public long payment_id;
		@RecordObject.Column(order = 1, properties = { "char16", "nullable" })
		public String payment_type;
		@RecordObject.Column(order = 2, properties = { "char16", "nullable" })
		public String credit_type;
		@RecordObject.Column(order = 3, properties = { "timestamp", "nullable" })
		public Long payment_timestamp;
		@RecordObject.Column(order = 4, properties = { "nullable" })
		public double fare_amount;
		@RecordObject.Column(order = 5, properties = { "nullable" })
		public double surcharge;
		@RecordObject.Column(order = 6, properties = { "nullable" })
		public double mta_tax;
		@RecordObject.Column(order = 7, properties = { "nullable" })
		public double tip_amount;
		@RecordObject.Column(order = 8, properties = { "nullable" })
		public double tolls_amount;
		@RecordObject.Column(order = 9, properties = { "nullable" })
		public double total_amount;

		public Payment() {}

		public Payment(
				long payment_id, String payment_type, String credit_type,
				Long payment_timestamp, double fare_amount, double surcharge,
				double mta_tax, double tip_amount, double tolls_amount,
				double total_amount
		)
		{
			this.payment_id = payment_id;
			this.payment_type = payment_type;
			this.credit_type = credit_type;
			this.payment_timestamp = payment_timestamp;
			this.fare_amount = fare_amount;
			this.surcharge = surcharge;
			this.mta_tax = mta_tax;
			this.tip_amount = tip_amount;
			this.tolls_amount = tolls_amount;
			this.total_amount = total_amount;
		}
	}


	public static class TaxiTripData extends RecordObject
	{
		@RecordObject.Column(order = 0, properties = { "primary_key" })
		public long transaction_id;
		@RecordObject.Column(order = 1, properties = { "primary_key", "shard_key"})
		public long payment_id;
		@RecordObject.Column(order = 2, properties = { "char4" })
		public String vendor_id;
		@RecordObject.Column(order = 3, properties = { "timestamp" })
		public long pickup_datetime;
		@RecordObject.Column(order = 4, properties = { "timestamp" })
		public long dropoff_datetime;
		@RecordObject.Column(order = 5, properties = { "int8" })
		public int passenger_count;
		@RecordObject.Column(order = 6)
		public float trip_distance;
		@RecordObject.Column(order = 7)
		public float pickup_longitude;
		@RecordObject.Column(order = 8)
		public float pickup_latitude;
		@RecordObject.Column(order = 9)
		public float dropoff_longitude;
		@RecordObject.Column(order = 10)
		public float dropoff_latitude;

		public TaxiTripData() {}
	}


	public static void main(String[] args) throws Exception
	{
		String url = (args.length > 0) ? args[0] : "http://localhost:9191";
		String user = (args.length > 1) ? args[1] : null;
		String pass = (args.length > 2) ? args[2] : null;

		final String CSV_FILE_PATH = "./taxi_trip_data.csv";

		// Columns and table names used in queries below
		final String SCHEMA_NAME = "tutorial_java";

		final String AGG_GRPBY_UNION_ALL_SRC1 = SCHEMA_NAME + ".agg_passcount_tripdist_btw_apr1_apr15";
		final String AGG_GRPBY_UNION_ALL_SRC2 = SCHEMA_NAME + ".agg_passcount_tripdist_btw_apr16_apr23";

		final String JOIN_TABLE_INNER = SCHEMA_NAME + ".pay_info_rides_gt_3_pass";
		final String JOIN_TABLE_LEFT = SCHEMA_NAME + ".all_vendor_transactions";
		final String JOIN_TABLE_OUTER = SCHEMA_NAME + ".vendors_w_no_transactions";

		final String PROJECTION_EXAMPLE1 = SCHEMA_NAME + ".credit_payment";
		final String PROJECTION_EXAMPLE2 = SCHEMA_NAME + ".lunch_time_rides";
		final String PROJECTION_EXCEPT_SRC1 = SCHEMA_NAME + ".vendors_operating_before_noon";
		final String PROJECTION_EXCEPT_SRC2 = SCHEMA_NAME + ".vendors_operating_after_noon";

		final String TABLE_PAYMENT = SCHEMA_NAME + ".payment";
		final String TABLE_TAXI = SCHEMA_NAME + ".taxi_trip_data";
		final String TABLE_TAXI_REPLICATED = SCHEMA_NAME + ".taxi_trip_data_replicated";
		final String TABLE_VENDOR = SCHEMA_NAME + ".vendor";

		final String UNION_ALL_TABLE = SCHEMA_NAME + ".passcount_tripdist_stats_apr";
		final String UNION_INTERSECT_TABLE = SCHEMA_NAME + ".shared_pickup_dropoff_points";
		final String UNION_EXCEPT_TABLE = SCHEMA_NAME + ".vendors_operating_btw_midnight_noon";

		final String VIEW_EXAMPLE1 = SCHEMA_NAME + ".null_payments";
		final String VIEW_EXAMPLE2 = SCHEMA_NAME + ".null_payments_gt_8";
		final String VIEW_EXAMPLE3 = SCHEMA_NAME + ".nyc_ycab_vendors";
		final String VIEW_EXAMPLE4 = SCHEMA_NAME + ".passenger_count_btw_1_3";

		final ObjectMapper JSON = new ObjectMapper();



		System.out.println();
		System.out.println("TUTORIAL OUTPUT");
		System.out.println("===============");

		// Establish connection with a locally-running instance of Kinetica
		GPUdb.Options options = new GPUdb.Options();
		options.setUsername(user);
		options.setPassword(pass);
		GPUdb kdb = new GPUdb(url, options);


		System.out.println();
		System.out.println("CREATING SCHEMA, TYPES, & TABLES");
		System.out.println("--------------------------------");
		System.out.println();

		System.out.println("Tutorial Schema");
		System.out.println("***************");

		/* Clear any existing tables by (re)creating the containing schema */
		Map<String, String> dropSchemaOptions = GPUdb.options(
				DropSchemaRequest.Options.NO_ERROR_IF_NOT_EXISTS, DropSchemaRequest.Options.TRUE,
				DropSchemaRequest.Options.CASCADE, DropSchemaRequest.Options.TRUE
		);
		kdb.dropSchema(SCHEMA_NAME, dropSchemaOptions);
		kdb.createSchema(SCHEMA_NAME, null);
		System.out.println("Tutorial schema successfully created");
		System.out.println();

		System.out.println("Vendor Table");
		System.out.println("************");

		/* Create the Vendor type in the database and save the type ID, needed
		 * to create a table in the next step; see classes above for type
		 * definition */
		String vendorTypeId = RecordObject.createType(Vendor.class, kdb);

		// Create the Vendor table using a request object
		CreateTableRequest vendorCreateReq = new CreateTableRequest();
		vendorCreateReq.setTableName(TABLE_VENDOR);
		vendorCreateReq.setTypeId(vendorTypeId);
		vendorCreateReq.setOptions(GPUdb.options(CreateTableRequest.Options.IS_REPLICATED, "true"));

		kdb.createTable(vendorCreateReq);
		System.out.println("Vendor table successfully created");
		System.out.println();

		System.out.println("Payment Table");
		System.out.println("*************");

		// Create the Payment table using individual parameters
		String paymentTypeId = RecordObject.createType(Payment.class, kdb);
		kdb.createTable(TABLE_PAYMENT, paymentTypeId, null);
		System.out.println("Payment table successfully created");
		System.out.println();

		System.out.println("Taxi Table");
		System.out.println("**********");
		String taxiTypeId = RecordObject.createType(TaxiTripData.class, kdb);
		kdb.createTable(TABLE_TAXI, taxiTypeId, null);
		System.out.println("Taxi table successfully created");


		System.out.println("\n");
		System.out.println("INSERTING DATA");
		System.out.println("--------------");
		System.out.println();

		// Insert single record example
		// Create a record object and assign values to properties
		Payment paymentDatum = new Payment();
		paymentDatum.payment_id = 189;
		paymentDatum.payment_type = "No Charge";
		paymentDatum.credit_type = null;
		paymentDatum.payment_timestamp = null;
		paymentDatum.fare_amount = 6.5;
		paymentDatum.surcharge = 0;
		paymentDatum.mta_tax = 0.6;
		paymentDatum.tip_amount = 0;
		paymentDatum.tolls_amount = 0;
		paymentDatum.total_amount = 7.1;

		// Insert the record into the table
		int numInserted = kdb.insertRecords(TABLE_PAYMENT, Arrays.asList(paymentDatum), null).getCountInserted();
		System.out.println("Number of records inserted into the Payment table:  " + numInserted);

		// Insert multiple records examples
		/* Create a list of in-line records. The order of the values must match
		 * the column order in the type */
		List<Vendor> vendorRecords = new ArrayList<>();
		vendorRecords.add(new Vendor(
				"VTS","Vine Taxi Service","9998880001","admin@vtstaxi.com",
				"26 Summit St.","Flushing","NY",11354,450,400));
		vendorRecords.add(new Vendor(
				"YCAB","Yes Cab","7895444321",null,
				"97 Edgemont St.","Brooklyn","NY",11223,445,425));
		vendorRecords.add(new Vendor(
				"NYC","New York City Cabs",null,"support@nyc-taxis.com",
				"9669 East Bayport St.","Bronx","NY",10453,505,500));
		vendorRecords.add(new Vendor(
				"DDS","Dependable Driver Service",null,null,
				"8554 North Homestead St.","Bronx","NY",10472,200,124));
		vendorRecords.add(new Vendor(
				"CMT","Crazy Manhattan Taxi","9778896500","admin@crazymanhattantaxi.com",
				"950 4th Road Suite 78","Brooklyn","NY",11210,500,468));
		vendorRecords.add(new Vendor(
				"TNY","Taxi New York",null,null,
				"725 Squaw Creek St.","Bronx","NY",10458,315,305));
		vendorRecords.add(new Vendor(
				"NYMT","New York Metro Taxi",null,null,
				"4 East Jennings St.","Brooklyn","NY",11228,166,150));
		vendorRecords.add(new Vendor(
				"5BTC","Five Boroughs Taxi Co.","4566541278","mgmt@5btc.com",
				"9128 Lantern Street","Brooklyn","NY",11229,193,175));

		// Insert the records into the Vendor table
		numInserted = kdb.insertRecords(TABLE_VENDOR, vendorRecords, null).getCountInserted();
		System.out.println("Number of records inserted into the Vendor table:  " + numInserted);

		// Create another list of in-line records
		List<Payment> paymentRecords = new ArrayList<>();
		paymentRecords.add(new Payment(136,"Cash",null,1428716521000L,4,0.5,0.5,1,0,6.3));
		paymentRecords.add(new Payment(148,"Cash",null,1430124581000L,9.5,0,0.5,1,0,11.3));
		paymentRecords.add(new Payment(114,"Cash",null,1428259673000L,5.5,0,0.5,1.89,0,8.19));
		paymentRecords.add(new Payment(180,"Cash",null,1428965823000L,6.5,0.5,0.5,1,0,8.8));
		paymentRecords.add(new Payment(109,"Cash",null,1428948513000L,22.5,0.5,0.5,4.75,0,28.55));
		paymentRecords.add(new Payment(132,"Cash",null,1429472779000L,6.5,0.5,0.5,1.55,0,9.35));
		paymentRecords.add(new Payment(134,"Cash",null,1429472668000L,33.5,0.5,0.5,0,0,34.8));
		paymentRecords.add(new Payment(176,"Cash",null,1428403962000L,9,0.5,0.5,2.06,0,12.36));
		paymentRecords.add(new Payment(100,"Cash",null,null,9,0,0.5,2.9,0,12.7));
		paymentRecords.add(new Payment(193,"Cash",null,null,3.5,1,0.5,1.59,0,6.89));
		paymentRecords.add(new Payment(140,"Credit","Visa",null,28,0,0.5,0,0,28.8));
		paymentRecords.add(new Payment(161,"Credit","Visa",null,7,0,0.5,0,0,7.8));
		paymentRecords.add(new Payment(199,"Credit","Visa",null,6,1,0.5,1,0,8.5));
		paymentRecords.add(new Payment(159,"Credit","Visa",1428674487000L,7,0,0.5,0,0,7.8));
		paymentRecords.add(new Payment(156,"Credit","MasterCard",1428672753000L,12.5,0.5,0.5,0,0,13.8));
		paymentRecords.add(new Payment(198,"Credit","MasterCard",1429472636000L,9,0,0.5,0,0,9.8));
		paymentRecords.add(new Payment(107,"Credit","MasterCard",1428717377000L,5,0.5,0.5,0,0,6.3));
		paymentRecords.add(new Payment(166,"Credit","American Express",1428808723000L,17.5,0,0.5,0,0,18.3));
		paymentRecords.add(new Payment(187,"Credit","American Express",1428670181000L,14,0,0.5,0,0,14.8));
		paymentRecords.add(new Payment(125,"Credit","Discover",1429869673000L,8.5,0.5,0.5,0,0,9.8));
		paymentRecords.add(new Payment(119,null,null,1430431471000L,9.5,0,0.5,0,0,10.3));
		paymentRecords.add(new Payment(150,null,null,1430432447000L,7.5,0,0.5,0,0,8.3));
		paymentRecords.add(new Payment(170,"No Charge",null,1430431502000L,28.6,0,0.5,0,0,28.6));
		paymentRecords.add(new Payment(123,"No Charge",null,1430136649000L,20,0.5,0.5,0,0,21.3));
		paymentRecords.add(new Payment(181,null,null,1430135461000L,6.5,0.5,0.5,0,0,7.8));

		// Insert the records into the Payment table
		numInserted = kdb.insertRecords(TABLE_PAYMENT, paymentRecords, null).getCountInserted();
		System.out.println("Number of records inserted into the Payment table:  " + numInserted);

		// Insert records from a CSV File into the Taxi table via KiFS
		GPUdbFileHandler fh = new GPUdbFileHandler(kdb);
		fh.ingest(Arrays.asList(CSV_FILE_PATH), TABLE_TAXI, null, null);

		numInserted = (int)kdb.showTable(TABLE_TAXI, GPUdb.options(ShowTableRequest.Options.GET_SIZES, "true")).getTotalSize();
		System.out.println("Number of records inserted into the Taxi table:  " + numInserted);

		System.out.println("\n");
		System.out.println("RETRIEVING DATA");
		System.out.println("---------------");
		System.out.println();

		// Retrieve no more than 10 records from payments using in-line request parameters
		GetRecordsResponse<Payment> getPaymentRecordsResp = kdb.getRecords(
				TABLE_PAYMENT,
				0,
				10,
				GPUdb.options(GetRecordsRequest.Options.SORT_BY,"payment_id")
		);
		System.out.println(
				"Payment ID Payment Type Credit Type Payment Timestamp " +
				"Fare Amount Surcharge MTA Tax Tip Amount Tolls Amount Total Amount"
		);
		System.out.println(
				"========== ============ =========== ================= " +
				"=========== ========= ======= ========== ============ ============"
		);
		for (Payment p : getPaymentRecordsResp.getData())
			System.out.printf(
					"%10d %-12s %-11s %17s %11.2f %9.2f %7.2f %10.2f %12.2f %12.2f%n",
					p.payment_id, Objects.toString(p.payment_type, ""), Objects.toString(p.credit_type, ""),
					Objects.toString(p.payment_timestamp, ""), p.fare_amount, p.surcharge, p.mta_tax,
					p.tip_amount, p.tolls_amount, p.total_amount
			);
		System.out.println();

		// Retrieve all records from the Vendor table using a request object
		GetRecordsRequest vendorReq = new GetRecordsRequest();
		vendorReq.setTableName(TABLE_VENDOR);
		vendorReq.setOffset(0);
		vendorReq.setLimit(GPUdb.END_OF_SET);
		vendorReq.setOptions(GPUdb.options(GetRecordsRequest.Options.SORT_BY, "vendor_id"));
		GetRecordsResponse<Vendor> vendorResp = kdb.getRecords(vendorReq);
		System.out.println(
				"Vendor ID Vendor Name                Phone       Email                         " +
				"HQ Street                HQ City  HQ State HQ Zip # Employees # Cabs"
		);
		System.out.println(
				"========= ========================== =========== ============================= " +
				"======================== ======== ======== ====== =========== ======"
		);
		for (Vendor v : vendorResp.getData())
			System.out.printf(
					"%-9s %-26s %-11s %-29s %-24s %-8s %-8s %-6d %11d %6d%n",
					v.vendor_id, v.vendor_name, Objects.toString(v.phone, ""), Objects.toString(v.email, ""),
					v.hq_street, v.hq_city, v.hq_state, v.hq_zip, v.num_emps, v.num_cabs
			);
		System.out.println();

		
		System.out.println();
		System.out.println("UPDATING RECORDS");
		System.out.println("----------------");
		System.out.println();

		// Update the e-mail, number of employees, and number of cabs of the DDS vendor
		List<Map<String, String>> newValsList = new ArrayList<>();
		Map<String,String> newVals = new HashMap<>();
		newVals.put("email", "'management@ddstaxico.com'");
		newVals.put("num_emps", "num_emps + 2");
		newVals.put("num_cabs", "num_cabs + 1");
		newValsList.add(newVals);
		kdb.updateRecords(
				TABLE_VENDOR,
				Arrays.asList("vendor_id = 'DDS'"),
				newValsList,
				null,
				GPUdb.options(
						UpdateRecordsRequest.Options.USE_EXPRESSIONS_IN_NEW_VALUES_MAPS,
						UpdateRecordsRequest.Options.TRUE
				)
		);
		GetRecordsResponse<Vendor> updVendRsp = kdb.getRecords(
				TABLE_VENDOR,
				0,
				GPUdb.END_OF_SET,
				GPUdb.options(GetRecordsRequest.Options.EXPRESSION, "vendor_id = 'DDS'")
		);

		System.out.println("Updated DDS vendor information:");
		System.out.println(
				"Vendor ID Vendor Name               Phone Email                    " +
				"HQ Street                HQ City HQ State HQ Zip # Employees # Cabs"
		);
		System.out.println(
				"========= ========================= ===== ======================== " +
				"======================== ======= ======== ====== =========== ======"
		);
		for (Vendor v : updVendRsp.getData())
			System.out.printf(
					"%-9s %-25s %-5s %-24s %-24s %-7s %-8s %-6d %11d %6d%n",
					v.vendor_id, v.vendor_name, Objects.toString(v.phone, ""), v.email,
					v.hq_street, v.hq_city, v.hq_state, v.hq_zip, v.num_emps, v.num_cabs
			);
		System.out.println();


		System.out.println();
		System.out.println("DELETING RECORDS");
		System.out.println("----------------");
		System.out.println();

		// Delete payment 189
		long preDelRecCount = kdb.getRecords(TABLE_PAYMENT, 0, GPUdb.END_OF_SET, null).getTotalNumberOfRecords();
		System.out.println("Records in the payment table (before delete): " + preDelRecCount);
		String delExpr = "payment_id = 189";
		System.out.println("Deleting record where " + delExpr);
		kdb.deleteRecords(TABLE_PAYMENT, Arrays.asList(delExpr), null);
		long postDelRecCount = kdb.getRecords(TABLE_PAYMENT, 0, GPUdb.END_OF_SET, null).getTotalNumberOfRecords();
		System.out.println("Records in the payment table (after delete): " + postDelRecCount);
		System.out.println();


		System.out.println();
		System.out.println("ALTER TABLE");
		System.out.println("-----------");
		System.out.println();

		System.out.println("Indexes");
		System.out.println("*******");

		/* Add column indexes on:
		 *   - payment table, fare_amount (for query-chaining filter example)
		 *   - taxi table, passenger_count (for filter-by-range example) */
		kdb.alterTable(TABLE_PAYMENT, AlterTableRequest.Action.CREATE_INDEX, "fare_amount", null);

		kdb.alterTable(TABLE_TAXI, AlterTableRequest.Action.CREATE_INDEX, "passenger_count", null);
		System.out.println("Indexes added successfully");
		System.out.println();

		System.out.println("Dictionary Encoding");
		System.out.println("*******************");

		String columnName = "vendor_id";

		// Display memory usage before dictionary encoding
		String preDictEncColInfoJson = kdb.showTable(
				TABLE_TAXI,
				GPUdb.options(
						ShowTableRequest.Options.GET_COLUMN_INFO,
						ShowTableRequest.Options.TRUE
				)
		).getAdditionalInfo().get(0).get(ShowTableResponse.AdditionalInfo.COLUMN_INFO);
		String preDictEncMemUsage = JSON.readTree(preDictEncColInfoJson)
				.get(columnName)
				.get("memory_usage")
				.asText();
		System.out.println(
				"Memory usage (in bytes) for '" + columnName + "' column " +
				"before adding dictionary encoding: " + preDictEncMemUsage
		);

		// Apply dictionary encoding to the payment type column
		AlterTableResponse dictEncResp = kdb.alterTable(
				TABLE_TAXI,
				AlterTableRequest.Action.CHANGE_COLUMN,
				columnName,
				GPUdb.options(
						AlterTableRequest.Options.COLUMN_PROPERTIES,
						"char4,dict"
				)
		);
		List<String> dictEncPropList = dictEncResp.getProperties().get(columnName);
		System.out.println(
				"Dictionary encoding added to '" + columnName + "' column " +
				"properties list:  " + dictEncPropList
		);

		// Display memory usage after dictionary encoding
		String postDictEncColInfoJson = kdb.showTable(
				TABLE_TAXI,
				GPUdb.options(
						ShowTableRequest.Options.GET_COLUMN_INFO,
						ShowTableRequest.Options.TRUE
				)
		).getAdditionalInfo().get(0).get(ShowTableResponse.AdditionalInfo.COLUMN_INFO);
		String postDictEncMemUsage = JSON.readTree(postDictEncColInfoJson)
				.get(columnName)
				.get("memory_usage")
				.asText();
		System.out.println(
				"Memory usage (in bytes) for '" + columnName + "' column " +
				"after adding dictionary encoding: " + postDictEncMemUsage
		);
		System.out.println();


		System.out.println();
		System.out.println("FILTERING");
		System.out.println("---------");
		System.out.println();

		// Filter Example 1
		// Filter for only payments with no corresponding payment type, returning the
		// count of records found
		long f1Count = kdb.filter(TABLE_PAYMENT, VIEW_EXAMPLE1, "IS_NULL(payment_type)", null).getCount();
		System.out.println("Number of null payments:  " + f1Count);

		// Filter Example 2
		// Using query chaining, filter null payment type records with a fare amount greater than 8
		long f2Count = kdb.filter(VIEW_EXAMPLE1, VIEW_EXAMPLE2, "fare_amount > 8", null).getCount();
		System.out.println("Number of null payments with a fare amount greater than $8.00 (with query chaining):  " + f2Count);

		// Filter Example 3
		// Filter by list where vendor ID is either NYC or YCAB
		Map<String, List<String>> columnValuesMap = new HashMap<>();
		columnValuesMap.put("vendor_id", Arrays.asList("NYC", "YCAB"));
		long f3Count = kdb.filterByList(TABLE_TAXI, VIEW_EXAMPLE3, columnValuesMap, null).getCount();
		System.out.println("Number of records where vendor is either NYC or YCAB:  " + f3Count);

		// Filter Example 4
		// Filter by range trip with passenger count between 1 and 3
		long f4Count = kdb.filterByRange(TABLE_TAXI, VIEW_EXAMPLE4, "passenger_count", 1, 3, null).getCount();
		System.out.println("Number of trips with a passenger count between 1 and 3:  " + f4Count);


		System.out.println("\n");
		System.out.println("AGGREGATING, GROUPING, & HISTOGRAMS");
		System.out.println("-----------------------------------");
		System.out.println();

		// Aggregate Example 1
		// Aggregate count, min, mean, and max on the trip distance
		Map<String,Double> a1Resp = kdb.aggregateStatistics(
				TABLE_TAXI,
				"trip_distance",
				AggregateStatisticsRequest.Stats.COUNT + "," +
				AggregateStatisticsRequest.Stats.MIN + "," +
				AggregateStatisticsRequest.Stats.MAX + "," +
				AggregateStatisticsRequest.Stats.MEAN,
				null
		).getStats();
		System.out.println("Statistics of values in the trip_distance column:");
		System.out.printf(
				"\tCount: %5.0f%n\tMin:   %5.2f%n\tMean:  %5.2f%n\tMax:   %5.2f%n%n",
				a1Resp.get(AggregateStatisticsRequest.Stats.COUNT),
				a1Resp.get(AggregateStatisticsRequest.Stats.MIN),
				a1Resp.get(AggregateStatisticsRequest.Stats.MEAN),
				a1Resp.get(AggregateStatisticsRequest.Stats.MAX)
		);

		// Aggregate Example 2
		// Find unique taxi vendor IDs
		List<Record> a2Resp = kdb.aggregateUnique(TABLE_TAXI, "vendor_id", 0, GPUdb.END_OF_SET, null).getData();
		System.out.println("Unique vendor IDs in the taxi trip table:");
		for (Record vendor : a2Resp)
			System.out.println("\t* " + vendor.get("vendor_id"));
		System.out.println();

		// Aggregate Example 3
		// Find number of trips per vendor
		List <String> colNames = Arrays.asList("vendor_id", "count(vendor_id)");
		List<Record> a3Resp = kdb.aggregateGroupBy(
				TABLE_TAXI,
				colNames,
				0,
				GPUdb.END_OF_SET,
				GPUdb.options(
						AggregateGroupByRequest.Options.SORT_BY,
						AggregateGroupByRequest.Options.KEY
				)
		).getData();
		System.out.println("Trips per vendor:");
		for (Record vendor : a3Resp)
			System.out.printf("\t%-6s %3d%n", vendor.get("vendor_id") + ":", vendor.get("count(vendor_id)"));
		System.out.println();

		// Aggregate Example 4
		// Create a histogram for the different groups of passenger counts
		float start = 1;
		float end = 6;
		float interval = 1;
		List<Double> a4Resp = kdb.aggregateHistogram(
				TABLE_TAXI,
				"passenger_count",
				start,
				end,
				interval,
				null
		).getCounts();

		System.out.println("Passenger count groups by size:");
		System.out.println("Passengers Total Trips");
		System.out.println("========== ===========");
		List<String> countGroups = Arrays.asList("1", "2", "3", "4", ">5");
		for (int hgNum = 0; hgNum < a4Resp.size(); hgNum++)
			System.out.printf("%10s %11.0f%n", countGroups.get(hgNum), a4Resp.get(hgNum));

		
		System.out.println("\n");
		System.out.println("JOINS");
		System.out.println("-----");
		System.out.println();

		// Join Example 1 (Inner Join)
		/* Retrieve cab ride transactions and the full name of the associated
		 * vendor for rides having more than three passengers between April 1st
		 * & 16th, 2015 */
		kdb.createJoinTable(
				JOIN_TABLE_INNER,
				Arrays.asList(TABLE_TAXI + " as t", TABLE_PAYMENT + " as p"),
				Arrays.asList(
						"t.payment_id", "payment_type", "total_amount",
						"passenger_count", "vendor_id", "trip_distance"
				),
				Arrays.asList("t.payment_id = p.payment_id", "passenger_count > 3"),
				null
		);
		GetRecordsByColumnResponse j1Resp = kdb.getRecordsByColumn(
				JOIN_TABLE_INNER,
				Arrays.asList(
						"payment_id", "payment_type", "total_amount",
						"passenger_count", "vendor_id", "trip_distance"
				),
				0,
				GPUdb.END_OF_SET,
				GPUdb.options(GetRecordsByColumnRequest.Options.ORDER_BY, "payment_id")
		);
		List<Record> innerJoinRecs = j1Resp.getData();
		System.out.println("Payment information for rides having more than three passengers:");
		System.out.println(
				"Payment ID Payment Type Total Amount Passenger Count " +
				"Vendor ID Trip Distance");
		System.out.println(
				"========== ============ ============ =============== " +
				"========= =============");
		for (Record rec : innerJoinRecs) {
			List<Type.Column> columns = rec.getType().getColumns();
			System.out.printf(
					"%10s %-12s %12.2f %15d %-9s %13.2f%n",
					rec.get(0), rec.get(1), rec.get(2), rec.get(3), rec.get(4), rec.get(5)
			);
		}
		System.out.println();

		// Join example 2 (Left Join)
		/* Retrieve cab ride transactions and the full name of the associated
		 * vendor (if available--blank if vendor name is unknown) for
		 * transactions with associated payment data, sorting by increasing
		 * values of transaction ID. */
		kdb.createJoinTable(
				JOIN_TABLE_LEFT,
				Arrays.asList(TABLE_TAXI + " as t", TABLE_VENDOR + " as v"),
				Arrays.asList("transaction_id", "pickup_datetime", "trip_distance", "t.vendor_id", "vendor_name"),
				Arrays.asList("left join t, v on (t.vendor_id = v.vendor_id)", "payment_id <> 0"),
				null
		);
		GetRecordsByColumnResponse j2Resp = kdb.getRecordsByColumn(
				JOIN_TABLE_LEFT,
				Arrays.asList("transaction_id", "pickup_datetime", "trip_distance","vendor_id", "vendor_name"),
				0,
				GPUdb.END_OF_SET,
				GPUdb.options(GetRecordsByColumnRequest.Options.ORDER_BY, "transaction_id")
		);
		List<Record> leftJoinRecs = j2Resp.getData();
		System.out.println("Transaction, trip, and vendor information where Payment ID is not null:");
		System.out.println(
				"Transaction ID Pickup (in secs since Epoch) " +
				"Trip Distance Vendor ID Vendor Name"
		);
		System.out.println(
				"============== ============================ " +
				"============= ========= =================="
		);
		for (Record rec : leftJoinRecs) {
			List<Type.Column> columns = rec.getType().getColumns();
			System.out.printf(
					"%-14s %28d %13.2f %-9s %-18s%n",
					rec.get(0), rec.get(1), rec.get(2), rec.get(3), Objects.toString(rec.get(4), "")
			);
		}

	    /* Full outer joins require both tables to be replicated. Set merges like
	     * Union Distinct, Intersect, and Except need to use replicated tables to
	     * ensure the correct results. Create a replicated version of the taxi trip
	     * data using createProjection. */
		kdb.createProjection(
				TABLE_TAXI,
				TABLE_TAXI_REPLICATED,
				Arrays.asList(
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
				),
				GPUdb.options(CreateProjectionRequest.Options.IS_REPLICATED, "true")
		);

		// Join Example 3 (Full Outer Join)
		/* Retrieve the vendor IDs of known vendors with no recorded cab ride
		 * transactions, as well as the vendor ID and number of transactions
		 * for unknown vendors with recorded cab ride transactions */
		kdb.createJoinTable(
				JOIN_TABLE_OUTER,
				Arrays.asList(TABLE_TAXI_REPLICATED + " as t", TABLE_VENDOR + " as v"),
				Arrays.asList("t.vendor_id as vendor_id", "v.vendor_id as vendor_id_1"),
				Arrays.asList("full_outer join t,v on ((v.vendor_id = t.vendor_id))"),
				null
		);

		/* Aggregate the join table results by vendor ID and count the amount of
		 * records */
		List<Record> j3Resp = kdb.aggregateGroupBy(
				JOIN_TABLE_OUTER,
				Arrays.asList(
						"vendor_id_1 as vend_table_vendors",
						"vendor_id as taxi_table_vendors",
						"count(*) as total_records"
				),
				0,
				GPUdb.END_OF_SET,
				GPUdb.options(
						AggregateGroupByRequest.Options.EXPRESSION,
						"(is_null(vendor_id_1) OR is_null(vendor_id))",
						AggregateGroupByRequest.Options.SORT_BY,
						AggregateGroupByRequest.Options.KEY
				)
		).getData();
		System.out.println();
		System.out.println("Known vendors with no transactions and unknown vendors with transactions:");
		System.out.println("Vend. Table Vendors Taxi Table Vendors Total Records");
		System.out.println("=================== ================== =============");
		for (Record vendor : j3Resp)
			System.out.printf(
					"%-19s %-18s %13s%n",
					Objects.toString(vendor.get("vend_table_vendors"), "<Unknown Vendor>"),
					Objects.toString(vendor.get("taxi_table_vendors"), "<No Transactions>"),
					vendor.get("total_records")
			);


		System.out.println("\n");
		System.out.println("PROJECTIONS");
		System.out.println("-----------");
		System.out.println();

		// Projection Example 1
		// Create a projection containing all payments by credit card
		kdb.createProjection(
				TABLE_PAYMENT,
				PROJECTION_EXAMPLE1,
				Arrays.asList(
						"payment_id", "payment_type", "credit_type",
						"payment_timestamp", "fare_amount", "surcharge",
						"mta_tax", "tip_amount", "tolls_amount", "total_amount"
				),
				GPUdb.options(CreateProjectionRequest.Options.EXPRESSION, "payment_type = 'Credit'")
		);
		GetRecordsByColumnResponse p1Resp = kdb.getRecordsByColumn(
				PROJECTION_EXAMPLE1,
				Arrays.asList(
						"payment_id", "payment_type", "credit_type",
						"payment_timestamp", "fare_amount", "surcharge",
						"mta_tax", "tip_amount", "tolls_amount", "total_amount"
				),
				0,
				GPUdb.END_OF_SET,
				GPUdb.options(GetRecordsByColumnRequest.Options.ORDER_BY, "payment_id")
		);
		List<Record> credPayRecs = p1Resp.getData();
		System.out.println("Projection of only credit payment types:");
		System.out.println(
				"Payment ID Payment Type Credit Type      Timestamp     " +
				"Fare  Surcharge MTA Tax Tip   Tolls Total"
		);
		System.out.println(
				"========== ============ ================ ============= " +
				"===== ========= ======= ===== ===== ====="
		);
		for (Record rec : credPayRecs) {
			List<Type.Column> columns = rec.getType().getColumns();
			System.out.printf(
					"%10s %-12s %-16s %13s " +
					"%5.2f %9.2f %7.2f %5.2f %5.2f %5.2f%n",
					rec.get(0), rec.get(1), rec.get(2), Objects.toString(rec.get(3), ""),
					rec.get(4), rec.get(5), rec.get(6), rec.get(7), rec.get(8), rec.get(9)
			);
		}

		// Projection Example 2
		/* Create a persisted table with cab ride transactions greater than 5
		 * miles whose trip started during lunch hours */
		kdb.createProjection(
				TABLE_TAXI,
				PROJECTION_EXAMPLE2,
				Arrays.asList(
						"hour(pickup_datetime) as hour_of_day", "vendor_id",
						"passenger_count", "trip_distance"
				),
				GPUdb.options(
						CreateProjectionRequest.Options.EXPRESSION,
						"(hour(pickup_datetime) >= 11) AND " +
						"(hour(pickup_datetime) <= 14) AND " +
						"(trip_distance > 5)",
						CreateProjectionRequest.Options.PERSIST,
						CreateProjectionRequest.Options.TRUE
				)
		);
		GetRecordsByColumnResponse p2Resp = kdb.getRecordsByColumn(
				PROJECTION_EXAMPLE2,
				Arrays.asList("hour_of_day", "vendor_id", "passenger_count", "trip_distance"),
				0,
				GPUdb.END_OF_SET,
				GPUdb.options(
						GetRecordsByColumnRequest.Options.ORDER_BY,
						"hour_of_day, vendor_id, passenger_count, trip_distance"
				)
		);
		List<Record> lunchRecs = p2Resp.getData();
		System.out.println();
		System.out.println("Projection of long trips taken during lunch hours:");
		System.out.println("Hour of Day Vendor ID Passenger Count Trip Distance");
		System.out.println("=========== ========= =============== =============");
		for (Record rec : lunchRecs) {
			Type type = rec.getType();
			List<Type.Column> columns = type.getColumns();
			System.out.printf(
					"%11s %-9s %15s %13.2f%n",
					rec.get(0), rec.get(1), rec.get(2), rec.get(3)
			);
		}


		System.out.println("\n");
		System.out.println("UNION, INTERSECT, & EXCEPT");
		System.out.println("--------------------------");
		System.out.println();

		// Union Example 1 (Union All)
		/* Calculate the average number of passengers, as well as the shortest,
		 * average, and longest trips for all trips in each of the two time
		 * periods--from April 1st through the 15th, 2015 and from April 16th
		 * through the 23rd, 2015--and return those two sets of statistics in a
		 * single result set. */
		kdb.aggregateGroupBy(
				TABLE_TAXI,
				Arrays.asList(
						"avg(passenger_count) as avg_pass_count",
						"avg(trip_distance) as avg_trip_dist",
						"min(trip_distance) as min_trip_dist",
						"max(trip_distance) as max_trip_dist"
				),
				0,
				GPUdb.END_OF_SET,
				GPUdb.options(
						AggregateGroupByRequest.Options.EXPRESSION,
						"((pickup_datetime >= '2015-04-01') AND " +
						"(pickup_datetime <= '2015-04-15 23:59:59.999'))",
						AggregateGroupByRequest.Options.RESULT_TABLE,
						AGG_GRPBY_UNION_ALL_SRC1
				)
		);
		kdb.aggregateGroupBy(
				TABLE_TAXI,
				Arrays.asList(
						"avg(passenger_count) as avg_pass_count",
						"avg(trip_distance) as avg_trip_dist",
						"min(trip_distance) as min_trip_dist",
						"max(trip_distance) as max_trip_dist"
				),
				0,
				GPUdb.END_OF_SET,
				GPUdb.options(
						AggregateGroupByRequest.Options.EXPRESSION,
						"((pickup_datetime >= '2015-04-16') AND " +
						"(pickup_datetime  <= '2015-04-23 23:59:59.999'))",
						AggregateGroupByRequest.Options.RESULT_TABLE,
						AGG_GRPBY_UNION_ALL_SRC2
				)
		);
		kdb.createUnion(
				UNION_ALL_TABLE,
				Arrays.asList(AGG_GRPBY_UNION_ALL_SRC1, AGG_GRPBY_UNION_ALL_SRC2),
				Arrays.asList(
						Arrays.asList(
								"'2015-04-01 - 2015-04-15'",
								"avg_pass_count", "avg_trip_dist",
								"min_trip_dist", "max_trip_dist"
						),
						Arrays.asList(
								"'2015-04-16 - 2015-04-23'",
								"avg_pass_count", "avg_trip_dist",
								"min_trip_dist", "max_trip_dist"
						)
				),
				Arrays.asList(
						"pickup_window_range", "avg_pass_count",
						"avg_trip", "min_trip", "max_trip"
				),
				GPUdb.options(CreateUnionRequest.Options.MODE, CreateUnionRequest.Options.UNION_ALL)
		);
		GetRecordsByColumnResponse u1Resp = kdb.getRecordsByColumn(
				UNION_ALL_TABLE,
				Arrays.asList("pickup_window_range", "avg_pass_count", "avg_trip", "min_trip", "max_trip"),
				0,
				GPUdb.END_OF_SET,
				null
		);
		List<Record> unionAllRecs = u1Resp.getData();
		System.out.println("Passenger statistics for each half of April:");
		System.out.println("Pickup Window Range     Avg. Pass. Count Avg. Trip Min. Trip Max. Trip");
		System.out.println("======================= ================ ========= ========= =========");
		for (Record rec : unionAllRecs) {
			List<Type.Column> columns = rec.getType().getColumns();
			System.out.printf(
					"%-23s %16.1f %9.2f %9.2f %9.2f%n",
					rec.get(0), rec.get(1), rec.get(2), rec.get(3), rec.get(4)
			);
		}
		System.out.println();

		// Union Example 2 (Intersect)
		/* Retrieve locations (as lat/lon pairs) that were both pick-up and
		 * drop-off points */
		kdb.createUnion(
				UNION_INTERSECT_TABLE,
				Arrays.asList(TABLE_TAXI_REPLICATED, TABLE_TAXI_REPLICATED),
				Arrays.asList(
						Arrays.asList("pickup_latitude", "pickup_longitude"),
						Arrays.asList("dropoff_latitude", "dropoff_longitude")
				),
				Arrays.asList("latitude", "longitude"),
				GPUdb.options(CreateUnionRequest.Options.MODE, CreateUnionRequest.Options.INTERSECT)
		);
		GetRecordsByColumnResponse u2Resp = kdb.getRecordsByColumn(
				UNION_INTERSECT_TABLE,
				Arrays.asList("latitude", "longitude"),
				0,
				GPUdb.END_OF_SET,
				GPUdb.options(
						GetRecordsByColumnRequest.Options.EXPRESSION,
						"((latitude <> 0) AND (longitude <> 0))",
						GetRecordsByColumnRequest.Options.ORDER_BY,
						"latitude, longitude"
				)
		);
		List<Record> intersectRecs = u2Resp.getData();
		System.out.println("Latitude/Longitude pairs that were both pick-up and drop-off points:");
		System.out.println("Latitude    Longitude");
		System.out.println("=========== ============");
		for (Record rec : intersectRecs) {
			List<Type.Column> columns = rec.getType().getColumns();
			System.out.printf("%11.8f %12.8f%n", rec.get(0), rec.get(1));
		}
		System.out.println();

		// Union Example 3 (Except)
		/* Show vendors that operate before noon, but not after noon: retrieve
		 * the unique list of IDs of vendors who provided cab rides between
		 * midnight and noon, and remove from that list the IDs of any vendors
		 * who provided cab rides between noon and midnight */
		kdb.createProjection(
				TABLE_TAXI_REPLICATED,
				PROJECTION_EXCEPT_SRC1,
				Arrays.asList("vendor_id"),
				GPUdb.options(
						CreateProjectionRequest.Options.EXPRESSION,
						"((HOUR(pickup_datetime) >= 0) AND (HOUR(pickup_datetime) <= 11))"
				)
		);
		kdb.createProjection(
				TABLE_TAXI_REPLICATED,
				PROJECTION_EXCEPT_SRC2,
				Arrays.asList("vendor_id"),
				GPUdb.options(
						CreateProjectionRequest.Options.EXPRESSION,
						"((HOUR(pickup_datetime) >= 12) AND (HOUR(pickup_datetime) <= 23))"
				)
		);
		kdb.createUnion(
				UNION_EXCEPT_TABLE,
				Arrays.asList(PROJECTION_EXCEPT_SRC1, PROJECTION_EXCEPT_SRC2),
				Arrays.asList(Arrays.asList("vendor_id"), Arrays.asList("vendor_id")),
				Arrays.asList("vendor_id"),
				GPUdb.options(CreateUnionRequest.Options.MODE, CreateUnionRequest.Options.EXCEPT)
		);
		GetRecordsByColumnResponse u3Resp = kdb.getRecordsByColumn(
				UNION_EXCEPT_TABLE,
				Arrays.asList("vendor_id"),
				0,
				GPUdb.END_OF_SET,
				null
		);
		List<Record> exceptRecs = u3Resp.getData();
		System.out.println("Vendors that operate between midnight and noon:");
		System.out.println("Vendor ID");
		System.out.println("=========");
		for (Record rec : exceptRecs) {
			Type type = rec.getType();
			List<Type.Column> columns = type.getColumns();
			for (int i=0;i<columns.size();i++)
				System.out.printf("%-9s", rec.get(i));
			System.out.println();
		}

	} // end main

} // end class Tutorial
