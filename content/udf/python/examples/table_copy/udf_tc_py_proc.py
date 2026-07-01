################################################################################
#                                                                              #
# Kinetica UDF Table Copy Example                                              #
# ---------------------------------------------------------------------------- #
# This UDF first compares the given CSV file's rank and tom number values to   #
# the ranks and toms processing the UDF. If the values in the CSV file match   #
# the ranks and toms found in the request info map, the associated data with   #
# the matching rank/tom is copied from the input table to the output table.    #
#                                                                              #
################################################################################

from kinetica_proc import ProcData
import csv


# Instantiate a handle to the ProcData() class
proc_data = ProcData()

# Retrieve rank and TOM from this UDF's request info map; together
# these two numbers uniquely identify this process of the UDF
proc_rank_num = proc_data.request_info["rank_number"]
proc_tom_num = proc_data.request_info["tom_number"]

# Read the CSV file (skipping the header) and extract the file's
# rank/TOM pairs to determine whether any refer to this process
rank_tom_info = csv.reader(open("rank_tom.csv"))
next(rank_tom_info)

for row in rank_tom_info:
    rank_num = row[0]
    tom_num = row[1]

    # Check if this proc instance's rank/TOM match the file values
    if (proc_rank_num == rank_num and proc_tom_num == tom_num):

        # Loop through input and output tables (assume the same number)
        for in_table, out_table in zip(
                proc_data.input_data, proc_data.output_data):
            out_table.size = in_table.size

            print(
                f'Copying <{in_table.size}> records '
                f'on rank/TOM <{proc_rank_num}/{proc_tom_num}> '
                f'from <{in_table.name}> to <{out_table.name}>'
            )

            # Loop through columns in the input and output tables (assume the
            # same number and types)
            for in_column, out_column in zip(in_table, out_table):
                out_column.extend(in_column)

        break;

# If no matches exist, don't copy any values
else:
    print(f'This rank/TOM <{proc_rank_num}/{proc_tom_num}> not present in rank_tom.csv')
 
# Inform Kinetica that the proc has finished successfully
proc_data.complete()
