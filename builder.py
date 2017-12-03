import requests, sys, json, numpy
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

	# With the "distances" argument, calculate the distances between stops
	elif len(sys.argv) > 2 and (sys.argv[1] == "distances" or sys.argv[1] == "-d" ):

		calculate_distances(sys.argv[2])
		calculate_road_distances(sys.argv[2])

	# With the "times" argument, calculate the times between stops
	elif len(sys.argv) > 2 and (sys.argv[1] == "times" or sys.argv[1] == "-t" ):
		
		calculate_times(sys.argv[2])
		
	# With the "cleanup" argument, remove invalid routes and cleanup data
	elif len(sys.argv) > 2 and (sys.argv[1] == "clean" or sys.argv[1] == "-c" ):
		
		cleanup(sys.argv[2])
		
	# With the "all" argument, calculate everything in a row
	elif len(sys.argv) > 2 and (sys.argv[1] == "all" or sys.argv[1] == "-a" ):
		
		build_static_network(sys.argv[2])

		calculate_distances(sys.argv[2])
		calculate_road_distances(sys.argv[2])

		calculate_times(sys.argv[2])
		
		cleanup(sys.argv[2])
		
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
		route_stops = get_route_stops(route_xml)
		route['stops_count'] = len(route_stops)
		stops_list = stops_list + route_stops

		connections_list = connections_list + get_route_connections(route_xml)

		print("Extracted data from " + str( index + 1 ) + "/" + str(len(routes_list)) + " routes", end="\r")

	# After all routes, clean and consolidate data
	stops_list = consolidate_stops(stops_list)
	stops_list = remove_isolated_stops(stops_list, connections_list)
	stops, connections_list = merge_nearby_stops(stops_list, connections_list, cities[city]['radius'])
	connections_list = consolidate_connections(connections_list)

	print("Found " + str(len(stops_list)) + " stops and " + str(len(connections_list)) + " connections")

	# Write results to files
	write_routes_file(cities[city]['tag'], routes_list)
	write_stops_file(cities[city]['tag'], stops_list)
	write_connections_file(cities[city]['tag'], connections_list)


def get_routes_list(city):
	"""Use the API to retrieve a list of the city's routes."""

	routes_list = []

	for api in cities[city]['apis']:

		routes_tree = ET.fromstring(call_transit_API(cities[city]['apis'][api], "route_list"))
		# we are only interested in the route tags
		routes_map = map((lambda x: {"tag":x.attrib["tag"],
			"api":api,
			"stops_count":0,
			"wait_time_mean":-1,
			"wait_time_std":-1}), routes_tree)
		# convert to list
		routes_list = routes_list + list(routes_map)

	return routes_list # DEBUG only the first 10 routes


def get_route_stops(route_xml):
	"""Extract the list of stops for this route."""

	# keep only stop xml elements
	stops_map = filter((lambda x: x.tag=="stop"), route_xml)

	# lambda function to turn xml attributes into dictionary keys
	stop_dict_func = lambda x: {
		'tag': x.attrib['tag'],
		'title': x.attrib['title'],
		'lat': x.attrib['lat'],
		'lon': x.attrib['lon'],
		'merged': [x.attrib['tag']]}
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
			from_stop = direction[i].attrib['tag']
			to_stop = direction[i+1].attrib['tag']

			# add the new connection between stops
			connection_dict = {
				'from': from_stop,
				'to': to_stop,
				'routes': [route_xml.attrib['tag']],
				'length': 0,
				'road_length': 0,
				'travel_time': -1}
			connections_list.append(connection_dict)

	return connections_list
		

def consolidate_stops(stops_list):
	"""Remove duplicates from the list of stops."""

	# Turn stop list into a dictionary and back to remove duplicates
	stops_list = list({stop['tag']: stop for stop in stops_list}.values())
	# Sort list (optional)
	stops_list.sort(key=(lambda x: x['tag']))

	return stops_list


def consolidate_connections(connections_list):
	"""Merge duplicates from the list of connections."""

	# Sort list (optional)
	connections_list.sort(key=(lambda x: (x['from'], x['to']) ))

	# Remove self loops
	for i in reversed(range(0,len(connections_list))):
		if (connections_list[i]['from'] == connections_list[i]['to']):
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
		'road_length': connection_1['road_length'],
		'travel_time': connection_1['travel_time']}


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

		connection['road_length'] = distances_list[index]

		if (connection['length'] == 0):
			connection['road_length'] = 0

		# Suspiciously big difference in distances, recalculate
		elif (connection['road_length']/connection['length'] > 2 ):
			connection['road_length'] = call_distance_API([stops_dict[connection['from']]],[stops_dict[connection['to']]])[0]

		if (connection['length'] > distances_list[index]):
			connection['road_length'] = connection['length']

		index = index + 1

		print("Calculated distances for " + str( index + 1 ) + "/" + str(len(connections_list)) + " connections", end="\r")


	write_connections_file(cities[city]['tag'], connections_list)


# ===============================================
# =			Network Times Calculation			=
# ===============================================


def calculate_times(city):

	# read the previously-built network data
	routes_list = read_routes_file(cities[city]['tag'])
	stops_list = read_stops_file(cities[city]['tag'])
	connections_list = read_connections_file(cities[city]['tag'])

	# Turn list of stops into dictionary for direct access
	stops_dict = {stop['tag']: stop for stop in stops_list}

	# Add an empty array to connections for holding all possible travel times
	for connection in connections_list:
		connection['travel_time-array'] = []

	# Iterate through routes
	for index, route in enumerate(routes_list):

		# Retrieve stops again to make sure they are correct
		route_xml = ET.fromstring( call_transit_API(cities[city]['apis'][route['api']], "route_data", route["tag"]) )[0]
		route_stops = [stop['tag'] for stop in get_route_stops(route_xml)]

		# Retrieve time predictions for this route and these stops
		predictions_xml = call_transit_API(cities[city]['apis'][route['api']], "predictions", route["tag"], route_stops)

		# Convert from xml to actual objects
		route_predictions = get_route_predictions(ET.fromstring(predictions_xml))

		# If this an actual entry without errors
		if (len(route_predictions) > 0):

			route['wait_time_mean'], route['wait_time_std'] = calculate_route_wait_time(route_predictions)
			
			# If this isn't a route with no time predictions (nighttime buses)
			if (route['wait_time_mean'] != -1):

				# Get the connections involved in this route
				route_connections = [connection for connection in connections_list if (route['tag'] in connection['routes']) ]

				# Calculate travel times
				calculate_connection_travel_times(route_predictions, route_connections, stops_dict)
		
		print("Calculated times from " + str( index + 1 ) + "/" + str(len(routes_list)) + " routes", end="\r")


	consolidate_connection_times(connections_list)

	# Write results to files
	write_routes_file(cities[city]['tag'], routes_list)
	write_connections_file(cities[city]['tag'], connections_list)


def get_route_predictions(predictions_xml):
	"""Extract the list of stops for this route."""

	predictions_list = []

	for prediction_xml in predictions_xml:

		# If we have directions for this stop
		if (len(prediction_xml) > 0):

			trips_list = []

			# Go through all the directions (and directions only)
			for direction in prediction_xml:
				if (direction.tag == "direction"):

					# Go through all the individual trips
					for trip in direction:
						if ('tripTag' in trip.attrib):

							# Add the trip entry
							trip_entry = {'tag': trip.attrib['tripTag'],
								'minutes': int(trip.attrib['minutes']),
								'direction': trip.attrib['dirTag']}
								# 'isDeparture': trip.attrib['isDeparture'] == 'true'}

							trips_list.append(trip_entry)


			# If there were no problems with that prediction
			if (trips_list):
				
				# Add the prediction entry
				prediction_entry = { 'route': prediction_xml.attrib['routeTag'],
					'stop': prediction_xml.attrib['stopTag'],
					'trips': trips_list}

				predictions_list.append(prediction_entry)

	return predictions_list


def calculate_route_wait_time(route_predictions):

	trip_wait_times = []

	# Go through every stop in route
	for stop_prediction in route_predictions:

		# Group together trips in the same direction
		for direction, same_direction_trips in groupby(stop_prediction['trips'], lambda x: x['direction']):
			index = 0
			same_direction_trips = list(same_direction_trips)
			same_direction_count = len(same_direction_trips)
			for trip in same_direction_trips:

				# Wait times are times between consecutive trips
				if (index < same_direction_count - 1):
					trip_wait_times.append(same_direction_trips[index+1]['minutes'] - same_direction_trips[index]['minutes'])

				index = index + 1

	if(len(trip_wait_times) > 0):
		wait_time_average = numpy.mean(trip_wait_times)
		wait_time_standard_deviation = numpy.std(trip_wait_times)
	else:
		wait_time_average = -1
		wait_time_standard_deviation = -1


	return wait_time_average, wait_time_standard_deviation


def calculate_connection_travel_times(route_predictions, route_connections, stops_dict):

	# Go through all possible combinations of stops in the predictions
	for from_prediction in route_predictions:
		for to_prediction in route_predictions:

			from_stop = from_prediction['stop']
			to_stop = to_prediction['stop']

			# Find pairs of stops that correspond to actual connections (including merged stops)
			for connection in route_connections:
				if ((from_stop == connection['from'] or from_stop in stops_dict[connection['from']]['merged'])
					and (to_stop == connection['to'] or to_stop in stops_dict[connection['to']]['merged'])):

					connection_times = []

					# Find individual trips
					for from_trip in from_prediction['trips']:
						for to_trip in to_prediction['trips']:
							if (from_trip['tag']==to_trip['tag']):

								# And finally calculate time
								trip_time = to_trip['minutes'] - from_trip['minutes']

								# If trip in the right direction (a.k.a. time positive)
								if (trip_time >= 0):
									connection_times.append(trip_time)

					# If trips were found, calculate the average trip time
					if (len(connection_times) > 0):
						travel_time = numpy.mean(connection_times)
						connection['travel_time-array'].append(travel_time)


def consolidate_connection_times(connections_list):

	for connection in connections_list:

		if (len(connection['travel_time-array']) > 0):
			connection['travel_time'] = numpy.mean(connection['travel_time-array'])
		else:
			connection['travel_time'] = -1

		connection.pop('travel_time-array', None)



def cleanup(city):

	# read the previously-built network data
	routes_list = read_routes_file(cities[city]['tag'])
	stops_list = read_stops_file(cities[city]['tag'])
	connections_list = read_connections_file(cities[city]['tag'])


	average_city_speed = 0
	index = 0

	# Calculate average connection speed
	for connection in connections_list:

		if (connection['travel_time'] > 0):
			average_city_speed = average_city_speed + (connection['road_length']/float(connection['travel_time']))
			index = index + 1

		elif (connection['travel_time'] == 0):
			index = index + 1

	average_city_speed = average_city_speed/index

	invalid_routes = []
	valid_routes = []

	# Find invalid routes (nightly, etc.)
	for route in routes_list:
		if (route['wait_time_mean'] <= 0 ):

			invalid_routes.append(route['tag'])
		else:
			valid_routes.append(route)

	valid_connections = []

	# Find connections with invalid times
	for connection in connections_list:

		if(connection['travel_time'] < 0):
	
			# Only keep connections if they don't belong only in invalid routes
			if ( [route for route in connection['routes'] if (route not in invalid_routes) ] ):

			# Else approximate travel time using length and average city speed
				valid_connections.append(connection)
				connection['travel_time'] = connection['length'] * average_city_speed
		else:
			valid_connections.append(connection)

	print("Data cleaned up! Final counts: " + str(len(valid_routes))
		+ " routes, " + str(len(stops_list))
		+ " stops, " + str(len(valid_connections)) + " connections.")

	# Write results to files
	write_routes_file(cities[city]['tag'], valid_routes)
	write_connections_file(cities[city]['tag'], valid_connections)	



# ===============================================
# =					API calls 					=
# ===============================================

def call_transit_API(api, command, route = "", stops=[]):
	"""Call the agency's API for a specific command.

	Args:
		api: The API of the agency we are interested in
		command: The command we want to give.
		route: The route used in the command (optional).
		stops: The listof stops for that route (optional)

	Returns:
		The response body.

	"""

	if command == 'route_list':
		options_url = ''

	elif command == 'route_data' and route != '':
		options_url = api['route'] + route

	elif command == 'predictions' and route != '':

		options_url = ''
		for stop in stops:
			options_url = options_url + '&stops=' + route + "|" + stop

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
