import requests, sys, os, math
import xml.etree.ElementTree as ET
from itertools import groupby
from functools import reduce
from pprint import pprint

from common import *



def main():
	"""Execute the main actions of the network builder program

	Argus:
		static - build the static network of stops and connections between them
		distances - calculate the straight-line and road distances between stops

		agency,agency_2,... - the transit agency for which we want to retrieve routes
		
	"""

	# With the "static" argument, build the static network
	if len(sys.argv) > 2 and (sys.argv[1] == "static" or sys.argv[1] == "-s" ):

		agencies = sys.argv[2].split(",")
		build_static_network(agencies)

	# With the "distances" argument, calculate the distances between stops
	elif len(sys.argv) > 2 and (sys.argv[1] == "distances" or sys.argv[1] == "-d" ):

		calculate_distances(sys.argv[2])

	# With wrong arguments, print usage help message
	else:
		print("Usage: builder <static|distances> <agency>[,<agency_2>,...]")

		


# ===============================================
# =			Static Network Construction 		=
# ===============================================

def build_static_network(agencies):
	"""Construct the atops & connection network of the transport system from all the routes"""

	# Get the list of routes and stops for these agencies
	routes_list = get_routes_list(agencies)
	print("Found " + str(len(routes_list)) + " routes")

	# Hold all the stops and their connections
	stops_list = []
	connections_list = []

	# Iterate through routes
	for index, route in enumerate(routes_list):
		route_xml = ET.fromstring( call_transit_API(route["agency"], "route_data", route["tag"]) )[0]
		stops_list = stops_list + get_route_stops(route_xml)
		connections_list = connections_list + get_route_connections(route_xml)

		print("Extracted data from " + str( index + 1 ) + "/" + str(len(routes_list)) + " routes", end="\r")

	# # After all routes, consolidate data
	stops_list = consolidate_stops(stops_list)
	connections_list = consolidate_connections(connections_list)

	print("\nFound " + str(len(stops_list)) + " stops and " + str(len(connections_list)) + " connections")

	# Write results to files
	write_stops_file(','.join(agencies), stops_list)
	write_connections_file(','.join(agencies), connections_list)


def get_routes_list(agencies):
	"""Use the API to retrieve a list of the agencies's routes."""

	routes_list = []

	for agency in agencies:

		routes_tree = ET.fromstring(call_transit_API(agency, "route_list"))
		# we are only interested in the route tags
		routes_map = map((lambda x: {"tag": x.attrib["tag"], "agency": agency}), routes_tree)
		# convert to list
		routes_list = routes_list + list(routes_map)

	return routes_list[:10] # DEBUG only the first 10 routes


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

def calculate_distances(directory):
	"""Calculate the straight-line and road distances between the connected stops of the network."""

	# read the previously-built network data
	stops_list = read_stops_file(directory)
	connections_list = read_connections_file(directory)

	connections_list = list(map(lambda connection: build_single_connection(connection, stops_list), connections_list))
		
	# pprint(connections_list)
	write_connections_distances_file(directory, connections_list)


def build_single_connection(connection,stops_list):
	"""Calculate the distance for a single connection and return it as a dictionary object"""

	stop1 = connection['from']
	stop2 = connection['to']
	routes = connection['routes']
	flag1 = 0

	#Radius of the Earth in kilometeres, used for 37 degrees, like Washington D.C.
	R = 6373

	for stop in stops_list: 
		if (stop['tag'] == stop1):
			lat1 = float(stop['lat']) * (math.pi / 180)
			lon1 = float(stop['lon']) * (math.pi / 180)
			if flag1 == 0:
				flag1 = 1
				continue
			elif flag1 == 1:
			 	break
		if (stop['tag'] == stop2):
			lat2 = float(stop['lat']) * (math.pi / 180)
			lon2 = float(stop['lon']) * (math.pi / 180)
			if flag1 == 0:
				flag1 = 1
				continue
			elif flag1 == 1:
				break
	dlon = lon2 - lon1
	dlat = lat2 - lat1
	a = ((math.sin(dlat/2))**2) + (math.cos(lat1) * math.cos(lat2) * ((math.sin(dlon/2))**2))
	c = 2 * math.atan2(math.sqrt(a),  math.sqrt(1-a))
	d = R * c

	return {"from": stop1, "to": stop2, "routes": routes, "straight-distance": str(d), "road-distance": str(0)}


# def calculate_road_distance(from_stops,to_stops):
	# len(from_stops) < 25
	# ...
	# ...


	# return [
	# 		{"from":"1324","to":"5","distance":25},
	# 		{"from":"1342","to":"5","distance":25},
	# 		{"from":"1","to":"5","distance":25},
	# 	]



# ===============================================
# =					API calls 					=
# ===============================================

def call_transit_API(agency, command, route = "", stop = ""):
	"""Call the agency's API for a specific command.

	Args:
		agency: The agency we are interested in
		command: The command we want to give.
		route: The route used in the command (optional).
		stop: The stop used in the command (optional).

	Returns:
		The response body.

	"""

	APIs_dict = {
		'ttc':{
			'api_base':"http://webservices.nextbus.com/service/publicXMLFeed?a=ttc&command=",
			'route_option':"&r=",
			'commands':{
				'route_list':"routeList",
				'route_data':"routeConfig"
				}
			},
		'nextTrain':{
			'api_base':"sadda"
			}
		}

	if command == 'route_list':
		options_url = ''
	elif command == 'route_data' and route != '':
		options_url = APIs_dict[agency]['route_option'] + route

	return requests.get(APIs_dict[agency]['api_base'] + APIs_dict[agency]['commands'][command] +  options_url).text




# ===============================================
if __name__ == "__main__":
    main()
