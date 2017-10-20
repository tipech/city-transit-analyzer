import requests, sys
import xml.etree.ElementTree as ET
from itertools import groupby
from functools import reduce
from pprint import pprint



def main():
	"""Execute the main actions of the program"""

	# With the "static" argument, build the static network
	if(len(sys.argv) > 1 and sys.argv[1] == "static"):

		build_static_network()
		

	close_files()


# ===============================================
# =			Static Network Construction 		=
# ===============================================

def build_static_network():
	"""Construct the atops & connection network of the transport system from all the routes"""

	# Get the list of routes and stops for this agency
	routes_list = get_routes_list()
	print("Found " + str(len(routes_list)) + " routes")

	# Hold all the stops and their connections
	stops_list = []
	connections_list = []

	# Iterate through routes
	for index, route in enumerate(routes_list):
		route_xml = ET.fromstring( call_API("routeConfig", route) )[0]
		stops_list = stops_list + get_route_stops(route_xml)
		connections_list = connections_list + get_route_connections(route_xml)

		print("Extracted data from " + str( index + 1 ) + "/" + str(len(routes_list)) + " routes", end="\r")

	# After all routes, consolidate data
	stops_list = consolidate_stops(stops_list)
	connections_list = consolidate_connections(connections_list)

	print("\nFound " + str(len(stops_list)) + " stops and " + str(len(connections_list)) + " connections")

	# DEBUG
	# pprint(connections_list)

	# Write results to files
	write_stops_file(stops_list)
	write_connections_file(connections_list)


def get_routes_list():
	"""Use the API to retrieve a list of the agency's routes."""

	routes_tree = ET.fromstring(call_API("routeList"))
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
# =					File IO 					=
# ===============================================

def open_files():
	"""Opens network files for reading."""

	global stops_file
	global connections_file
	stops_file = open("stops.csv","r+")
	connections_file = open("connections.csv","r+")
	

def write_stops_file(stops_list):
	"""Creates a new or empties the existing stops file and fills it with the list of stops."""

	# Empty or otherwise create the stops file
	global stops_file
	try:
		stops_file.truncate()
	except (IOError, NameError):
		stops_file = open("stops.csv","w+")

	# Write stops file
	stops_file.write("tag,title,lat,lon\n")
	for stop in stops_list:
		stops_file.write(stop['tag'] + "," + stop['title'] + "," + stop['lat'] + "," + stop['lon'] + "\n" )


def write_connections_file(connections_list):
	"""Creates a new or empties the existing connections file and fills it with the list of connections."""

	# Empty or otherwise create the connections file
	global connections_file
	try:
		connections_file.truncate()
	except (IOError, NameError):
		connections_file = open("connections.csv","w+")

	# Write connections file
	connections_file.write("from,to,routes\n")
	for connection in connections_list:
		connections_file.write(connection['from'] + "," + connection['to'] + "," + '|'.join(connection['routes']) + "\n" )


def close_files():
	"""Closes network files."""

	global stops_file
	global connections_file
	stops_file.close()
	connections_file.close()


# ===============================================
# =					API calls 					=
# ===============================================

def call_API(command, route = "", stop = ""):
	"""Call the agency's API for a specific command.

	Args:
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