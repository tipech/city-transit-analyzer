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

	# With the "static" argument, create images of the static network
	if len(sys.argv) > 2 and (sys.argv[1] == "static" or sys.argv[1] == "-s" ):

		metrics = []

		for city in sys.argv[2].split(" "):

			# Read the network files
			routes_list = read_routes_file(cities[city]['tag'])
			stops_list = read_stops_file(cities[city]['tag'])
			connections_list = read_connections_file(cities[city]['tag'])

			G = create_undirected_network(stops_list, connections_list)

			# draw_static_network(G,stops_list)
			
			city_metrics = calculate_city_metrics(G, routes_list, stops_list, connections_list, city)
			metrics.append(city + "," + ",".join(str(value) for value in city_metrics.values()))

			print("Calculated metrics for: " + city + "                    ")


		metrics = ["city," + ",".join(str(value) for value in city_metrics.keys())] + metrics
		print("\n" + "\n".join(metrics) + "\n")

	# With wrong arguments, print usage help message
	else:
		print("Usage: visualizer <static|...> <city>[,<city_2>,...]")

		

def create_undirected_network(stops_list, connections_list):
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

def calculate_city_metrics(G, routes_list, stops_list, connections_list, city):

	# Area and earth radius presets
	radius = cities[city]['radius']
	area = cities[city]['area']

	repetitions = 1
	sample_size = 100

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

	metrics['connection_speed_average'] = metrics['total_length']/metrics['total_travel_time']

	metrics['wait_time_average'] = numpy.mean([route['wait_time_mean'] for route in routes_list])
	metrics['wait_time_std'] = numpy.std([route['wait_time_mean'] for route in routes_list])


	# ------------- Shortest Times --------------
	metrics['average_trip'] = calculate_trip(G, stops_list, radius, sample_size, repetitions)


	# --------- Shortest Paths & Detour ---------
	# metrics['average_shortest_path'] = nx.average_shortest_path_length(G,weight='length')
	# metrics['average_straight_distance'] = calculate_average_straight_distance(G, stops_list, radius)
	# metrics['average_detour_normalized'] = ((metrics['average_shortest_path']-metrics['average_straight_distance'])
	# 	/metrics['average_straight_distance'])

	# ------------- Shortest Times --------------
	# metrics['average']
	# metrics['average_trip_time'], metrics['average_trip_changes'],  = nx.average_shortest_path_length(G,weight='length')


	# ----------------- Coverage ----------------
	sectors_list = read_demographics_file(cities[city]['tag'])
	metrics['area_coverage_stops'], metrics['area_coverage_distance'] = (
		calculate_area_coverage(stops_list, radius, sample_size, repetitions))
	metrics['population_coverage_stops'], metrics['population_coverage_distance'] = (
		calculate_population_coverage(stops_list, sectors_list, radius, sample_size, repetitions))


	# -------- Clustering & Connectivity --------
	# metrics['average_clustering'] = nx.average_clustering(G,weight='length')

	# metrics['degree_connectivity'] = nx.average_degree_connectivity(G,weight='length')

	return metrics


def calculate_average_straight_distance(G, stops_list, radius):

	sum = 0

	for i in range(0,len(stops_list)):
		for j in range(i+1,len(stops_list)):

			stop_1 = stops_list[i]
			stop_2 = stops_list[j]

			if stop_1 != stop_2:
				distance = calculate_straight_distance(stop_1['lat'], stop_1['lon'], stop_2['lat'], stop_2['lon'], radius)
				sum = sum + distance
		
		print("Calculated distances for " + str( i + 1 ) + "/" + str(len(G.nodes)) + " stops", end="\r")
	
	return 2*sum/(len(G.nodes)*(len(G.nodes)-1))


def calculate_area_coverage(stops_list, radius, sample_size, repetitions):

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
			least_distance = calculate_least_distance(random_lat, random_lon, close_stops_distances, cutoff_square_stops, radius)

			close_stops = close_stops + close_stops_count
			least_distance = least_distance + least_distance
			print("Calculated area coverage for " + str(x*repetitions) + "/" + str(sample_size*repetitions), end="\r")

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
			least_distance = calculate_least_distance(random_lat, random_lon, close_stops_distances, cutoff_square_stops, radius)

			close_stops = close_stops + close_stops_count
			least_distance = least_distance + least_distance
			print("Calculated area coverage for " + str(x*repetitions) + "/" + str(sample_size*repetitions), end="\r")

	return close_stops/(sample_size*repetitions), least_distance/(sample_size*repetitions)


def calculate_trip(G, stops_list, radius, sample_size, repetitions):

	cutoff_high_deg = 0.0072	# 800m
	cutoff_low_deg = 0.0036  	# 400m

	lat_list = [float(stop['lat']) for stop in stops_list]
	lon_list = [float(stop['lon']) for stop in stops_list]

	bounding_box = { 'left': min(lon_list) - cutoff_low_deg,
		'right': max(lon_list) + cutoff_low_deg,
		'top': max(lat_list) + cutoff_low_deg,
		'bottom': min(lat_list) - cutoff_low_deg}

	trip_time = 0
	trip_distance = 0
	trip_changes = 0

	# Average over several seeds
	for i in range(0,repetitions):

		random.seed()
		for x in range(0,sample_size):

			random_lat_1, random_lon_1 = select_random_point_uniform(bounding_box)
			random_lat_2, random_lon_2 = select_random_point_uniform(bounding_box)

			# Make sure first point is within the service area (within 800m of nearest stop)
			cutoff_square_stops = get_stops_in_square(stops_list, random_lat_1, random_lon_1, cutoff_high_deg)
			while (len(cutoff_square_stops) == 0):
				random_lat_1, random_lon_1 = select_random_point_uniform(bounding_box)
				cutoff_square_stops = get_stops_in_square(stops_list, random_lat_1, random_lon_1, cutoff_high_deg)

			# Make sure second point is within the service area (within 800m of nearest stop)
			cutoff_square_stops = get_stops_in_square(stops_list, random_lat_2, random_lon_2, cutoff_high_deg)
			while (len(cutoff_square_stops) == 0):
				random_lat_2, random_lon_2 = select_random_point_uniform(bounding_box)
				cutoff_square_stops = get_stops_in_square(stops_list, random_lat_2, random_lon_2, cutoff_high_deg)

			# Calculate trip time
			nx.shortest_path(G,)

			trip_time = trip_time + 1
			trip_distance = trip_distance + 1
			trip_changes = trip_changes + 1
			print("Calculated trip stats for " + str(x*repetitions) + "/" + str(sample_size*repetitions), end="\r")

	return trip_time/(sample_size*repetitions), trip_distance/(sample_size*repetitions), trip_changes/(sample_size*repetitions)


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

	stop[''] for 





# ===============================================
# =				Helper Methods		 			=
# ===============================================


def count_route_changes(connections_seq):

	candidate_routes = [route for route in connections_seq[0]['routes'] if route['wait_time_mean'] != -1]
	last_candidates = []
	final_routes = []
	changes = 0

	for connection in connections_seq:

		for candidate_route in candidate_routes:

			# If a route doesn't go all the way to the previous change
			if (candidate_route not in connection['routes']):

				# Remove it from the possible all-the-way routes
				last_candidates.append(candidate_route)
				candidate_routes.remove(candidate_route)

		# if there is no possible route for the last trip leg
		if (not candidate_routes):

			# We have a change, remember the routes that were left
			changes = changes + 1
			final_routes.append(last_candidates)
			candidate_routes = [route for route in connection['routes'] if route['wait_time_mean'] != -1]
			last_candidates = candidate_routes

	final_routes.append(last_candidates)

	return changes,final_routes


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
