import os, sys

# ===============================================
# =					File IO 					=
# ===============================================

def create_agencies_folder(directory):
	"""Creates a folder for these agencies if one doesn't already exist."""

	if not os.path.isdir(directory):
		os.makedirs(directory)


def read_stops_file(directory):
	"""Opens stops file and reads contents into a list."""

	# read the file and split the rows into a list
	try:
		stops_file = open(directory + "/stops.csv","r+")
	except FileNotFoundError:
		print("Error: Stops file missing for these agencies!")
		sys.exit()

	stops_list_csv = stops_file.read().split("\n")
	stops_file.close()

	# split every row into a stop entry by applying read_stop_entry
	stops_map = map(read_stop_entry, stops_list_csv)
	# filter out first (header) and last (empty) lines
	stops_list = list(filter(lambda x: x != None, stops_map))

	return stops_list


def read_connections_file(directory):
	"""Opens connections file and reads contents into a list."""

	# read the file and split the rows into a list
	try:
		connections_file = open(directory + "/connections.csv","r+")
	except FileNotFoundError:
		print("Error: Connections file missing for these agencies!")
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
		return {
			"from": connection_list[0],
			"to": connection_list[1],
			"routes": connection_list[2].split("|"),
			"straight-distance": float(connection_list[3]),
			"road-distance": float(connection_list[4])}
	else:
		return None


def write_stops_file(directory, stops_list):
	"""Creates a new or empties the existing stops file and fills it with the list of stops."""

	# (Re)create empty stops file
	create_agencies_folder(directory)
	stops_file = open(directory + "/stops.csv", "w+")

	# Write stops file
	stops_file.write("tag,title,lat,lon\n")
	for stop in stops_list:
		stops_file.write(
			  stop['tag'] + ","
			+ stop['title'] + ","
			+ str(stop['lat']) + ","
			+ str(stop['lon']) + "\n" )

	# Close the file
	stops_file.close()


def write_connections_file(directory, connections_list):
	"""Creates a new or empties the existing connections file and fills it with the list of connections with distances."""

	# (Re)create empty connections file
	connections_file = open(directory + "/connections.csv", "w+")

	# Write connections file
	connections_file.write("from,to,routes,straight-distance,road-distance\n")
	for connection in connections_list:
		connections_file.write(
			  connection['from'] + ","
			+ connection['to'] + ","
			+ '|'.join(connection['routes']) + ","
			+ str(connection['straight-distance']) + ","
			+ str(connection['road-distance'])
			+ "\n" )

	# Close the file
	connections_file.close()


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

	map_func = lambda x: (x['from'], x['to'], {'routes':x['routes'], 'straight-distance': x['straight-distance']} )

	return list(map(map_func, connections_list))



