import os, sys, math


cities = {
	'toronto':{
		'tag':"ttc",
		'area': 630,
		'radius': 6368.262,
		'apis':{
			'ttc': {
				'base':"http://webservices.nextbus.com/service/publicXMLFeed?a=ttc&command=",
				'route':"&r=",
				'commands':{
					'route_list':"routeList",
					'route_data':"routeConfig",
					'predictions':"predictionsForMultiStops"
				}
			}
		}
	},
	'la':{
		'tag':"lametro",
		'area': 1214,
		'radius': 6371.57,
		'apis':{
			'lametro': {
				'base':"http://webservices.nextbus.com/service/publicXMLFeed?a=lametro&command=",
				'route':"&r=",
				'commands':{
					'route_list':"routeList",
					'route_data':"routeConfig",
					'predictions':"predictionsForMultiStops"
				}
			}
		}
	},
	'sf':{
		'tag':"sf-muni",
		'area': 121,
		'radius': 6370.158,
		'apis':{
			'sf-muni': {
				'base':"http://webservices.nextbus.com/service/publicXMLFeed?a=sf-muni&command=",
				'route':"&r=",
				'commands':{
					'route_list':"routeList",
					'route_data':"routeConfig",
					'predictions':"predictionsForMultiStops"
				}
			}
		}
	}
 }




# ===============================================
# =					Helper Methods				=
# ===============================================

def calculate_straight_distance(stop_1_lat, stop_1_lon, stop_2_lat, stop_2_lon, radius):

	rad_pi = math.pi/180

	lat_1 = float(stop_1_lat) * rad_pi
	lon_1 = float(stop_1_lon) * rad_pi

	lat_2 = float(stop_2_lat) * rad_pi
	lon_2 = float(stop_2_lon) * rad_pi

	dlon = lon_2 - lon_1
	dlat = lat_2 - lat_1

	a = ((math.sin(dlat/2))**2) + (math.cos(lat_1) * math.cos(lat_2) * ((math.sin(dlon/2))**2))
	c = 2 * math.atan2(math.sqrt(a),  math.sqrt(1-a))
	d = radius * c

	return d



# ===============================================
# =					File IO 					=
# ===============================================

def create_agencies_folder(directory):
	"""Creates a folder for this city if one doesn't already exist."""

	if not os.path.isdir(directory):
		os.makedirs(directory)


def read_routes_file(directory):
	"""Opens routes file and reads contents into a list."""

	# read the file and split the rows into a list
	try:
		routes_file = open(directory + "/routes.csv","r+")
	except FileNotFoundError:
		print("Error: Routes file missing for this city!")
		sys.exit()

	routes_list_csv = routes_file.read().split("\n")
	routes_file.close()

	# split every row into a route entry by applying read_route_entry
	routes_map = map(read_route_entry, routes_list_csv)
	# filter out first (header) and last (empty) lines
	routes_list = list(filter(lambda x: x != None, routes_map))

	return routes_list


def read_stops_file(directory):
	"""Opens stops file and reads contents into a list."""

	# read the file and split the rows into a list
	try:
		stops_file = open(directory + "/stops.csv","r+")
	except FileNotFoundError:
		print("Error: Stops file missing for this city!")
		sys.exit()

	stops_list_csv = stops_file.read().split("\n")
	stops_file.close()

	# split every row into a stop entry by applying read_stop_entry
	stops_map = map(read_stop_entry, stops_list_csv)
	# filter out first (header) and last (empty) lines
	stops_list = list(filter(lambda x: x != None, stops_map))

	return stops_list



def read_demographics_file(directory):
	"""Opens demographics file and reads contents into a list."""

	# read the file and split the rows into a list
	try:
		demographics_file = open(directory + "/demographics.csv","r+")
	except FileNotFoundError:
		print("Error: Demographics file missing for this city!")
		sys.exit()

	sectors_list_csv = demographics_file.read().split("\n")
	demographics_file.close()

	# split every row into a sector entry by applying read_sector_entry
	sectors_map = map(read_sector_entry, sectors_list_csv)
	# filter out first (header) and last (empty) lines
	sectors_list = list(filter(lambda x: x != None, sectors_map))

	return sectors_list


def read_connections_file(directory):
	"""Opens connections file and reads contents into a list."""

	# read the file and split the rows into a list
	try:
		connections_file = open(directory + "/connections.csv","r+")
	except FileNotFoundError:
		print("Error: Connections file missing for this city!")
		sys.exit()

	connections_list_csv = connections_file.read().split("\n")
	connections_file.close()

	# split every row into a connection entry by applying read_connection_entry
	connections_map = map(read_connection_entry, connections_list_csv)
	# filter out first (header) and last (empty) lines
	connections_list = list(filter(lambda x: x != None, connections_map))

	return connections_list
	
	
def read_route_entry(route_text):
	"""Parses a route entry from comma-separated to dictionary form."""
	
	# split comma-separated values
	route_list = route_text.split(",")

	# handle invalid lines
	if len(route_list) > 1 and route_list[0] != "tag":
		return {
			"tag": route_list[0],
			"api": route_list[1],
			"stops_count": int(route_list[2]),
			"wait_time_mean": float(route_list[3]),
			"wait_time_std": float(route_list[4])}
	else:
		return None

	
def read_stop_entry(stop_text):
	"""Parses a stop entry from comma-separated to dictionary form."""
	
	# split comma-separated values
	stop_list = stop_text.split(",")

	# handle invalid lines
	if len(stop_list) > 1 and stop_list[0] != "tag":
		return {
			"tag": stop_list[0],
			"title": stop_list[1],
			"lat": stop_list[2],
			"lon": stop_list[3],
			"merged": stop_list[4].split("|")}
	else:
		return None
	
	
def read_sector_entry(sector_text):
	"""Parses a sector entry from comma-separated to dictionary form."""
	
	# split comma-separated values
	sector_list = sector_text.split(",")

	# handle invalid lines
	if len(sector_list) > 1 and sector_list[1] != "lat":
		return {"id": sector_list[0],
			"lat": float(sector_list[1]),
			"lon": float(sector_list[2]),
			"population": int(sector_list[3]),
			"area": float(sector_list[4]),
			"density": float(sector_list[5])}
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
			"length": float(connection_list[3]),
			"road_length": float(connection_list[4]),
			"travel_time": float(connection_list[5])}
	else:
		return None


def write_routes_file(directory, routes_list):
	"""Creates a new or empties the existing routes file and fills it with the list of routes."""

	# (Re)create empty routes file
	create_agencies_folder(directory)
	routes_file = open(directory + "/routes.csv", "w+")

	# Write routes file
	routes_file.write("tag,api,stops_count,wait_time_mean,wait_time_std\n")
	for route in routes_list:
		routes_file.write(
			  route['tag'] + ","
			+ route['api'] + ","
			+ str(route['stops_count']) + ","
			+ str(route['wait_time_mean']) + ","
			+ str(route['wait_time_std']) + "\n" )

	# Close the file
	routes_file.close()


def write_stops_file(directory, stops_list):
	"""Creates a new or empties the existing stops file and fills it with the list of stops."""

	# (Re)create empty stops file
	create_agencies_folder(directory)
	stops_file = open(directory + "/stops.csv", "w+")

	# Write stops file
	stops_file.write("tag,title,lat,lon,merged\n")
	for stop in stops_list:
		stops_file.write(
			  stop['tag'] + ","
			+ stop['title'] + ","
			+ str(stop['lat']) + ","
			+ str(stop['lon']) + ","
			+ '|'.join(stop['merged']) + "\n" )

	# Close the file
	stops_file.close()


def write_connections_file(directory, connections_list):
	"""Creates a new or empties the existing connections file and fills it with the list of connections with distances."""

	# (Re)create empty connections file
	connections_file = open(directory + "/connections.csv", "w+")

	# Write connections file
	connections_file.write("from,to,routes,length,road_length,road_length\n")
	for connection in connections_list:
		connections_file.write(
			  connection['from'] + ","
			+ connection['to'] + ","
			+ '|'.join(connection['routes']) + ","
			+ str(connection['length']) + ","
			+ str(connection['road_length']) + ","
			+ str(connection['travel_time'])
			+ "\n" )

	# Close the file
	connections_file.close()


# ===============================================
# =				Graph manipulation				=
# ===============================================

def convert_stops_to_tuples(stops_list):
	"""Convert the list of stops from list to tuple format."""

	map_func = lambda x: (x['tag'], {'title':x['title'], 'lat':x['lat'], 'lon':x['lon'], 'merged':x['merged']} )

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

	map_func = lambda x: (x['from'], x['to'], {'routes':x['routes'], 'length': x['length']} )

	return list(map(map_func, connections_list))



