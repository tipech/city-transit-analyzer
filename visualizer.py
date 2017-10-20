import sys
import networkx as nx



def main():
	"""Execute the main actions of the program"""

	# With the "static" argument, create images of the static network
	if(len(sys.argv) > 1 and sys.argv[1] == "static"):

		draw_static_network()
		

	close_files()


# ===============================================
# =			Static Network Visualization 		=
# ===============================================

def draw_static_network():
	"""Draw an image for the pre-built static network of the transport system"""

	# Read the network files
	stops_file, connections_file = open_files()




# ===============================================
# =					File IO 					=
# ===============================================

def open_files():
	"""Opens network files for reading."""

	global stops_file
	global connections_file
	stops_file = open("stops.csv","r+")
	connections_file = open("connections.csv","r+")

	return stops_file, connections_file
	

def close_files():
	"""Closes network files."""

	global stops_file
	global connections_file
	stops_file.close()
	connections_file.close()



# ===============================================
if __name__ == "__main__":
    main()