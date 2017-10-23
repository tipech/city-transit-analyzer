import sys
import networkx as nx
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

	G = nx.Graph()
	G.add_nodes_from(convert_stops_to_tuples(stops_list))
	G.add_edges_from(convert_connections_to_tuples(connections_list))

	# pprint(stops_list)



# ===============================================
# =				Graph manipulation				=
# ===============================================

def convert_stops_to_tuples(stops_list):
	"""Convert the list of stops from list to tuple format."""

	map_func = lambda x: (x['tag'], {'title':x['title'], 'lat':x['lat'], 'lon':x['lon']} )

	return list(map(map_func, stops_list))


def convert_connections_to_tuples(connections_list):
	"""Convert the list of connections from list to tuple format."""

	map_func = lambda x: (x['from'], x['to'], {'routes':x['routes']} )

	return list(map(map_func, connections_list))
	



# ===============================================
if __name__ == "__main__":
    main()