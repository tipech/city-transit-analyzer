import sys
import networkx as nx
from pprint import pprint



def main():
	"""Execute the main actions of the network visualizer program

	Arguments:
		static - draw the static network

	"""

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
	stops_list = read_stops_file()
	connections_list = read_connections_file()

	pprint(stops_list)



# ===============================================
# =					File IO 					=
# ===============================================\

def create_agency_folder(agency):
	"""Creates a folder for this agency if one doesn't already exist."""

	if not os.path.isdir(agency):
		os.makedirs(agency)


def read_stops_file(agency):
	"""Opens stops file and reads contents into a list."""

	# read the file and split the rows into a list
	try:
		stops_file = open(agency + "/stops.csv","r+")
	except FileNotFoundError:
		print("Error: Stops file missing for this agency!")
		sys.exit()

	stops_list_csv = stops_file.read().split("\n")
	stops_file.close()

	# split every row into a stop entry by applying read_stop_entry
	stops_map = map(read_stop_entry, stops_list_csv)
	# filter out first (header) and last (empty) lines
	stops_list = list(filter(lambda x: x != None, stops_map))

	return stops_list


def read_connections_file(agency):
	"""Opens connections file and reads contents into a list."""

	# read the file and split the rows into a list
	try:
		connections_file = open(agency + "/connections.csv","r+")
	except FileNotFoundError:
		print("Error: Connections file missing for this agency!")
		sys.exit()

	connections_list_csv = connections_file.read().split("\n")
	connections_file.close()

	# split every row into a connection entry by applying read_connection_entry
	connections_map = map(read_connection_entry, connections_list_csv)
	# filter out first (header) and last (empty) lines
	connections_list = list(filter(lambda x: x != None, connections_map))

	return connections_list
	
	
def read_stop_entry(stop_text):
	"""Parses a stop entry from comma-separated to dictionary form."""
	
	# split comma-separated values
	stop_list = stop_text.split(",")

	# handle invalid lines
	if len(stop_list) > 1 and stop_list[0] != "tag":
		return {"tag": stop_list[0], "title": stop_list[1], "lat": stop_list[2], "lon": stop_list[3]}
	else:
		return None
	
	
def read_connection_entry(connection_text):
	"""Parses a connection entry from comma-separated to dictionary form."""
	
	# split comma-separated values
	connection_list = connection_text.split(",")

	# handle invalid lines
	if len(connection_list) > 1 and connection_list[0] != "from":
		return {"from": connection_list[0], "to": connection_list[1], "routes": connection_list[2].split("|")}
	else:
		return None



# ===============================================
if __name__ == "__main__":
    main()