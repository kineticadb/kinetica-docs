import com.gpudb.*;
import com.gpudb.protocol.*;

import java.util.*;
import java.util.concurrent.*;

import java.time.*;



/*
 * Distributed Ingest & Key Lookup with the Java API
 *
 * This example will demonstrate both distributed ingestion and key lookup.
 * 
 * It makes use of an order_history table for ingestion and a store_sales
 * materialized view for key lookup, which need to be created beforehand.
 */
public class DistributedIOUseCase
{
	private static final String TABLE_NAME_HISTORY = "order_history";
	private static final String VIEW_NAME_SALES = "store_sales";
	private static final int TOTAL_STORES = 10;
	
	private final GPUdb db;
	private final String schemaName;
	private final String tableNameHistory;
	private final String viewNameSales;


	public DistributedIOUseCase(String url, String user, String pass, String schema) throws GPUdbException
	{
		GPUdbBase.Options options = new GPUdbBase.Options();
		options.setUsername(user);
		options.setPassword(pass);
		this.db = new GPUdb(url, options);

		this.schemaName = schema;
		this.tableNameHistory = (schema == null || schema.isEmpty()) ? TABLE_NAME_HISTORY : schema + "." + TABLE_NAME_HISTORY;
		this.viewNameSales = (schema == null || schema.isEmpty()) ? VIEW_NAME_SALES : schema + "." + VIEW_NAME_SALES;
	}

	/*
	 * Helper class for parallelizing usage of the bulk ingest object.
	 * 
	 * This class will generate a batch of inserts of a given size, starting at
	 * a given index, and then add them to a given BulkInserter
	 */
	private static class BatchInsert implements Runnable
	{
		/* Bulk ingestion object to use for inserting records*/
		BulkInserter<GenericRecord> bulkInserter;
		/* Database type schema of records being inserted */
		Type type;
		/* ID/index of first record */
		int startIndex;
		/* Number of records to insert */
		int batchSize;

		/*
		 * Creates a new batch insert object, which will generate objects of the
		 * specified type and add them to the specified bulk ingest object
		 * 
		 * @param bulkInserter bulk ingest object to which records will be added
		 * @param type database type schema to use for objects being inserted
		 * @param startIndex starting index of records being inserted; will be
		 *        used as order ID for inserted records
		 * @param batchSize number of records to insert in this batch
		 */
		public BatchInsert(BulkInserter<GenericRecord> bulkInserter, Type type, int startIndex, int batchSize)
		{
			this.bulkInserter = bulkInserter;
			this.type = type;
			this.startIndex = startIndex;
			this.batchSize = batchSize;
		}

		public void run()
		{
			try
			{
				int endIndex = this.startIndex + this.batchSize;

				for (int recIndex = this.startIndex; recIndex < endIndex; recIndex++)
				{
					// Generate data
					final int orderId = recIndex;
					final int storeId = ThreadLocalRandom.current().nextInt(1, TOTAL_STORES + 1);
					final double totalAmount = ThreadLocalRandom.current().nextDouble(0, 1000) + .01;
					final long timestamp = LocalDateTime.now().toEpochSecond(ZoneOffset.UTC) * 1000;

					// Populate record
					GenericRecord order = new GenericRecord(this.type);
					order.put(0, storeId);
					order.put(1, orderId);
					order.put(2, totalAmount);
					order.put(3, timestamp);
					this.bulkInserter.insert(order);
				}
			}
			catch (Exception e)
			{
				System.out.println("Error inserting record: " + e);
			}
		}
	}

	/*
	 * Creates the schema and tutorial objects
	 */
	void setup() throws GPUdbException
	{
		// Create the tutorial schema, if necessary
		if (this.schemaName != null)
			if (!this.db.hasSchema(this.schemaName, null).getSchemaExists())
				this.db.createSchema(this.schemaName, null);

		// Create the order history table
		String ddlOrderHistory = "" +
		"   CREATE OR REPLACE TABLE " + this.tableNameHistory   +
		"    (                                                " +
		"        store_id INT NOT NULL,                       " +
		"        id INT NOT NULL,                             " +
		"        total_amount DOUBLE NOT NULL,                " +
		"        timestamp TYPE_TIMESTAMP NOT NULL,           " +
		"        PRIMARY KEY (id, store_id),                  " +
		"        SHARD KEY (store_id)                         " +
		"    );                                               ";
		this.db.executeSql(new ExecuteSqlRequest().setStatement(ddlOrderHistory));

		// Create the store sales materialized view
		String ddlStoreSales = "" +
		"    CREATE OR REPLACE MATERIALIZED VIEW " + this.viewNameSales    +
		"    REFRESH EVERY 10 MINUTES AS                                 " +
		"    SELECT  /* KI_HINT_GROUP_BY_PK */                           " +
		"        store_id,                                               " +
		"        DATE(timestamp) AS order_date,                          " +
		"        SUM(total_amount) AS total_sales                        " +
		"    FROM                                                        " +
		"        " + this.tableNameHistory + "                           " +
		"    GROUP BY                                                    " +
		"        store_id,                                               " +
		"        DATE(timestamp);                                        ";
		this.db.executeSql(new ExecuteSqlRequest().setStatement(ddlStoreSales));
	}

	/*
	 * Performs a bulk ingestion of data into Kinetica
	 * 
	 * Creates a BulkInserter and 4 record-generating threads to push a
	 * pre-configured amount of data into the database.  The target shard for
	 * each record will be calculated on the client side, and records will be
	 * pushed directly to the database ranks serving the respective shards in
	 * batches of preconfigured size.
	 * 
	 * Steps required for bulk ingestion:
	 * 
	 * 1. Acquire a handle to the database
	 * 2. Retrieve the type schema of the target table from the database
	 * 3. Create a BulkInserter for the table with the retrieved type schema
	 * 4. Insert records with the BulkInserter, flushing its queues when done
	 * 
	 * NOTE:  The BulkInserter has no inherent parallelism of its own, but is
	 *        thread-safe, and can be made more performant by having multiple
	 *        threads use it.  In this case, for example, using 4 threads allows
	 *        4 insert requests to execute concurrently.
	 */
	void ingest() throws GPUdbException
	{
		final int totalThreads = 4;
		final int totalBatches = 10;
		final int batchSize = 100_000;
		final int queueSize = 10_000;

		ExecutorService executorService = null;


		// Acquire a type for the order history table
		Type orderType = Type.fromTable(this.db, this.tableNameHistory);

		// Configure bulk inserter options to store up per-record insertion errors
		Map<String,String> options = GPUdbBase.options
		(
				InsertRecordsRequest.Options.RETURN_INDIVIDUAL_ERRORS, InsertRecordsRequest.Options.TRUE,
				InsertRecordsRequest.Options.ALLOW_PARTIAL_BATCH, InsertRecordsRequest.Options.TRUE
		);

		// Construct a bulk inserter to perform the distributed ingest
		try (BulkInserter<GenericRecord> bulkInserter =
				new BulkInserter<>(this.db, this.tableNameHistory, orderType, queueSize, options))
		{
			try
			{
				// Create a thread pool for generating & inserting data
				executorService = Executors.newFixedThreadPool(totalThreads);
	
				for (int batchIndex = 0; batchIndex < totalBatches; batchIndex++)
					executorService.execute
					(
							new BatchInsert(bulkInserter, orderType, batchIndex * batchSize, batchSize)
					);
			}
			finally
			{
				// Shut down thread pool
				if (executorService != null)
				{
					executorService.shutdown();
					try
					{
						if (!executorService.awaitTermination(30, TimeUnit.SECONDS))
							executorService.shutdownNow();
					}
					catch (@SuppressWarnings("unused") InterruptedException e)
					{
						executorService.shutdownNow();
					}
				}
			}

			// To ensure all records are inserted, flush the bulk inserter object
			bulkInserter.flush();

			// Process any errors
			for (BulkInserter.InsertException ie : bulkInserter.getErrors())
				System.err.println(String.format("Error sending records to <%s>:  %s", ie.getURL(), ie.getMessage()));
		}
	}

	/*
	 * Performs a keyed extraction of data from Kinetica
	 * 
	 * Creates a RecordRetriever to look up sales totals of each store in the
	 * database for the current day.  The sales totals are aggregated in the
	 * materialized view used as the lookup source.  The key for lookup is the
	 * store ID and the filter applied is for the current date.
	 * 
	 * Steps required for keyed lookup:
	 * 
	 * 1. Acquire a handle to the database
	 * 2. Retrieve the type schema of the source table from the database
	 * 3. Create a RecordRetriever for the table with the retrieved type schema
	 * 4. Lookup records by key with the RecordRetriever
	 */
	void lookup() throws GPUdbException
	{
		final String today = LocalDate.now().toString();
		final String todayFilter = "order_date = '" + today + "'";

		// Acquire a type for the store total table
		Type storeTotalType = Type.fromTable(this.db, this.viewNameSales);

		// Acquire a record retriever to perform the distributed key lookup
		RecordRetriever<GenericRecord> recordRetriever =
				new RecordRetriever<>(this.db, this.viewNameSales, storeTotalType);

		System.out.println("Summary for date: [" + today + "]");
		System.out.println("Store #  Total Sales");
		System.out.println("======= =============");

		for (int storeNum = 1; storeNum <= TOTAL_STORES; storeNum++)
		{
			// Set up store number to look up
			List<Object> storeKeyset = GPUdbBase.list((Object)storeNum);

			// Request filtered records
			GetRecordsResponse<GenericRecord> grResp = recordRetriever.getByKey(storeKeyset, todayFilter);

			// Output columns 1 and 3 from table--store ID and total sales
			for (GenericRecord storeTotal : grResp.getData())
				System.out.printf("%7d %13.2f%n", storeTotal.get(0), storeTotal.get(2));
		}
	}

	/*
	 * Refreshes the materialized view that is the source for distributed key
	 * lookup
	 */
	void refresh() throws GPUdbException
	{
		// Refresh the lookup source materialized view
		this.db.alterTable(this.viewNameSales, AlterTableRequest.Action.REFRESH, null, null);
	}
}
