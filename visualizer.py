import sys
import networkx as nx
import matplotlib.pyplot as plt
from pprint import pprint

from common import *



def main():
	"""Execute the main actions of the network visualizer program

	Arguments:
		static - draw the static network

		agency,agency_2,... - the transit agency for which we want to retrieve routes

	"""

	# With the "static" argument, create images of the static network
	if len(sys.argv) > 2 and (sys.argv[1] == "static" or sys.argv[1] == "-s" ):

		draw_static_network(sys.argv[2])

	# With wrong arguments, print usage help message
	else:
		print("Usage: visualizer <static|...> <agency>[,<agency_2>,...]")

		

# ===============================================
# =			Static Network Visualization 		=
# ===============================================

def draw_static_network(directory):
	"""Draw an image for the pre-built static network of the transport system."""

	# Read the network files
	stops_list = read_stops_file(directory)
	connections_list = read_connections_file(directory)

	# Build the graph object, add stops and connections
	G = nx.Graph()
	G.add_nodes_from(convert_stops_to_tuples(stops_list))
	G.add_edges_from(convert_connections_to_tuples(connections_list))

	# remove isolated nodes that are in no connections
	G.remove_nodes_from(list(nx.isolates(G)))



	# result = nx.k_components(G)
	# print(len(G.node))

	# print(len(result[1]))

	# pprint(convert_stops_to_positions(stops_list))
	# convert_stops_to_positions(stops_list)

	nx.draw_networkx(G,node_size=0.1,with_labels=False,arrows=False,pos=convert_stops_to_positions(stops_list))
	plt.show()


	# for subgraph in result[1]:
	# 	G2 = G.subgraph(subgraph)

	# 	nx.draw_networkx(G2,node_size=2,with_labels=False,arrows=False,pos=convert_stops_to_positions(stops_list))
	# 	plt.show()

	# print(list(nx.isolates(G)))

	# H = nx.petersen_graph()

	# pprint(stops_list)



# ===============================================
# =				Graph manipulation				=
# ===============================================

def convert_stops_to_tuples(stops_list):
	"""Convert the list of stops from list to tuple format."""

	map_func = lambda x: (x['tag'], {'title':x['title'], 'lat':x['lat'], 'lon':x['lon']} )

	return list(map(map_func, stops_list))


def convert_stops_to_positions(stops_list):
	"""Convert the list of stops from list to dictionary of stops:positions format."""

	map_func = lambda x: (x['tag'], float(x['lat']), float(x['lon']) )
	stops_matrix = list(map(map_func, stops_list))

	transposed_stops_list = list(zip(*stops_matrix))

	min_lat = min(transposed_stops_list[1])
	max_lat = max(transposed_stops_list[1])
	min_lon = min(transposed_stops_list[2])
	max_lon = max(transposed_stops_list[2])
	scale_lat = 1/ (max_lat - min_lat)
	scale_lon = 1/ (max_lon - min_lon)

	scale_func = lambda x: (x[0], ( (x[2] - min_lat) * scale_lat, (x[1] - min_lon) * scale_lon))
	
	return dict(map(scale_func, stops_matrix))


def convert_connections_to_tuples(connections_list):
	"""Convert the list of connections from list to tuple format."""

	map_func = lambda x: (x['from'], x['to'], {'routes':x['routes']} )

	return list(map(map_func, connections_list))




# ===============================================
if __name__ == "__main__":
    main()