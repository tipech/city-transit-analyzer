import requests
import xml.etree.ElementTree as ET

agency = "ttc"
agency_API_base = "http://webservices.nextbus.com/service/publicXMLFeed?command="



# Get the list of routes for this agency
command = "routeList"
request_final = agency_API_base + command + '&a=' + agency

routes_response = requests.get(request_final)
routes_tree = ET.fromstring(routes_response.text)
# we are only interested in the route tags
routes_map = map((lambda x: x.attrib["tag"]), routes_tree)

# Now we have the list of routes, get the list of stops for each one
command = "routeConfig"

routes_list = list(routes_map)[:2] # DEBUG

for route in routes_list:
	# print(route) # DEBUG

	request_final = agency_API_base + command + '&a=' + agency + '&r=' + route

	stops_response = requests.get(request_final)
	stops_tree = ET.fromstring(stops_response.text)
	# we are only interested in the stops
	stops_map = filter((lambda x: x.tag=="stop"), stops_tree[0])
	stops_map = map((lambda x: x.attrib), stops_map)
	print(list(stops_map))
	# print(stops_tree[0][1])