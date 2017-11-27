import requests, sys, os, math, googlemaps, json
import xml.etree.ElementTree as ET
import networkx as nx
from itertools import groupby
from functools import reduce
from pprint import pprint

from common import *


# Constants
walking_distance = 0.05 # 50m



def main():
	"""Execute the main actions of the network builder program

	Args:
		static - build the static network of stops and connections between them
		distances - calculate the straight-line and road distances between stops

		city - the city for which we want to get results
		
	"""

	# With the "static" argument, build the static network
	if len(sys.argv) > 2 and (sys.argv[1] == "static" or sys.argv[1] == "-s" ):

		build_static_network(sys.argv[2])
		calculate_distances(sys.argv[2])

	# With the "distances" argument, calculate the distances between stops
	elif len(sys.argv) > 2 and (sys.argv[1] == "distances" or sys.argv[1] == "-d" ):
		# pass
		calculate_road_distances(sys.argv[2])
		

	# With the "distances" argument, calculate the distances between stops
	elif len(sys.argv) > 2 and (sys.argv[1] == "times" or sys.argv[1] == "-t" ):
		
		calculate_times(sys.argv[2])
		
	# With the "help" argument, calculate the distances between stops
	elif len(sys.argv) > 1 and sys.argv[1] == "help":

		print("Supported cities:")
		for city in cities:
			print("\t- " + city)

	# With wrong arguments, print usage help message
	else:
		print("Usage: builder <static|distances> <city>")


# ===============================================
# =			Static Network Construction 		=
# ===============================================

def build_static_network(city):
	"""Construct the atops & connection network of the transport system from all the routes"""

	# Get the list of routes and stops for this city
	routes_list = get_routes_list(city)
	print("Found " + str(len(routes_list)) + " routes")

	# Hold all the stops and their connections
	stops_list = []
	connections_list = []

	# Iterate through routes
	for index, route in enumerate(routes_list):
		route_xml = ET.fromstring( call_transit_API(cities[city]['apis'][route['api']], "route_data", route["tag"]) )[0]
		stops_list = stops_list + get_route_stops(route_xml)
		connections_list = connections_list + get_route_connections(route_xml)

		print("Extracted data from " + str( index + 1 ) + "/" + str(len(routes_list)) + " routes", end="\r")

	# After all routes, clean and consolidate data
	stops_list = consolidate_stops(stops_list)
	stops_list = remove_isolated_stops(stops_list, connections_list)
	stops, connections_list = merge_nearby_stops(stops_list, connections_list, cities[city]['radius'])
	connections_list = consolidate_connections(connections_list)

	print("Found " + str(len(stops_list)) + " stops and " + str(len(connections_list)) + " connections")

	# Write results to files
	write_stops_file(cities[city]['tag'], stops_list)
	write_connections_file(cities[city]['tag'], connections_list)


def get_routes_list(city):
	"""Use the API to retrieve a list of the city's routes."""

	routes_list = []

	for api in cities[city]['apis']:

		routes_tree = ET.fromstring(call_transit_API(cities[city]['apis'][api], "route_list"))
		# we are only interested in the route tags
		routes_map = map((lambda x: {"tag": x.attrib["tag"], "api": api}), routes_tree)
		# convert to list
		routes_list = routes_list + list(routes_map)

	return routes_list[:10] # DEBUG only the first 10 routes


def get_route_stops(route_xml):
	"""Extract the list of stops for this route."""

	# keep only stop xml elements
	stops_map = filter((lambda x: x.tag=="stop"), route_xml)

	# lambda function to turn xml attributes into dictionary keys
	stop_dict_func = lambda x: {
		'tag': x.attrib['tag'].split("_")[0],
		'title': x.attrib['title'],
		'lat': x.attrib['lat'],
		'lon': x.attrib['lon'],
		'merged': [x.attrib['tag'].split("_")[0]]}
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
			connection_dict = {
				'from': from_stop,
				'to': to_stop,
				'routes': [route_xml.attrib['tag']],
				'length': 0,
				'road-length': 0}
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

	# Remove self loops
	for i in reversed(range(0,len(connections_list))):
		if(connections_list[i]['from'] == connections_list[i]['to']):
			del(connections_list[i])

	# Split list to groups that have the same from and to stops
	same_connection_groups = groupby(connections_list, key=lambda x: x['from'] + "_" + x['to'])

	# Merge these groups together by concating the routes for each connection using "|"
	connections_list = [reduce(merge_connections, group) for _,group in same_connection_groups]

	return connections_list


def merge_connections(connection_1, connection_2):
	"""Merge two connections by comparing routes."""

	# Turn into set to discard duplicates 
	routes_set = set(connection_1['routes'] + connection_2['routes'])

	return {
		'from': connection_1['from'],
		'to': connection_1['to'],
		'routes': list(routes_set),
		'length': connection_1['length'],
		'road-length': connection_1['road-length']}


def remove_isolated_stops(stops_list, connections_list):
	"""Use NetworkX to remove isolated or obsolete stops."""

	# Build the graph object, add stops and connections
	G = nx.Graph()
	G.add_nodes_from(convert_stops_to_tuples(stops_list))
	G.add_edges_from(convert_connections_to_tuples(connections_list))

	# remove isolated nodes that are in no connections
	isolated_stops = list(nx.isolates(G))

	return list(filter(lambda stop: stop['tag'] not in isolated_stops, stops_list))


def merge_nearby_stops(stops_list, connections_list, radius):
	"""Merge stops that are within walking distance."""

	# Turn list of connections into dictionary for direct access
	connections_dict = {connection['from'] + "_" + connection['to'] : connection for connection in connections_list}

	# Counters
	stops_merged = 0
	initial_length = len(stops_list)

	# Iterate over every stop with every other in a triangle (in reverse because we are changing it)
	for i in reversed(range(0, initial_length)):
		new_length = len(stops_list)
		for j in reversed(range(i+1, new_length)):

			# Calculate distance between any two stops
			stop_1 = stops_list[i]
			stop_2 = stops_list[j]

			distance = calculate_straight_distance(stop_1['lat'], stop_1['lon'], stop_2['lat'], stop_2['lon'], radius)

			# If the two stops are within 50m
			if distance < walking_distance:

				# If there is no actual transit route connecting the two, merge 2nd to 1st
				if (stops_list[i]['tag'] + "_" + stops_list[j]['tag'] not in connections_dict and
					stops_list[j]['tag'] + "_" + stops_list[i]['tag'] not in connections_dict):

					# Set 1st stop position to average of two
					stops_list[i]['lat'] = (float(stops_list[i]['lat']) + float(stops_list[j]['lat'])) /2
					stops_list[i]['lon'] = (float(stops_list[i]['lon']) + float(stops_list[j]['lon'])) /2

					# Add stop to merged stops
					stops_list[i]['merged'] = list(set(stops_list[i]['merged'] + stops_list[j]['merged']))

					# Change connections to tag of 1st stop
					for connection in connections_list:
						if connection['from'] == stops_list[j]['tag']:
							connection['from'] = stops_list[i]['tag']

					for connection in connections_list:
						if connection['to'] == stops_list[j]['tag']:
							connection['to'] = stops_list[i]['tag']

					# Delete the second stop
					del stops_list[j]

					stops_merged = stops_merged + 1

		print("Calculated distances for " + str( initial_length - i + 1 ) + "/" + str(initial_length) + " stops", end="\r")

	print("\nComparison done! Merged: " + str(stops_merged) + " pairs of nearby stops.")
	
	return stops_list, connections_list


# ===============================================
# =				Distance Calculation			=
# ===============================================

def calculate_distances(city):
	"""Calculate the straight-line and road distances between the connected stops of the network."""

	# read the previously-built network data
	stops_list = read_stops_file(cities[city]['tag'])
	connections_list = read_connections_file(cities[city]['tag'])
	
	# Get Earth radius at city
	radius = cities[city]['radius']

	# Turn list of stops into dictionary for direct access
	stops_dict = {stop['tag']: stop for stop in stops_list}

	# Calculate the length of every connection
	for connection in connections_list:
		stop_1 = stops_dict[connection['from']]
		stop_2 = stops_dict[connection['to']]
		connection['length'] = calculate_straight_distance(stop_1['lat'], stop_1['lon'], stop_2['lat'], stop_2['lon'], radius)

	# pprint(connections_list)
	write_connections_file(cities[city]['tag'], connections_list)


def calculate_road_distances(city):
	#
	
	# read the previously-built network data
	connections_list = read_connections_file(cities[city]['tag'])
	stops_list = read_stops_file(cities[city]['tag'])

	# Turn list of stops into dictionary for direct access
	stops_dict = {stop['tag']: stop for stop in stops_list}


	sources_list = [stops_dict[connection['from']] for connection in connections_list]
	destinations_list = [stops_dict[connection['to']] for connection in connections_list]


	distances_list = call_distance_API(sources_list, destinations_list)

	index = 0
	for connection in connections_list:


		connection['road-length'] = distances_list[index]

		# Suspiciously big difference in distances, recalculate
		if(connection['road-length']/connection['length'] > 2 ):
			connection['road-length'] = call_distance_API([stops_dict[connection['from']]],[stops_dict[connection['to']]])[0]

		if(connection['length'] > distances_list[index]):
			connection['road-length'] = connection['length']

		index = index + 1


	pprint(connections_list)


	write_connections_file(cities[city]['tag'], connections_list)



# ===============================================
# =			Network Times Calculation			=
# ===============================================


def calculate_times(city):
	pass





# ===============================================
# =					API calls 					=
# ===============================================

def call_transit_API(api, command, route = "", stop = ""):
	"""Call the agency's API for a specific command.

	Args:
		api: The API of the agency we are interested in
		command: The command we want to give.
		route: The route used in the command (optional).
		stop: The stop used in the command (optional).

	Returns:
		The response body.

	"""

	if command == 'route_list':
		options_url = ''
	elif command == 'route_data' and route != '':
		options_url = api['route'] + route

	return requests.get(api['base'] + api['commands'][command] +  options_url).text


def call_distance_API(sources_list, destinations_list):
	"""Call the OSRM road distance API to get the distances between a list of points.

	Args:
		sources_list: The list of source points.
		destinations_list: The list of destination points.

	Returns:
		The response body.

	"""


	source_points_list = [stop['lon'] + "," + stop['lat'] for stop in sources_list]
	destination_points_list = [stop['lon'] + "," + stop['lat'] for stop in destinations_list]

	points_list = [None]*(len(source_points_list)+len(destination_points_list))
	points_list[::2] = source_points_list
	points_list[1::2] = destination_points_list

	api_base = "http://router.project-osrm.org/route/v1/driving/"
	api_options = "?overview=false"

	distances = []

	# Do a request per 100 stops
	for x in range(0, len(points_list), 100):
		
		response_text = requests.get(api_base + ';'.join(points_list[x:x+100]) + api_options).text	
		response_json = json.loads(response_text)

		results = response_json['routes'][0]['legs'][::2]
		distances = distances + [connection['distance']*0.001 for connection in results]

	return distances







# ===============================================
if __name__ == "__main__":
    main()
