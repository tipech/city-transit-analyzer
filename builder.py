import requests, sys, os, math, googlemaps
import xml.etree.ElementTree as ET
import networkx as nx
from itertools import groupby
from functools import reduce
from pprint import pprint

from common import *


# Constants
walking_distance = 0.05 # 50m
cities = {
	'toronto':{
		'tag':"ttc",
		'area': 630,
		'radius': 6368.262,
		'apis':{
			'ttc': {
				'base':"http://webservices.nextbus.com/service/publicXMLFeed?a=ttc&command=",
				'route':"&r=",
				'commands':{
					'route_list':"routeList",
					'route_data':"routeConfig"
				}
			}
		}
	},
	'la':{
		'tag':"lametro",
		'area': 1214,
		'radius': 6371.57,
		'apis':{
			'lametro': {
				'base':"http://webservices.nextbus.com/service/publicXMLFeed?a=lametro&command=",
				'route':"&r=",
				'commands':{
					'route_list':"routeList",
					'route_data':"routeConfig"
				}
			}
		}
	},
	'sf':{
		'tag':"sf-muni2",
		'area': 121,
		'radius': 6370.158,
		'apis':{
			'sf-muni': {
				'base':"http://webservices.nextbus.com/service/publicXMLFeed?a=sf-muni&command=",
				'route':"&r=",
				'commands':{
					'route_list':"routeList",
					'route_data':"routeConfig"
				}
			}
		}
	}
 }



def main():
	"""Execute the main actions of the network builder program

	Argus:
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
		pass
		# calculate_road_distances(sys.argv[2])
		#calculate_road_distance_per_row(["262", "264", "265", "266", "267", "268", "269", "270", "271", "271", "273"], ["4907", "4165", "10375", "7773", "4040", "5109", "9687", "5231", "280", "7497", "2768"], sys.argv[2])
		#calculate_road_distance_per_row(["269", "270", "271", "271"], ["9687", "5231", "280", "7497"], sys.argv[2])

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
		'length': 0,
		'road-distance': 0}
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
				'road-distance': 0}
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
		'road-distance': connection_1['road-distance']}


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

	#Set google client key
	gmaps = googlemaps.Client(key="AIzaSyB2yJoPRC-bIAPE9CQZBmyyjL_5r--OJSI")
	
	#Create a list of latitudes and longtitudes for origins and destinations
	from_stops_lat_lon = []
	to_stops_lat_lon = []
	
	# counter used to point to connections_list
	c1 = 1
	
	# limit for each api call
	api_call_limit = 10
	
	len_c = len(connections_list)
	
	while c1 <= len_c:
		if len_c - c1 < api_call_limit:
			c3 = len_c - c1 + 1
		else:
			c3 = api_call_limit		
		from_stops_lat_lon = []
		to_stops_lat_lon = []
		c2 = 1
		for connection in connections_list: # If considered ordered, we could change to while, to change the pointer of where to start
			from_stop = connection['from']
			to_stop = connection['to']
	
			flag1 = 0
			for stop in stops_list: 
				if (stop['tag'] == from_stop):
					lat1 = stop['lat']
					lon1 = stop['lon']
					if flag1 == 0:
						flag1 = 1
						continue
					elif flag1 == 1:
						break
				if (stop['tag'] == to_stop):
					lat2 = stop['lat']
					lon2 = stop['lon']
					if flag1 == 0:
						flag1 = 1
						continue
					elif flag1 == 1:
						break
	
			from_stops_lat_lon.append([lat1, lon1])
			to_stops_lat_lon.append([lat2, lon2])
			
			c2 = c2 + 1
			if c2 > c3:
				break
	
		#Call to google distance matrix api
		google_result = gmaps.distance_matrix(origins = from_stops_lat_lon, destinations = to_stops_lat_lon,  mode = "driving")
		
		for stop1 in range(0, c3):
			single_distance = google_result['rows'][stop1]['elements'][stop1]['distance']['value']
			connections_list[c1-1]['road_distance'] = single_distance			
		
		c1 = c1 + c3
	write_connections_file(cities[city]['tag'], connections_list)

def calculate_road_distance_per_row(from_stops, to_stops,  city):
	# input: lists of tags of stops, from_stops and to_stops, and directory
	#
	# len(from_stops) <= 25
	# len(to_stops) <= 25
	# len (from_stops) = len (to_stops)
	# return [
	#   {'distance': 17451, 'from': '263', 'to': '311'},
	#   {'distance': 19553, 'from': '263', 'to': '359'},
	#   {'distance': 11186, 'from': '265', 'to': '311'},
	#   {'distance': 26893, 'from': '265', 'to': '359'}
	#   ]
	
	# read the previously-built network data
	stops_list = read_stops_file(cities[city]['tag'])
	
	#Set google client key
	gmaps = googlemaps.Client(key="AIzaSyB2yJoPRC-bIAPE9CQZBmyyjL_5r--OJSI")
	
	#Create a list of latitudes and longtitudes for origins and destinations
	from_stops_lat_lon = []
	to_stops_lat_lon = []
	for stop1 in from_stops:
		for stop2 in stops_list:
			if (stop2['tag'] == stop1):
				from_stops_lat_lon.append([(stop2['lat']), (stop2['lon'])])
				break
	for stop1 in to_stops:
		for stop2 in stops_list:
			if (stop2['tag'] == stop1):
				to_stops_lat_lon.append([(stop2['lat']), (stop2['lon'])])
				break

	#Call to google distance matrix api
	google_result = gmaps.distance_matrix(origins = from_stops_lat_lon, destinations = to_stops_lat_lon,  mode = "driving")
	
	#Format output from the resulting google maps api call
	distances = []
	for stop1 in range(0, len(from_stops)):
		#for stop2 in range(0, len(to_stops)):
		single_distance = google_result['rows'][stop1]['elements'][stop1]['distance']['value']
		distances.append({"from":from_stops[stop1], "to":to_stops[stop1], "distance":single_distance})
	return distances

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




# ===============================================
if __name__ == "__main__":
    main()
