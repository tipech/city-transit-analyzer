import sys
import networkx as nx
#from networkx.algorithms import approximation
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

	# G = nx.connected_components(G)

	# nx.draw_networkx(G,node_size=0.1,with_labels=False,arrows=False,pos=convert_stops_to_positions(stops_list))
	# plt.show()
	# plt.savefig("network_1200", dpi=800)

	print("Total length:")
	print(sum(connection['straight-distance'] for connection in connections_list))

	print("Average connection length:")
	print(sum(connection['straight-distance'] for connection in connections_list) / len(connections_list))

	print("Average shortest path:")
	print(nx.average_shortest_path_length(G,weight='straight-distance'))

	# print("Center:")
	# print(nx.center(G))

	# print("Connectivity:")
	# print(nx.all_pairs_node_connectivity(G))






# ===============================================
# =				Graph manipulation				=
# ===============================================


# ===============================================
if __name__ == "__main__":
    main()
