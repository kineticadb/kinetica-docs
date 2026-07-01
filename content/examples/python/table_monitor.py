""" This script serves as an example for using Kinetica table monitors using the
    Python Table Monitor API, which provides a more user-friendly table monitor
    management interface for abstracting some of the setup required when working
    with table monitors through the Python API directly.

    Topics Covered:

    * Creating, starting, and stopping a table monitor manager
    * Defining callbacks for handling monitored events
    * Usage of each of the three types of monitorable table data events
    * Displaying a per-table list of attached table monitors
    * Recovering from a database restart


    General Flow:
    
    * (Re)create the city weather "history" & "status" tables
      * The "history" table represents temperature records, over time, for a
        set of locations
      * The "status" table represents the current temperatures for the set of
        locations, each with its most recent temperature reading
    * Create a table monitor manager on each of the two tables:
      * One table monitor manager will watch for data inserted into the
        "history" table and update the "status" table with the
        location/temperature data pulled from those new "history" records.
      * The other table monitor manager will watch for updates and deletes on
        the "status" table and output the number of records updated or deleted
        for each update/delete made to the table, as well as output the contents
        of the "status" table itself.
    * Display a list of the "history" & "status" tables and their attached table
      monitors
    * (Optional) Restart the database to demonstrate the persistent nature of
      table monitors--must pass the appropriate flag to this example script in
      order to invoke this behavior
    * Insert city weather records into the "history" table, in batches; when
      these batch inserts occur:
      * The table monitor manager on the "history" table will update the
        "status" table with the new temperatures
    * Update city weather records directly in the "status" table; when these
      updates occur:
      * The table monitor manager on the "status" table will note the updates
        and output the number of records updated and the contents of the
        "status" table, for verification.
    * Delete city weather records directly from the "status" table; when these
      deletes occur:
      * The table monitor manager on the "status" table will note the deletes
        and output both the number of records deleted and the contents of the
        "status" table, to verify the city records are being deleted correctly.
    * Stop the two table monitor managers
    * Once again, display a list of the "history" & "status" tables and their
      attached table monitors; there should be no table monitors at this point.
"""

import gpudb
from gpudb import GPUdbRecordColumn as GRC
from gpudb import GPUdbColumnProperty as GCP
from gpudb import GPUdbTableMonitor as GTM

import argparse
import json
import random
import time
from datetime import datetime
from kinetica_tabulate import tabulate
from subprocess import call



SCHEMA = "tutorial_table_monitor"
HISTORY_TABLE = SCHEMA + ".table_monitor_history"
STATUS_TABLE = SCHEMA + ".table_monitor_status"


class StatusUpdater(GTM.Client):
    """ This class is an instance of a table monitor client that creates
        a table insert monitor on the "history" table and updates the "status"
        table with the location temperatures received in each "history" table
        insert batch.

        This class has the following features:

        * A handle to the "status" table, for updating with new temperatures
        * An on_insert_decoded callback defined, which extracts the decoded
          records inserted into the "history" table, and updates the "status"
          table accordingly
    """

    def __init__(self, kinetica):
        """ Initialize with a handle to the target database, facilitating the
            creation of a table monitor on the "history" table and the
            acquisition of a handle to the "status" table, for updating.  The
            monitor client will be set to abort processing if a record inserted
            into the "history" table cannot be decoded.
        """
        callbacks = [
            GTM.Callback(
                GTM.Callback.Type.INSERT_DECODED,
                self.on_insert_decoded,
                event_options = GTM.Callback.InsertDecodedOptions(
                    GTM.Callback.InsertDecodedOptions.DecodeFailureMode.ABORT
                )
            )
        ]

        # Invoke the base class constructor and pass in the list of callback
        # objects; using a short inactivity timeout to allow this example run
        # to terminate quickly
        super(StatusUpdater, self).__init__(
            kinetica,
            HISTORY_TABLE,
            callback_list = callbacks,
            options = GTM.Options(dict(inactivity_timeout=0.1))
        )

        self.status_table = gpudb.GPUdbTable(name = STATUS_TABLE, db = kinetica)


    def on_insert_decoded(self, history_record):
        """ Handles each insert event on the "history" table, updating the
            "status" table with the latest information from the "history" table

        Args:
            payload:  The record inserted into the "history" table
        """
        print("[TM/SU]  Received a new city temperature record")

        # City record with its new temperature and timestamp to create for
        # update in the "status" table
        status_update_record = [
            history_record["city"],
            history_record["state_province"],
            history_record["country"],
            history_record["temperature"],
            history_record["ts"]
        ]

        # Upsert new weather records into "status" table
        print("[TM/SU]  Updating city temperature status with received message...")
        self.status_table.insert_records(status_update_record, options = {"update_on_existing_pk": "true"})

        """ NOTE:  "Status" records will be updated via the insert_records()
                   call's "upsert" feature for simplicity's sake--the
                   corresponding call to update_records() would require the
                   construction of 3 parameter sets compared to the single one
                   required by insert_records().
                   
                   Also noteworthy is that the update_on_existing_pk parameter that
                   is specified to perform the "upsert" is only meaningful when the
                   target table has a primary key.  In this case, the primary key is
                   a composite key of the city & state_province columns.
        """

# end class StatusUpdater



class StatusReporter(GTM.Client):
    """ This class is an instance of a table monitor client that creates
        one table update monitor and one table delete monitor on the "status"
        table and outputs the counts of updates/deletes along with all "status"
        table records for verification.
    
        This class has the following features:
    
        * A handle to the "status" table, for retrieving and outputting all
          table data
        * An on_update callback defined, which outputs the number of "status"
          table records updated and the full set of "status" records
        * An on_delete callback defined, which outputs the number of "status"
          table records deleted and the full set of "status" records
    """


    def __init__(self, kinetica):
        """ Initialize with a handle to the target database, facilitating the
            creation of two table monitors on the "status" table and the
            acquisition of a handle to the "status" table, for verification.
        """
        callbacks = [
            GTM.Callback(
                GTM.Callback.Type.UPDATED,
                self.on_update
            ),
            GTM.Callback(
                GTM.Callback.Type.DELETED,
                self.on_delete
            )
        ]

        # Invoke the base class constructor and pass in the list of callback
        # objects; using a short inactivity timeout to allow this example run
        # to terminate quickly
        super(StatusReporter, self).__init__(
            kinetica,
            STATUS_TABLE,
            callback_list = callbacks,
            options = GTM.Options(dict(inactivity_timeout=0.1))
        )

        self.status_table = gpudb.GPUdbTable(name = STATUS_TABLE, db = kinetica)


    def on_update(self, count):
        """ Handles update events on the "status" table, outputting the count
            of records updated and all of the data in the "status" table

        Args:
            count:  The number of records updated in the "status" table
        """

        print("[TM/SR]  Updated <%s> city temperature statuses:" % (count))
        self.show_status()

    def on_delete(self, count):
        """ Handles delete events on the "status" table, outputting the count
            of records deleted and all of the data in the "status" table

        Args:
            count:  The number of records deleted from the "status" table
        """

        print("[TM/SR]  Deleted <%s> city temperature statuses:" % (count))
        self.show_status()


    def show_status(self):
        """ Output the contents of the "status" table, for verification purposes
        """

        print("")
        print("Status Table Output")
        print("===================")
        print("")

        self.status_table.get_records_by_column(
            column_names = ["city", "state_province", "country", "temperature", "last_update_ts"],
            options = {"sort_by":"city"},
            print_data = True
        )

        print("")


# end class StatusReporter



def define_data():

    # Base data set, from which cities will be randomly chosen, with a random
    #   new temperature picked for each, per batch loaded 
    return [
        ["Washington", "DC", "USA", -77.016389, 38.904722, 58.5, "UTC-5"],
        ["Paris", "TX", "USA", -95.547778, 33.6625, 64.6, "UTC-6"],
        ["Memphis", "TN", "USA", -89.971111, 35.1175, 63, "UTC-6"],
        ["Sydney", "Nova Scotia", "Canada", -60.19551, 46.13631, 44.5, "UTC-4"],
        ["La Paz", "Baja California Sur", "Mexico", -110.310833, 24.142222, 77, "UTC-7"],
        ["St. Petersburg", "FL", "USA", -82.64, 27.773056, 74.5, "UTC-5"],
        ["Oslo", "--", "Norway", 10.75, 59.95, 45.5, "UTC+1"],
        ["Paris", "--", "France", 2.3508, 48.8567, 56.5, "UTC+1"],
        ["Memphis", "--", "Egypt", 31.250833, 29.844722, 73, "UTC+2"],
        ["St. Petersburg", "--", "Russia", 30.3, 59.95, 43.5, "UTC+3"],
        ["Lagos", "Lagos", "Nigeria", 3.384082, 6.455027, 83, "UTC+1"],
        ["La Paz", "Pedro Domingo Murillo", "Bolivia", -68.15, -16.5, 44, "UTC-4"],
        ["Sao Paulo", "Sao Paulo", "Brazil", -46.633333, -23.55, 69.5, "UTC-3"],
        ["Santiago", "Santiago Province", "Chile", -70.666667, -33.45, 62, "UTC-4"],
        ["Buenos Aires", "--", "Argentina", -58.381667, -34.603333, 65, "UTC-3"],
        ["Manaus", "Amazonas", "Brazil", -60.016667, -3.1, 83.5, "UTC-4"],
        ["Sydney", "New South Wales", "Australia", 151.209444, -33.865, 63.5, "UTC+10"],
        ["Auckland", "--", "New Zealand", 174.74, -36.840556, 60.5, "UTC+12"],
        ["Jakarta", "--", "Indonesia", 106.816667, -6.2, 83, "UTC+7"],
        ["Hobart", "--", "Tasmania", 147.325, -42.880556, 56, "UTC+10"],
        ["Perth", "Western Australia", "Australia", 115.858889, -31.952222, 68, "UTC+8"]
    ]

# end define_data()


def insert_data(city_data):
    """ Load random city weather data into a "history" table, in batches.  Each
        batch will be loaded 2 seconds apart, to give the table insert monitor
        time to receive the message batch and the callback time to process it
    """

    print("\n\n=========================")
    print("TABLE INSERT MONITOR TEST")
    print("=========================\n\n")

    # Grab a handle to the "history" table for inserting new weather records
    history_table = gpudb.GPUdbTable(name = HISTORY_TABLE, db = kinetica)

    random.seed(0)

    # Insert 3 batches of city weather records
    # ========================================

    for iter in range(3):

        city_updates = []

        # Grab a random set of cities
        cities = random.sample(city_data, k = random.randint(1, len(city_data) // 2))

        # Create a list of weather records to insert
        for city in cities:

            # Pick a random temperature for each city at the current time
            city_update = list(city)
            city_update[5] = city_update[5] + random.randrange(-10, 10)
            city_update.append(datetime.now())

            city_updates.append(city_update)

        # Insert the records into the table and allow time for the table insert
        #   monitor to process them before inserting the next batch
        print("")
        print("[Main/Inserter]  Inserting <%s> new city temperatures..." % len(city_updates))
        history_table.insert_records(city_updates)

        time.sleep(2)

# end insert_data()


def update_data(city_data):
    """ Update random city weather data in the "status" table, in batches.  Each
        batch will be updated 2 seconds apart, to give the table update monitor
        time to receive the update event and the callback time to process it
    """

    print("\n\n=========================")
    print("TABLE UPDATE MONITOR TEST")
    print("=========================\n\n")

    # Grab a handle to the "status" table for updating exiting weather records
    status_table = gpudb.GPUdbTable(name = STATUS_TABLE, db = kinetica)

    random.seed(0)

    # Update 3 batches of city weather records
    # ========================================

    for iter in range(3):

        city_keys = []
        city_updates = []

        # Grab a random set of cities
        cities = random.sample(city_data, k = random.randint(1, len(city_data) // 2))
    
        # Create a list of weather records to update
        for city in cities:
            
            # Pick a random temperature for each city at the current time
            city_keys.append("city = '%s' AND state_province = '%s'" % (city[0], city[1]))
            city_updates.append({
                "temperature": city[5] + random.randrange(-10, 10),
                "last_update_ts": datetime.now()
            })
    
        # Update the records in the table and allow time for the table update
        #   monitor to process them before updating the next batch
        print("")
        print("[Main/Updater]  Updating <%s> new city temperatures..." % len(city_keys))
        response = status_table.update_records(city_keys, city_updates)

        time.sleep(2)

# end update_data()


def delete_data(city_data):
    """ Delete random city weather data in a "status" table, in batches.  Each
        batch will be deleted 2 seconds apart, to give the table delete monitor time
        to receive the delete event and the callback time to process it
    """

    print("\n\n=========================")
    print("TABLE DELETE MONITOR TEST")
    print("=========================\n\n")

    # Grab a handle to the "status" table for deleting existing weather records
    status_table = gpudb.GPUdbTable(name = STATUS_TABLE, db = kinetica)

    random.seed(0)

    # Delete 3 batches of city weather records
    # ========================================

    for iter in range(3):

        city_keys = []

        # Grab a random set of cities
        cities = random.sample(city_data, k = random.randint(1, len(city_data) // 2))
    
        # Create a list of weather records to delete
        for city in cities:
            
            city_keys.append("city = '%s' AND state_province = '%s'" % (city[0], city[1]))

        # Delete the records from the table and allow time for the table delete
        #   monitor to process them before deleting the next batch
        print("")
        print("[Main/Deleter]  Attempting to delete records for <%s> randomly selected cities..." % len(city_keys))
        status_table.delete_records(city_keys)

        time.sleep(2)

# end delete_data()


def create_tables():
    """ Create the city weather "history" & "status" tables used in this example
    """

    # Create schema for table monitor tutorial tables
    kinetica.create_schema(SCHEMA)

    # Create a column list for the "history" table
    columns = [
        [ "city", GRC._ColumnType.STRING, GCP.CHAR16 ],
        [ "state_province", GRC._ColumnType.STRING, GCP.CHAR32 ],
        [ "country", GRC._ColumnType.STRING, GCP.CHAR16 ],
        [ "x", GRC._ColumnType.DOUBLE ],
        [ "y", GRC._ColumnType.DOUBLE ],
        [ "temperature", GRC._ColumnType.DOUBLE ],
        [ "time_zone", GRC._ColumnType.STRING, GCP.CHAR8 ],
        [ "ts", GRC._ColumnType.STRING, GCP.DATETIME ]
    ]

    # Create the "history" table using the column list
    gpudb.GPUdbTable(columns, name = HISTORY_TABLE, db = kinetica)


    # Create a column list for the "status" table
    columns = [
        [ "city", GRC._ColumnType.STRING, GCP.CHAR16, GCP.PRIMARY_KEY ],
        [ "state_province", GRC._ColumnType.STRING, GCP.CHAR32, GCP.PRIMARY_KEY ],
        [ "country", GRC._ColumnType.STRING, GCP.CHAR16 ],
        [ "temperature", GRC._ColumnType.DOUBLE ],
        [ "last_update_ts", GRC._ColumnType.STRING, GCP.DATETIME ]
    ]

    # Create the "status" table using the column list
    gpudb.GPUdbTable(columns, name = STATUS_TABLE, db = kinetica)

# end create_tables()


def clear_tables():
    """ Drop the city weather "history" & "status" tables used in this example
    """

    # Drop all the tables by dropping the containing schema
    kinetica.drop_schema(SCHEMA, {"cascade": "true"})

# end clear_tables()


def show_monitors():
    """ Show the city weather "history" & "status" tables used in this example,
        along with their attached table monitors
    """

    print("\n\n====================")
    print("TABLE MONITOR STATUS")
    print("====================\n\n")

    table_monitor_headers = ["Table Name", "Monitor Type", "Topic ID"]
    table_monitor_records = []

    # Show table monitors on all the tables
    for table_name in [
        HISTORY_TABLE,
        STATUS_TABLE
    ]:
        table_info = kinetica.show_table(table_name)['additional_info'][0]
        
        if 'table_monitor' in table_info:

            table_monitor_info = json.loads(table_info['table_monitor'])

            for monitor_type in ['insert', 'update', 'delete']:
                if monitor_type in table_monitor_info:
                    table_monitor_records.append([table_name, monitor_type, table_monitor_info[monitor_type]])
    
    print( tabulate( table_monitor_records, headers = table_monitor_headers, tablefmt = 'grid' ) ) 
    print("")

# end show_monitors()


def restart_db():
    """ Restart the database, to test table monitor persistence
    """

    print("[Main/Restarter]  Restarting the database...")
    call("service gpudb restart", shell=True)

# end restart_db()



if __name__ == '__main__':

    # Set up args
    parser = argparse.ArgumentParser(description='Run table monitor tutorial.')
    parser.add_argument('command', nargs="?", help='command to execute (currently only "clear" to remove the example tables')
    parser.add_argument('--url', default='http://127.0.0.1:9191', help='Kinetica URL to run example against')
    parser.add_argument('--username', default='', help='Username of user to run example with')
    parser.add_argument('--password', default='', help='Password of user')
    parser.add_argument('--restart', action='store_true', help='Whether or not to restart the database during the test')

    args = parser.parse_args()

    # Establish connection with an instance of Kinetica, given a URL and credentials
    kinetica = gpudb.GPUdb(host = [args.url], username = args.username, password = args.password)


    # If command line arg is clear, just clear tables and exit
    if (args.command == "clear"):
        clear_tables()
        quit()

    clear_tables()

    create_tables()

    status_updater = StatusUpdater(kinetica)
    status_reporter = StatusReporter(kinetica)

    status_updater.start_monitor()
    status_reporter.start_monitor()

    show_monitors()

    if args.restart:
        restart_db()
        show_monitors()

    city_data = define_data()
    
    insert_data(city_data)
    update_data(city_data)
    delete_data(city_data)

    # Wait for monitor queues to empty
    time.sleep(2)

    print("[Main]  Stopping monitors...")
    status_updater.stop_monitor()
    status_reporter.stop_monitor()

    show_monitors()

    print("[Main]  Example complete.")
