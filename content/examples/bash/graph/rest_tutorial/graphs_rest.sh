#!/bin/bash
################################################################################
#
# Graphs REST Tutorial
#
# This script backs the Graph Solver REST tutorial on the doc site
#
# A Kinetica instance will handle calls to /create/graph and /solve/graph for a
# D.C.-based graph.
#
# NOTE:
#       Running the script requires that the 'dc_roads' dataset first be
#       ingested into the 'tutorial_graph' schema in the same Kinetica instance
#       that this script will be run against. This dataset can be downloaded
#       from the documentation site and imported via GAdmin or Workbench.
#
#       This script will put all of its own objects into the
#       'graph_rest' schema and recreate it upon execution.
#
# EXAMPLE:
#       ./graphs_rest.sh http://localhost:9191 some_user some_password
#
################################################################################

THIS_SCRIPT=$(basename ${BASH_SOURCE[0]})
HOST_URL="${1:-http://localhost:9191}"
USERNAME="${2}"
PASSWORD="${3}"
JSON_CMD="python -mjson.tool --sort-keys"

cd "$( dirname "${BASH_SOURCE[0]}" )"


# Extract the data_str attribute from the given JSON response object and output
# it JSONified
function extract_data_str
{
  RESP=$(${1})
  if echo ${RESP} | ${JSON_CMD} | grep status | grep OK > /dev/null
  then
    echo ${RESP} | ${JSON_CMD} | \
      grep data_str | grep -o {.*} | xargs -0 printf '%b\n' | ${JSON_CMD}
  else
    echo ${RESP} | ${JSON_CMD} | grep message | cut -f4 -d'"'
  fi
}

function extract_jrsp_str
{
  RESP=$(${1})
  if echo ${RESP} | ${JSON_CMD} | grep status | grep OK > /dev/null
  then
    echo ${RESP} | ${JSON_CMD} | \
      grep data_str | grep -o {.*} | xargs -0 printf '%b\n' | ${JSON_CMD} | \
      grep json_encoded_response | grep -o {.*} | xargs -0 printf '%b\n' | ${JSON_CMD}
  else
    echo ${RESP} | ${JSON_CMD} | grep message | cut -f4 -d'"'
  fi
}


function drop_schema
{
  curl -sS --header "Content-Type: application/json" \
    --user ${USERNAME}:${PASSWORD} \
    --data @drop_schema.json ${HOST_URL}/drop/schema
}

function create_schema
{
  curl -sS --header "Content-Type: application/json" \
    --user ${USERNAME}:${PASSWORD} \
    --data @create_schema.json ${HOST_URL}/create/schema
}

function create_graph
{
  curl -sS --header "Content-Type: application/json" \
    --user ${USERNAME}:${PASSWORD} \
    --data @create_graph.json ${HOST_URL}/create/graph
}

function solve_graph_sp
{
  curl -sS --header "Content-Type: application/json" \
    --user ${USERNAME}:${PASSWORD} \
    --data @solve_graph_shortest_path.json ${HOST_URL}/solve/graph
}

function verify_solve_sp
{
  curl -sS --header "Content-Type: application/json" \
    --user ${USERNAME}:${PASSWORD} \
    --data @get_records_shortest_path.json ${HOST_URL}/get/records/bycolumn
}

function solve_graph_mr
{
  curl -sS --header "Content-Type: application/json" \
    --user ${USERNAME}:${PASSWORD} \
    --data @solve_graph_multiple_routing.json ${HOST_URL}/solve/graph
}

function verify_solve_mr
{
  curl -sS --header "Content-Type: application/json" \
    --user ${USERNAME}:${PASSWORD} \
    --data @get_records_multiple_routing.json ${HOST_URL}/get/records/bycolumn
}


echo
echo "GRAPHS REST TUTORIAL OUTPUT"
echo "==========================="
echo

echo "(RE)CREATE SCHEMA"
echo "-----------------"
echo 

extract_data_str drop_schema
echo

extract_data_str create_schema
echo
echo

echo "CREATE GRAPH"
echo "------------"
echo 

extract_data_str create_graph
echo
echo

echo "SOLVE GRAPH"
echo "-----------"
echo

echo "SHORTEST PATH"
echo "*************"
echo

extract_data_str solve_graph_sp
echo
echo
extract_jrsp_str verify_solve_sp
echo
echo

echo "MULTIPLE ROUTING"
echo "****************"
echo

extract_data_str solve_graph_mr
echo
echo
extract_jrsp_str verify_solve_mr
echo
echo
