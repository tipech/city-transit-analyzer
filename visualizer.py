import sys,random,math,numpy
import networkx as nx
import matplotlib.pyplot as plt
from pprint import pprint

from common import *



def main():
	"""Execute the main actions of the network visualizer program

	Arguments:
		static - draw the static network

		city - 

	"""

	# With the "draw" argument, draw the network
	if len(sys.argv) > 2 and (sys.argv[1] == "draw" or sys.argv[1] == "-d" ):

		draw_static_network(G,stops_list)


	# With the "poi" argument, calculate poi statistics
	elif len(sys.argv) > 2 and (sys.argv[1] == "poi" or sys.argv[1] == "-p" ):


		metrics = []

		for city in sys.argv[2].split(","):

			# Read the network files
			routes_list = read_routes_file(cities[city]['tag'])
			stops_list = read_stops_file(cities[city]['tag'])
			connections_list = read_connections_file(cities[city]['tag'])
			poi_list = read_poi_file(cities[city]['tag'])

			sample_size = sys.argv[3]
			sample_size = sys.argv[4]

			G = create_directed_network(stops_list, connections_list)
			radius = cities[city]['radius']
			area = cities[city]['area']


			# ------------ Points Of Interest -----------
			poi = calculate_poi_uniform(G, routes_list, stops_list, connections_list, poi_list,
				radius, sample_size, repetitions, poi_type)
		
			print(poi)

			print("Calculated poi for: " + city + "                    ")


	# With the "metrics" argument, calculate all metrics
	elif len(sys.argv) > 2 and (sys.argv[1] == "metrics" or sys.argv[1] == "-m" ):

		metrics = []

		for city in sys.argv[2].split(","):

			# Read the network files
			routes_list = read_routes_file(cities[city]['tag'])
			stops_list = read_stops_file(cities[city]['tag'])
			connections_list = read_connections_file(cities[city]['tag'])

			sample_size = int(sys.argv[3])
			repetitions = int(sys.argv[4])

			G = create_directed_network(stops_list, connections_list)
			
			city_metrics = calculate_city_metrics(G, routes_list, stops_list, connections_list, city, sample_size, repetitions)
			metrics.append(city + "," + ",".join(str(value) for value in city_metrics.values()))
			write_metrics_file("city," + ",".join(str(value) for value in city_metrics.keys())
				+ "\n".join(metrics) + "\n")
		
			print("Calculated metrics for: " + city + "                    ")


		metrics = ["city," + ",".join(str(value) for value in city_metrics.keys())] + metrics
		metrics_text = "\n".join(metrics) + "\n"
		write_metrics_file(metrics_text)
		# print(metrics_text)

	# With the "evaluation" argument, calculate some paths for evaluation
	elif len(sys.argv) > 2 and (sys.argv[1] == "evaluation" or sys.argv[1] == "-e" ):

		city = sys.argv[2]
		sample_size = int(sys.argv[3])
		repetitions = 1

		# Area and earth radius presets
		radius = cities[city]['radius']
		area = cities[city]['area']

		# Read the network files
		routes_list = read_routes_file(cities[city]['tag'])
		stops_list = read_stops_file(cities[city]['tag'])
		connections_list = read_connections_file(cities[city]['tag'])
		sectors_list = read_demographics_file(cities[city]['tag'])

		G = create_directed_network(stops_list, connections_list)

		calculate_trip_uniform(G, routes_list, stops_list, connections_list, radius, sample_size, repetitions)
		calculate_trip_population(G, routes_list, stops_list, connections_list, sectors_list, radius, sample_size, repetitions)

	# With wrong arguments, print usage help message
	else:
		print("Usage: visualizer <metrics|evaluation|draw|poi> <city>[,<city_2>,...]")

		

def create_directed_network(stops_list, connections_list):
	"""Draw an image for the pre-built static network of the transport system."""


	# Build the graph object, add stops and connections
	G = nx.DiGraph()
	G.add_nodes_from(convert_stops_to_tuples(stops_list))
	G.add_edges_from(convert_connections_to_tuples(connections_list))

	# G = nx.connected_components(G)

	return G



# ===============================================
# =				Metrics Calculation				=
# ===============================================

def calculate_city_metrics(G, routes_list, stops_list, connections_list, city, sample_size, repetitions):

	sectors_list = read_demographics_file(cities[city]['tag'])

	# Area and earth radius presets
	radius = cities[city]['radius']
	area = cities[city]['area']

	metrics = {}


	# ----------- General Statistics ------------
	metrics['routes_count'] = len(routes_list)
	metrics['stops_count'] = len(stops_list)
	metrics['connections_count'] = len(connections_list)

	metrics['total_length'] = sum(connection['length'] for connection in connections_list)
	# metrics['total_length_normalized'] = metrics['total_length']/area
	metrics['connection_length_average'] = metrics['total_length']/metrics['connections_count']

	metrics['total_travel_time'] = sum([connection['travel_time'] for connection in connections_list])
	metrics['connection_travel_time_average'] = metrics['total_travel_time']/metrics['connections_count']

	metrics['connection_speed_average'] = 60*metrics['total_length']/metrics['total_travel_time']

	metrics['wait_time_average'] = numpy.mean([route['wait_time_mean'] for route in routes_list])/2
	metrics['wait_time_std'] = numpy.std([route['wait_time_mean'] for route in routes_list])/2


	# --------- Shortest Times & Paths ----------
	(metrics['average_trip_time_uniform'],
		metrics['average_trip_length_uniform'],
		metrics['average_transfers_uniform'],
		metrics['average_straight_distance_uniform']) = (
		calculate_trip_uniform(G, routes_list, stops_list, connections_list, radius, sample_size, repetitions))

	metrics['average_trip_length_normalized_uniform'] = metrics['average_trip_length_uniform']/metrics['average_straight_distance_uniform']
	metrics['average_time_normalized_uniform'] = metrics['average_trip_time_uniform']/metrics['average_straight_distance_uniform']
	metrics['average_transfers_normalized_uniform'] = metrics['average_transfers_uniform']/metrics['average_straight_distance_uniform']
	


	# --- Shortest Population Times and Paths ---
	(metrics['average_trip_time_population'],
		metrics['average_trip_length_population'],
		metrics['average_transfers_population'],
		metrics['average_straight_distance_population']) = (
		calculate_trip_population(G, routes_list, stops_list, connections_list, sectors_list, radius, sample_size, repetitions))

	metrics['average_trip_length_normalized_population'] = metrics['average_trip_length_population']/metrics['average_straight_distance_population']
	metrics['average_time_normalized_population'] = metrics['average_trip_time_population']/metrics['average_straight_distance_population']
	metrics['average_transfers_normalized_population'] = metrics['average_transfers_population']/metrics['average_straight_distance_population']
	


	# ----------------- Coverage ----------------
	metrics['uniform_coverage_stops'], metrics['uniform_coverage_distance'] = (
		calculate_uniform_coverage(stops_list, radius, sample_size, repetitions))
	metrics['population_coverage_stops'], metrics['population_coverage_distance'] = (
		calculate_population_coverage(stops_list, sectors_list, radius, sample_size, repetitions))


	# -------- Clustering & Connectivity --------
	# metrics['average_clustering'] = nx.average_clustering(G,weight='length')

	# metrics['degree_connectivity'] = nx.average_degree_connectivity(G,weight='length')

	return metrics


def calculate_uniform_coverage(stops_list, radius, sample_size, repetitions):

	cutoff_high_deg = 0.0072	# 800m
	cutoff_low_deg = 0.0036  	# 400m
	walk_km = 0.4				# 400m

	lat_list = [float(stop['lat']) for stop in stops_list]
	lon_list = [float(stop['lon']) for stop in stops_list]

	bounding_box = { 'left': min(lon_list) - cutoff_low_deg,
		'right': max(lon_list) + cutoff_low_deg,
		'top': max(lat_list) + cutoff_low_deg,
		'bottom': min(lat_list) - cutoff_low_deg}

	close_stops = 0
	least_distance = 0

	# Average over several seeds
	for i in range(0,repetitions):

		random.seed()
		for x in range(0,sample_size):

			random_lat, random_lon = select_random_point_uniform(bounding_box)

			# Make sure we are within the service area (within 800m of nearest stop)
			cutoff_square_stops = get_stops_in_square(stops_list, random_lat, random_lon, cutoff_high_deg)
			while (len(cutoff_square_stops) == 0):
				random_lat, random_lon = select_random_point_uniform(bounding_box)
				cutoff_square_stops = get_stops_in_square(stops_list, random_lat, random_lon, cutoff_high_deg)

			# Calculate number of close stops and least distance
			close_stops_count, close_stops_distances = (
				calculate_close_stops(cutoff_square_stops, random_lat, random_lon, cutoff_low_deg, radius))
			least_distance_stop = calculate_least_distance(random_lat, random_lon, close_stops_distances, cutoff_square_stops, radius)

			close_stops = close_stops + close_stops_count
			least_distance = least_distance + least_distance_stop
			print("Calculated area coverage for " + str(x + i*sample_size) + "/" + str(sample_size*repetitions), end="\r")

	return close_stops/(sample_size*repetitions), least_distance/(sample_size*repetitions)


def calculate_population_coverage(stops_list, sectors_list, radius, sample_size, repetitions):

	population_distribution = [sector['population'] for sector in sectors_list]

	cutoff_high_deg = 0.0072	# 800m
	cutoff_low_deg = 0.0036  	# 400m

	close_stops = 0
	least_distance = 0

	# Average over several seeds
	for i in range(0,repetitions):

		random.seed()
		for x in range(0,sample_size):

			random_lat, random_lon = select_random_point_population(population_distribution, sectors_list)

			# Make sure we are within the service area (within 800m of nearest stop)
			cutoff_square_stops = get_stops_in_square(stops_list, random_lat, random_lon, cutoff_high_deg)
			while (len(cutoff_square_stops) == 0):
				random_lat, random_lon = select_random_point_population(population_distribution, sectors_list)
				cutoff_square_stops = get_stops_in_square(stops_list, random_lat, random_lon, cutoff_high_deg)

			# Calculate number of close stops and least distance
			close_stops_count, close_stops_distances = (
				calculate_close_stops(cutoff_square_stops, random_lat, random_lon, cutoff_low_deg, radius))
			least_distance_stop = calculate_least_distance(random_lat, random_lon, close_stops_distances, cutoff_square_stops, radius)

			close_stops = close_stops + close_stops_count
			least_distance = least_distance + least_distance_stop
			print("Calculated population coverage for " + str(x + i*sample_size) + "/" + str(sample_size*repetitions), end="\r")

	return close_stops/(sample_size*repetitions), least_distance/(sample_size*repetitions)


def calculate_trip_uniform(G, routes_list, stops_list, connections_list, radius, sample_size, repetitions):

	cutoff_high_deg = 0.0072	# 800m
	cutoff_low_deg = 0.0036  	# 400m
	# Adjust the result by 30% due to greedy path bias
	adjustment_weight = 0.7

	lat_list = [float(stop['lat']) for stop in stops_list]
	lon_list = [float(stop['lon']) for stop in stops_list]

	routes_dict = {route['tag']:route for route in routes_list}

	bounding_box = { 'left': min(lon_list) - cutoff_low_deg,
		'right': max(lon_list) + cutoff_low_deg,
		'top': max(lat_list) + cutoff_low_deg,
		'bottom': min(lat_list) - cutoff_low_deg}

	trip_time = 0
	trip_distance = 0
	trip_transfers = 0
	trip_straight_distance = 0

	# Average over several seeds
	for i in range(0,repetitions):

		random.seed()
		x=0
		while x < sample_size:

			random_lat_1, random_lon_1 = select_random_point_uniform(bounding_box)
			random_lat_2, random_lon_2 = select_random_point_uniform(bounding_box)

			# Make sure first point is within the service area (within 800m of nearest stop)
			cutoff_square_stops = get_stops_in_square(stops_list, random_lat_1, random_lon_1, cutoff_high_deg)
			while (len(cutoff_square_stops) == 0):
				random_lat_1, random_lon_1 = select_random_point_uniform(bounding_box)
				cutoff_square_stops = get_stops_in_square(stops_list, random_lat_1, random_lon_1, cutoff_high_deg)

			stop_1 = get_closest_stop(random_lat_1, random_lon_1, cutoff_square_stops, radius)

			# Make sure second point is within the service area (within 800m of nearest stop)
			cutoff_square_stops = get_stops_in_square(stops_list, random_lat_2, random_lon_2, cutoff_high_deg)
			while (len(cutoff_square_stops) == 0):
				random_lat_2, random_lon_2 = select_random_point_uniform(bounding_box)
				cutoff_square_stops = get_stops_in_square(stops_list, random_lat_2, random_lon_2, cutoff_high_deg)

			stop_2 = get_closest_stop(random_lat_2, random_lon_2, cutoff_square_stops, radius)

			# Find shortest path (forward or backwards)
			try:
				path = nx.shortest_path(G, stop_1['tag'], stop_2['tag'], 'travel_time')
			except nx.NetworkXNoPath:
				try:
					path = nx.shortest_path(G, stop_2['tag'], stop_1['tag'], 'travel_time')
				except nx.NetworkXNoPath:
					path = -1

			# pprint(path)

			# If it exists, get data on it
			if(path != -1):

				connections_seq =  convert_stops_seq_to_connections_seq(path, connections_list)
				transfers, trip_legs = count_route_transfers(connections_seq, routes_dict)

				wait_time = 0
				for leg_routes in trip_legs:
					
					wait_times_list = [routes_dict[route]['wait_time_mean'] for route in leg_routes]
					if(wait_times_list):
						wait_time = wait_time + min(wait_times_list)/2
					else:
						transfers = -1
			
				if(transfers != -1):
					print("Trip:                                ")
					print("From: " + str(random_lat_1) + "," + str(random_lon_1) + " to: " + str(random_lat_2) + "," + str(random_lon_2))
					print("Time: ")
					print(adjustment_weight*wait_time + sum([connection['travel_time'] for connection in connections_seq]))
					print("Distance: ")
					print(sum([connection['road_length'] for connection in connections_seq]))
					print("Transfers: ")
					print(transfers)
					print("Straight Distance: ")
					print(calculate_straight_distance(stop_1['lat'], stop_1['lon'], stop_2['lat'], stop_2['lon'], radius))
					print(" ")

					trip_time = trip_time + adjustment_weight*wait_time + sum([connection['travel_time'] for connection in connections_seq])
					trip_distance = trip_distance + sum([connection['road_length'] for connection in connections_seq])
					trip_transfers = trip_transfers + transfers
					trip_straight_distance = (trip_straight_distance + 
						calculate_straight_distance(stop_1['lat'], stop_1['lon'], stop_2['lat'], stop_2['lon'], radius))
					x = x + 1
					print("Calculated trip stats for " + str(x + i*sample_size) + "/" + str(sample_size*repetitions), end="\r")

	print("")

	return (trip_time/(sample_size*repetitions),
		trip_distance/(sample_size*repetitions),
		trip_transfers/(sample_size*repetitions),
		trip_straight_distance/(sample_size*repetitions))


def calculate_trip_population(G, routes_list, stops_list, connections_list, sectors_list, radius, sample_size, repetitions):

	# Adjust the result by 30% due to greedy path bias
	adjustment_weight = 0.7

	population_distribution = [sector['population'] for sector in sectors_list]
	
	routes_dict = {route['tag']:route for route in routes_list}

	cutoff_high_deg = 0.0072	# 800m
	cutoff_low_deg = 0.0036  	# 400m

	trip_time = 0
	trip_distance = 0
	trip_transfers = 0
	trip_straight_distance = 0

	# Average over several seeds
	for i in range(0,repetitions):

		random.seed()
		x=0
		while x < sample_size:

			random_lat_1, random_lon_1 = select_random_point_population(population_distribution, sectors_list)
			random_lat_2, random_lon_2 = select_random_point_population(population_distribution, sectors_list)

			# Make sure first point is within the service area (within 800m of nearest stop)
			cutoff_square_stops = get_stops_in_square(stops_list, random_lat_1, random_lon_1, cutoff_high_deg)
			while (len(cutoff_square_stops) == 0):
				random_lat_1, random_lon_1 = select_random_point_population(population_distribution, sectors_list)
				cutoff_square_stops = get_stops_in_square(stops_list, random_lat_1, random_lon_1, cutoff_high_deg)

			stop_1 = get_closest_stop(random_lat_1, random_lon_1, cutoff_square_stops, radius)

			# Make sure second point is within the service area (within 800m of nearest stop)
			cutoff_square_stops = get_stops_in_square(stops_list, random_lat_2, random_lon_2, cutoff_high_deg)
			while (len(cutoff_square_stops) == 0):
				random_lat_2, random_lon_2 = select_random_point_population(population_distribution, sectors_list)
				cutoff_square_stops = get_stops_in_square(stops_list, random_lat_2, random_lon_2, cutoff_high_deg)

			stop_2 = get_closest_stop(random_lat_2, random_lon_2, cutoff_square_stops, radius)

			# Find shortest path (forward or backwards)
			try:
				path = nx.shortest_path(G, stop_1['tag'], stop_2['tag'], 'travel_time')
			except nx.NetworkXNoPath:
				try:
					path = nx.shortest_path(G, stop_2['tag'], stop_1['tag'], 'travel_time')
				except nx.NetworkXNoPath:
					path = -1

			# If it exists, get data on it
			if(path != -1):

				connections_seq =  convert_stops_seq_to_connections_seq(path, connections_list)
				transfers, trip_legs = count_route_transfers(connections_seq, routes_dict)

				wait_time = 0
				for leg_routes in trip_legs:
					
					wait_times_list = [routes_dict[route]['wait_time_mean'] for route in leg_routes]
					if(wait_times_list):
						wait_time = wait_time + min(wait_times_list)/2
					else:
						transfers = -1
			
				if(transfers != -1):

					print("Trip:                                ")
					print("From: " + str(random_lat_1) + "," + str(random_lon_1) + " to: " + str(random_lat_2) + "," + str(random_lon_2))
					print("Time: ")
					print(adjustment_weight*wait_time + sum([connection['travel_time'] for connection in connections_seq]))
					print("Distance: ")
					print(sum([connection['road_length'] for connection in connections_seq]))
					print("Transfers: ")
					print(transfers)
					print("Straight Distance: ")
					print(calculate_straight_distance(stop_1['lat'], stop_1['lon'], stop_2['lat'], stop_2['lon'], radius))
					print(" ")

					trip_time = trip_time + adjustment_weight*wait_time + sum([connection['travel_time'] for connection in connections_seq])
					trip_distance = trip_distance + sum([connection['road_length'] for connection in connections_seq])
					trip_transfers = trip_transfers + transfers
					trip_straight_distance = (trip_straight_distance + 
						calculate_straight_distance(stop_1['lat'], stop_1['lon'], stop_2['lat'], stop_2['lon'], radius))
					x = x + 1
					print("Calculated trip stats for " + str(x + i*sample_size) + "/" + str(sample_size*repetitions), end="\r")

	print("")

	return (trip_time/(sample_size*repetitions),
		trip_distance/(sample_size*repetitions),
		trip_transfers/(sample_size*repetitions),
		trip_straight_distance/(sample_size*repetitions))


def calculate_poi_uniform(G, routes_list, stops_list, connections_list, poi_list, radius, sample_size, repetitions, poi_type):

	cutoff_high_deg = 0.0072	# 800m
	cutoff_low_deg = 0.0036  	# 400m

	lat_list = [float(stop['lat']) for stop in stops_list]
	lon_list = [float(stop['lon']) for stop in stops_list]

	routes_dict = {route['tag']:route for route in routes_list}

	bounding_box = { 'left': min(lon_list) - cutoff_low_deg,
		'right': max(lon_list) + cutoff_low_deg,
		'top': max(lat_list) + cutoff_low_deg,
		'bottom': min(lat_list) - cutoff_low_deg}

	closest_poi_trip_time = 0

	# Average over several seeds
	for i in range(0,repetitions):

		random.seed()
		x=0
		j=0
		while x < sample_size and j < 1000:

			random_lat_1, random_lon_1 = select_random_point_uniform(bounding_box)

			trip_times = []

			for poi in poi_list:

				# Make sure first point is within the service area (within 800m of nearest stop)
				cutoff_square_stops = get_stops_in_square(stops_list, random_lat_1, random_lon_1, cutoff_high_deg)
				while (len(cutoff_square_stops) == 0):
					random_lat_1, random_lon_1 = select_random_point_uniform(bounding_box)
					cutoff_square_stops = get_stops_in_square(stops_list, random_lat_1, random_lon_1, cutoff_high_deg)

				stop_1 = get_closest_stop(random_lat_1, random_lon_1, cutoff_square_stops, radius)

				stop_2 = get_closest_stop(poi['lat'], poi['lon'], stops_list, radius)
				# pprint(stop_2)

				# Find shortest path (forward or backwards)
				try:
					path = nx.shortest_path(G, stop_1['tag'], stop_2['tag'], 'travel_time')
				except nx.NetworkXNoPath:
					path = -1

				# If it exists, get data on it
				if(path != -1):

					connections_seq =  convert_stops_seq_to_connections_seq(path, connections_list)
					transfers, trip_legs = count_route_transfers(connections_seq, routes_dict)

				wait_time = 0
				for leg_routes in trip_legs:
					
					wait_times_list = [routes_dict[route]['wait_time_mean'] for route in leg_routes]
					if(wait_times_list):
						wait_time = wait_time + min(wait_times_list)/2
					else:
						transfers = -1
			
				if(transfers != -1):
						trip_times.append(wait_time + sum([connection['travel_time'] for connection in connections_seq]))

			if(not trip_times):
				closest_poi_trip_time = closest_poi_trip_time + min(trip_times)

				x = x + 1
				print("Calculated trip stats for " + str(x + i*sample_size) + "/" + str(sample_size*repetitions), end="\r")
			j = j + 1

	return closest_poi_trip_time/(sample_size*repetitions)


# ===============================================
# =				Helper Methods		 			=
# ===============================================


def get_stops_in_square(stops_list, random_lat, random_lon, cutoff):

	return [ stop for stop in stops_list if (
			(random_lat < float(stop['lat'])+cutoff and random_lat > float(stop['lat'])-cutoff)
			and (random_lon < float(stop['lon'])+cutoff and random_lon > float(stop['lon'])-cutoff))]


def calculate_close_stops(stops_list, random_lat, random_lon, cutoff_low_deg, radius):

	walk_km = 0.4		# 400m

	close_square_stops = get_stops_in_square(stops_list, random_lat, random_lon, cutoff_low_deg)
	
	close_stops_distances = (
			[calculate_straight_distance(random_lat, random_lon, stop['lat'], stop['lon'], radius) for stop in close_square_stops])

	close_stops_count = len([distance for distance in close_stops_distances if distance < walk_km])

	return close_stops_count, close_stops_distances


def calculate_least_distance(random_lat, random_lon, close_stops_distances, cutoff_square_stops, radius):

	if(close_stops_distances):

		least_distance = min(close_stops_distances)

	else:
		cutoff_stops_distances = (
			[calculate_straight_distance(random_lat, random_lon, stop['lat'], stop['lon'], radius) for stop in cutoff_square_stops])
		least_distance = min(cutoff_stops_distances)

	return least_distance


def get_closest_stop(random_lat, random_lon, cutoff_square_stops, radius):

	stops_distances = (
		[{'distance': calculate_straight_distance(random_lat, random_lon, stop['lat'], stop['lon'], radius), 'stop': stop}
			for stop in cutoff_square_stops])
	least_distance = min([stop['distance'] for stop in stops_distances])

	closest_stop = [stop['stop'] for stop in stops_distances if (stop['distance']==least_distance)][0]
	return closest_stop


def convert_stops_seq_to_connections_seq(stops_seq, connections_list):

	connections_seq = []

	for index in range(0, len(stops_seq) - 1):

		from_stop = stops_seq[index]
		to_stop = stops_seq[index + 1]

		connection = [connection for connection in connections_list
			if (connection['from'] == from_stop and connection['to'] == to_stop)][0]

		connections_seq.append(connection)

	return connections_seq


def count_route_transfers(connections_seq, routes_dict):

	# Adjust the result by 30% due to greedy path bias
	adjustment_weight = 0.7

	# Impossible if empty list
	if(not connections_seq):
		return -1, []

	candidate_routes = [route for route in connections_seq[0]['routes']
		if (route in routes_dict and routes_dict[route]['wait_time_mean'] != -1)]
	last_candidates = []
	final_routes = []
	changes = 0

	for connection in connections_seq:

		new_candidate_routes = []
	
		for candidate_route in candidate_routes:

			# If a route doesn't go all the way to the previous change
			if (candidate_route not in connection['routes']):

				# print(candidate_routes)
				# Remove it from the possible all-the-way routes
				last_candidates.append(candidate_route)
				# candidate_routes.remove(candidate_route)
			else:
				new_candidate_routes.append(candidate_route)

		# if there is no possible route for the last trip leg
		if (not new_candidate_routes):

			# We have a change, remember the routes that were left
			changes = changes + 1
			final_routes.append(last_candidates)
			candidate_routes = [route for route in connection['routes']
				if (route in routes_dict and routes_dict[route]['wait_time_mean'] != -1)]
			last_candidates = list(candidate_routes)

	final_routes.append(last_candidates)

	# Test if route was possible (due to having invalid routes)
	for leg in final_routes:
		if(not leg):
			changes = -1



	return int((changes-1)*adjustment_weight),final_routes


def select_random_point_uniform(bounding_box):

	# Uniformly select a random point within the boundaries
	random_lat = random.uniform(bounding_box['top'], bounding_box['bottom'])
	random_lon = random.uniform(bounding_box['left'], bounding_box['right'])

	return random_lat, random_lon


def select_random_point_population(population_distribution, sectors_list):

	# Select a random sector based on population distribution
	random_sector = random.choices(sectors_list, weights=population_distribution)[0]
	random_square_side = math.sqrt(random_sector['area']) * 0.0045 #degrees

	# Uniformly select a random point within that sector
	random_lat = random.uniform(random_sector['lat'] - random_square_side, random_sector['lat'] + random_square_side)
	random_lon = random.uniform(random_sector['lon'] - random_square_side, random_sector['lon'] + random_square_side)

	return random_lat, random_lon




# ===============================================
# =				Graph Visualization				=
# ===============================================

def draw_static_network(G,stops_list):

	nx.draw_networkx(
		G,
		node_size=0.1,
		with_labels=False
		,edge_color="#AAAAAA"
		,node_color="black"
		,arrows=False
		,pos=convert_stops_to_positions(stops_list))
	# plt.show()



	# print("Bridges:")
	bridges, G2 = get_graph_bridges(G)
	# # print(bridges)
	nx.draw_networkx(G2,node_size=0.1,edge_color="red",with_labels=False,arrows=False,pos=convert_stops_to_positions(stops_list))
	

	# print("Center:")
	# center, G3 = get_graph_center(G)
	# print(center)
	# nx.draw_networkx(G3,node_size=15,node_color="green",with_labels=False,arrows=False,pos=convert_stops_to_positions(stops_list))


	plt.show()
	# plt.savefig("bridges_800", dpi=800)


def get_graph_bridges(G):

	bridges = list(nx.bridges(G))
	non_bridges = [edge for edge in G.edges if edge not in bridges]

	G2 = G.copy()
	G2.remove_edges_from(non_bridges)
	G2.remove_nodes_from(list(nx.isolates(G2)))

	return bridges, G2


def get_graph_center(G):

	center= nx.center(G)
	non_center = [node for node in G.nodes if node not in center]

	G2 = G.copy()
	G2.remove_nodes_from(non_center)

	return center, G2


# ===============================================
if __name__ == "__main__":
    main()
