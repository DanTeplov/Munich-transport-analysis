import os
import pickle
from tqdm import tqdm


def load_all_trips(data_directories):
    """
    Loads all data from the specified directories, ignoring old_trips.pickle files.

    Parameters:
    data_directories (list of str): List of paths to data directories.

    Returns:
    dict: A concatenated dictionary with data from all files.
    """
    all_trips = {}
    
    for directory in data_directories:
        for filename in tqdm(os.listdir(directory)):
            if filename.endswith(".pickle") and filename != "old_trips.pickle":
                filepath = os.path.join(directory, filename)
                try:
                    with open(filepath, 'rb') as file:
                        trips = pickle.load(file)
                        # Data Merging
                        for key, value in trips.items():
                            if key in all_trips:
                                for station, trips_list in value.items():
                                    if station in all_trips[key]:
                                        all_trips[key][station].extend(trips_list)
                                    else:
                                        all_trips[key][station] = trips_list
                            else:
                                all_trips[key] = value
                except Exception as e:
                    print(f"Error loading {filepath}: {e}")
    
    return all_trips

# Data folders
data_folders = ["saved_trips", "From_AWS"]

# Loading all data
all_trips_data = load_all_trips(data_folders)

# Check how many keys were loaded
#print(f"Total number of unique records: {len(all_trips_data)}")


###################################
# 1. Average delay analysis
###################################

import matplotlib.pyplot as plt
from datetime import timedelta


# Parameters
all_transport_types = ['ICE', 'STR', 'Bus', 'U', 'RE', 'NJ', 'BRB', 'EN']
allowed_transport_types = ['STR', 'Bus', 'U']  # Types of transport that interest us
min_record_threshold = 2  # Minimum number of records to include a route in the analysis
delay_threshold = 1  # Minimum delay to be taken into account in charts (in minutes)


# We collect data on delays, flights and cancellations
route_delays = {}
route_total_stops = {} 
route_cancellations = {} 
route_unique_trips = {} 

for route, stations in all_trips_data.items():
    # Check if the route corresponds to the allowed transport
    transport_type = ''.join(filter(str.isalpha, route.split()[0]))  # Extracting the transport prefix
    if transport_type not in allowed_transport_types:
        continue

    unique_trips_set = set()

    # We take the first station of the route to count unique trips
    first_station = next(iter(stations.keys()), None)
    if first_station is None:
        continue

    for trip in stations[first_station]:
        trip_id = trip[1]  # Time is a unique identifier
        unique_trips_set.add(trip_id)

    route_unique_trips[route] = len(unique_trips_set)

    # Collecting data from all stations
    for station, trips in stations.items():
        for trip in trips:
            # Checking if a trip is cancelled
            if trip[2]:
                if route not in route_cancellations:
                    route_cancellations[route] = 0
                route_cancellations[route] += 1
                continue  # Do not include cancelled trips in delays

            # Checking the data format and extracting the delay
            if isinstance(trip[2], timedelta):  # New format with timedelta
                delay = trip[2].total_seconds() / 60 
            elif isinstance(trip[2], bool):  # Format with boolean value
                if isinstance(trip[3], timedelta):  
                    delay = trip[3].total_seconds() / 60 
                elif isinstance(trip[3], (int, float)): # Delay in numeric format
                    delay = trip[3]
                else:
                    continue
            else:
                continue

            # Adding data to route_delays
            if route not in route_delays:
                route_delays[route] = []
                route_total_stops[route] = 0
            route_delays[route].append(delay)
            route_total_stops[route] += 1


# Calculate the average delay, delay frequency and delay percentage
average_delays = {route: sum(route_delays[route]) / route_total_stops[route] for route in route_delays}
filtered_delays = {route: [d for d in route_delays[route] if d > delay_threshold] for route in route_delays}
delay_frequencies = {route: len(filtered_delays[route]) for route in filtered_delays}
delay_percentages = {
    route: (len(filtered_delays[route]) / route_total_stops[route]) * 100 if route_total_stops[route] > 0 else 0
    for route in filtered_delays
}

# Filter routes by the minimum number of trips
filtered_routes = {
    route: avg_delay
    for route, avg_delay in average_delays.items()
    if route_unique_trips.get(route, 0) >= min_record_threshold
}
print(f"Number of routes after filtering: {len(filtered_routes)}")

if filtered_routes:
    # Sort routes by average delay
    sorted_routes = sorted(filtered_routes.items(), key=lambda x: x[1], reverse=True)
    routes = [route for route, _ in sorted_routes[:20]]
    delays = [filtered_routes[route] for route in routes]  # Average delays for top 20 routes


    # Average delay by route graph
    plt.figure(figsize=(14, 8))
    plt.barh(routes, delays, color='steelblue', edgecolor='black')
    for i, route in enumerate(routes):
        plt.text(delays[i], i, f' {route_unique_trips[route]} trips', va='center', fontsize=9, color='black')
    plt.xlabel('Average delay (minutes)', fontsize=12)
    plt.ylabel('Routes', fontsize=12)
    plt.title('Average route delay (top 20)', fontsize=14)
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.show()

    # # Saving a graph to a file instead of displaying it
    # plt.savefig("average_delay_by_route.png")  # Save the graph to a file
else:
    print("No data to plot average delay.")

# Delay frequency graph
sorted_routes_frequency = sorted(delay_frequencies.items(), key=lambda x: x[1], reverse=True)
filtered_frequency_data = [
    (route, freq)
    for route, freq in sorted_routes_frequency
    if route in filtered_routes and freq > 0  # We only consider routes with delays
]

if not filtered_frequency_data:
    print("There is no data to plot the graph.")
else:
    try:
        # Extracting data for the graph
        routes_freq, frequencies = zip(*filtered_frequency_data[:20])  # Top 20 routes 

        plt.figure(figsize=(14, 8))
        plt.barh(routes_freq, frequencies, color='salmon', edgecolor='black')

        for i, route in enumerate(routes_freq):
            # Checking if there is data on unique trips
            unique_trips = route_unique_trips.get(route, 0)
            plt.text(frequencies[i], i, f' {unique_trips} trips', va='center', fontsize=9, color='black')

        plt.xlabel('Number of delays', fontsize=12)
        plt.ylabel('Routes', fontsize=12)
        plt.title('Number of delays by route (top 20)', fontsize=14)
        plt.gca().invert_yaxis()
        plt.tight_layout()

        plt.show()

        # # Saving a graph to a file instead of displaying it
        # plt.savefig("delay_frequency_by_route.png")  # Save the graph to a file
        

    except Exception as e:
        print(f"Error while plotting the graph: {e}")

# Calculating the percentage of delays
delay_percentages = {
    route: (len(filtered_delays[route]) / route_total_stops[route]) * 100 if route_total_stops[route] > 0 else 0
    for route in filtered_delays
}

# for route, delays in route_delays.items():
#     print(f"Маршрут: {route}, общее количество задержек: {len(delays)}")
#     print(f"После фильтра: {len(filtered_delays.get(route, []))}")

# Delay percentage plot
sorted_routes_percentage = sorted(delay_percentages.items(), key=lambda x: x[1], reverse=True)
routes_percent = [route for route, _ in sorted_routes_percentage if route in route_unique_trips][:20] # route_unique_trips to check, if the transport is allowed
percentages = [delay_percentages[route] for route in routes_percent]

plt.figure(figsize=(14, 8))
plt.barh(routes_percent, percentages, color='gold', edgecolor='black')
for i, route in enumerate(routes_percent):
    plt.text(percentages[i], i, f' {route_unique_trips[route]} trips', va='center', fontsize=9, color='black')
plt.xlabel('Delay percentage (%)', fontsize=12)
plt.ylabel('Rotes', fontsize=12)
plt.title('Percentage of delays by routes (top 20)', fontsize=14)
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()

# # Saving a graph to a file instead of displaying it
# plt.savefig("delay_percentage_by_route.png")  # Save the graph to a file

# Cancellation rate chart
sorted_cancellations = sorted(
    [(route, route_cancellations[route] / len(all_trips_data[route])) for route in route_cancellations],
    key=lambda x: x[1],
    reverse=True
)

# Top 20 routes
routes_cancel = [route for route, _ in sorted_cancellations][:20]
cancellations = [cancel_per_station for _, cancel_per_station in sorted_cancellations][:20]

fig, ax = plt.subplots(figsize=(14, 8))
ax.barh(routes_cancel, cancellations, color='tomato', edgecolor='black')

for i, route in enumerate(routes_cancel):
    unique_trips = route_unique_trips.get(route, 0)  # Number of unique routes
    ax.text(cancellations[i], i, f' {unique_trips} trips', va='center', fontsize=9, color='black')

ax.set_xlabel('Number of cancellations', fontsize=12)
ax.set_ylabel('Routes', fontsize=12)
ax.set_title('Number of cancellations by route (top 20)', fontsize=14)
ax.invert_yaxis()
fig.tight_layout()

plt.show()

# # Saving a graph to a file instead of displaying it
# plt.savefig("cancellations_by_route.png")  # Save the graph to a file
# # plt.close(fig)