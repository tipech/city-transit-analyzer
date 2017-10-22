import requests, sys, os
import xml.etree.ElementTree as ET
from itertools import groupby
from functools import reduce
from pprint import pprint



def main():
	"""Execute the main actions of the network builder program

	Argus:
		static - build the static network of stops and connections between them
		distances - calculate the straight-line and road distances between stops
		
	"""

	# With the "static" argument, build the static network
	if len(sys.argv) > 2 and (sys.argv[1] == "static" or sys.argv[1] == "-s" ):

		agency = sys.argv[2]
		build_static_network(agency)

	# With the "distances" argument, calculate the distances between stops
	elif len(sys.argv) > 2 and (sys.argv[1] == "distances" or sys.argv[1] == "-d" ):

		agency = sys.argv[2]
		calculate_distances(agency)

	# With wrong arguments, print usage help message
	else:
		print("Usage: builder <static|distances> <agency>")

		


# ===============================================
# =			Static Network Construction 		=
# ===============================================

def build_static_network(agency):
	"""Construct the atops & connection network of the transport system from all the routes"""

	# Get the list of routes and stops for this agency
	routes_list = get_routes_list(agency)
	print("Found " + str(len(routes_list)) + " routes")

	# Hold all the stops and their connections
	stops_list = []
	connections_list = []

	# Iterate through routes
	for index, route in enumerate(routes_list):
		route_xml = ET.fromstring( call_API(agency, "routeConfig", route) )[0]
		stops_list = stops_list + get_route_stops(route_xml)
		connections_list = connections_list + get_route_connections(route_xml)

		print("Extracted data from " + str( index + 1 ) + "/" + str(len(routes_list)) + " routes", end="\r")

	# After all routes, consolidate data
	stops_list = consolidate_stops(stops_list)
	connections_list = consolidate_connections(connections_list)

	print("\nFound " + str(len(stops_list)) + " stops and " + str(len(connections_list)) + " connections")

	# Write results to files
	write_stops_file(agency, stops_list)
	write_connections_file(agency, connections_list)


def get_routes_list(agency):
	"""Use the API to retrieve a list of the agency's routes."""

	routes_tree = ET.fromstring(call_API(agency, "routeList"))
	# we are only interested in the route tags
	routes_map = map((lambda x: x.attrib["tag"]), routes_tree)
	# convert to list
	return list(routes_map)
	# return list(routes_map)[100:110] # DEBUG only the first 10 routes


def get_route_stops(route_xml):
	"""Extract the list of stops for this route."""

	# keep only stop xml elements
	stops_map = filter((lambda x: x.tag=="stop" and not '_' in x.attrib['tag']), route_xml)

	# lambda function to turn xml attributes into dictionary keys
	stop_dict_func = lambda x: {'tag': x.attrib['tag'], 'title': x.attrib['title'], 'lat': x.attrib['lat'], 'lon': x.attrib['lon']}
	stops_map = map(stop_dict_func, stops_map)

	return list(stops_map)


def get_route_connections(route_xml):
	"""Extract the list of connections between stops for this route."""

	connections_list = []
	
	# look at stop xml elements inside direction elements
	directions_map = filter((lambda x: x.tag=="direction"), route_xml)
	for direction in directions_map:
		for i in range(len(direction) - 1):

			# get the stop tags, discard special endings like "_ar"
			from_stop = (direction[i].attrib['tag']).split('_',1)[0]
			to_stop = (direction[i+1].attrib['tag']).split('_',1)[0]

			# add the new connection between stops
			connection_dict = {'from': from_stop, 'to': to_stop, 'routes': [route_xml.attrib['tag']]}
			connections_list.append(connection_dict)

	return connections_list
		

def consolidate_stops(stops_list):
	"""Remove duplicates from the list of stops."""

	# Turn stop list into a dictionary and back to remove duplicates
	stops_list = list({stop['tag']: stop for stop in stops_list}.values())
	# Sort list (optional)
	stops_list.sort(key=(lambda x: int(x['tag'])))

	return stops_list


def consolidate_connections(connections_list):
	"""Merge duplicates from the list of connections."""

	# Sort list (optional)
	connections_list.sort(key=(lambda x: (int(x['from']), int(x['to'])) ))

	# Split list to groups that have the same from and to stops
	same_connection_groups = groupby(connections_list, key=lambda x: x['from'] + "_" + x['to'])

	# Merge these groups together by concating the routes for each connection using "|"
	connections_list = [reduce(merge_connections, group) for _,group in same_connection_groups]

	return connections_list


def merge_connections(connection_1, connection_2):
	"""Merge two connections by comparing routes."""

	routes = list(set(connection_1['routes'] + connection_2['routes']))


	return {'from': connection_1['from'], 'to': connection_1['to'], 'routes': routes}


# ===============================================
# =				Distance Calculation			=
# ===============================================

def calculate_distances(agency):
	"""Calculate the straight-line and road distances between the connected stops of the network."""

	# read the previously-built network data
	stops_list = read_stops_file(agency)
	connections_list = read_connections_file(agency)

	# pprint(connections_list)


	# @Abbas distance calculation here
	# you can use write_connections_distances_file() at the end which expects connection_list to be 
	# [
	#   {"from": ...  , "to": ...  , "routes": ...|...|...  , "straight-distance": ...  , "road-distance": ...},
	#   ...,  ...,  ...  ]



# ===============================================
# =					File IO 					=
# ===============================================\

def create_agency_folder(agency):
	"""Creates a folder for this agency if one doesn't already exist."""

	if not os.path.isdir(agency):
		os.makedirs(agency)


def read_stops_file(agency):
	"""Opens stops file and reads contents into a list."""

	# read the file and split the rows into a list
	try:
		stops_file = open(agency + "/stops.csv","r+")
	except FileNotFoundError:
		print("Error: Stops file missing for this agency!")
		sys.exit()

	stops_list_csv = stops_file.read().split("\n")
	stops_file.close()

	# split every row into a stop entry by applying read_stop_entry
	stops_map = map(read_stop_entry, stops_list_csv)
	# filter out first (header) and last (empty) lines
	stops_list = list(filter(lambda x: x != None, stops_map))

	return stops_list


def read_connections_file(agency):
	"""Opens connections file and reads contents into a list."""

	# read the file and split the rows into a list
	try:
		connections_file = open(agency + "/connections.csv","r+")
	except FileNotFoundError:
		print("Error: Connections file missing for this agency!")
		sys.exit()

	connections_list_csv = connections_file.read().split("\n")
	connections_file.close()

	# split every row into a connection entry by applying read_connection_entry
	connections_map = map(read_connection_entry, connections_list_csv)
	# filter out first (header) and last (empty) lines
	connections_list = list(filter(lambda x: x != None, connections_map))

	return connections_list
	
	
def read_stop_entry(stop_text):
	"""Parses a stop entry from comma-separated to dictionary form."""
	
	# split comma-separated values
	stop_list = stop_text.split(",")

	# handle invalid lines
	if len(stop_list) > 1 and stop_list[0] != "tag":
		return {"tag": stop_list[0], "title": stop_list[1], "lat": stop_list[2], "lon": stop_list[3]}
	else:
		return None
	
	
def read_connection_entry(connection_text):
	"""Parses a connection entry from comma-separated to dictionary form."""
	
	# split comma-separated values
	connection_list = connection_text.split(",")

	# handle invalid lines
	if len(connection_list) > 1 and connection_list[0] != "from":
		return {"from": connection_list[0], "to": connection_list[1], "routes": connection_list[2].split("|")}
	else:
		return None


def write_stops_file(agency, stops_list):
	"""Creates a new or empties the existing stops file and fills it with the list of stops."""

	# (Re)create empty stops file
	create_agency_folder(agency)
	stops_file = open(agency + "/stops.csv", "w+")

	# Write stops file
	stops_file.write("tag,title,lat,lon\n")
	for stop in stops_list:
		stops_file.write(stop['tag'] + "," + stop['title'] + "," + stop['lat'] + "," + stop['lon'] + "\n" )

	# Close the file
	stops_file.close()


def write_connections_file(agency, connections_list):
	"""Creates a new or empties the existing connections file and fills it with the list of connections."""

	# (Re)create empty connections file
	create_agency_folder(agency)
	connections_file = open(agency + "/connections.csv", "w+")

	# Write connections file
	connections_file.write("from,to,routes\n")
	for connection in connections_list:
		connections_file.write(connection['from'] + "," + connection['to'] + "," + '|'.join(connection['routes']) + "\n" )

	# Close the file
	connections_file.close()


def write_connections_distances_file(agency, connections_list):
	"""Creates a new or empties the existing connections file and fills it with the list of connections with distances."""

	# (Re)create empty connections file
	connections_file = open(agency + "/connections.csv", "w+")

	# Write connections file
	connections_file.write("from,to,routes\n")
	for connection in connections_list:
		connections_file.write(
			  connection['from'] + ","
			+ connection['to'] + ","
			+ '|'.join(connection['routes'])
			+ connection['straight-distance'] + ","
			+ connection['road-distance']
			+ "\n" )

	# Close the file
	connections_file.close()



# ===============================================
# =					API calls 					=
# ===============================================

def call_API(agency, command, route = "", stop = ""):
	"""Call the agency's API for a specific command.

	Args:
		agency: The agency we are interested in
		command: The command we want to give.
		route: The route used in the command (optional).
		stop: The stop used in the command (optional).

	Returns:
		The response body.

	"""

	# TODO change these to arguments so that we can use other agencies
	agency = "ttc"
	agency_API_base = "http://webservices.nextbus.com/service/publicXMLFeed?command="

	request_url = agency_API_base + command + '&a=' + agency 

	if command == 'routeList':
		options_url = ''
	elif command == 'routeConfig' and route != '':
		options_url = '&r=' + route


	return requests.get(request_url + options_url).text



# ===============================================
if __name__ == "__main__":
    main()