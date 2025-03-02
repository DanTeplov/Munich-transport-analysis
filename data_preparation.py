import os
import pickle
from datetime import timedelta, datetime
from tqdm import tqdm

def parse_transport_name(route_name: str) -> str:
    """
    Extracts the transport name from the beginning of route_name.
    Stops when it encounters the first digit.
    Then does additional normalization (BusSEV -> Bus, Str -> STR, etc.).
    """

    route_name = route_name.strip()
    raw = ""
    for char in route_name:
        if char.isdigit():
            # As soon as we meet a number, we stop
            break
        if char.isalpha():
            # We take only letters
            raw += char
    
    # Now raw can be like 'BusSEV', 'STR', 'Ice', 'U', 'Str', 'Bus', ...

    raw_lower = raw.lower()  # for comparison

    # dictionary of "synonyms" or "prefixes"
    if raw_lower.startswith("bus"):
        return "Bus"
    elif raw_lower.startswith("str"):
        return "STR"
    elif raw_lower.startswith("ice"):
        return "ICE"
    elif raw_lower.startswith("u"):
        return "U"
    elif raw_lower.startswith("s"):  
        return "S"
    elif raw_lower.startswith("re"):
        return "RE"
    elif raw_lower.startswith("nj"):
        return "NJ"
    elif raw_lower.startswith("brb"):
        return "BRB"
    elif raw_lower.startswith("en"):
        return "EN"
    else:
        return raw.upper() if raw else "UNKNOWN"


def create_or_load_standardized_data(data_directories, output_file="standardized_data.pickle"):
    """
    If output_file already exists, loads standardized records from it and returns.
    Otherwise, it goes through all .pickle files in data_directories, parses and saves to output_file.
    Returns a list of dictionaries with keys:
    ['route', 'station', 'transport', 'datetime', 'is_canceled', 'delay'].
    """

    if os.path.isfile(output_file):
        print(f"File '{output_file}' already exists. Loading...")
        with open(output_file, "rb") as f:
            standardized_data = pickle.load(f)
        print(f"{len(standardized_data)} standardized records loaded.")
        return standardized_data

    print("File with standardized data not found. Starting parsing source .pickle...")

    from_path_records = []  # We will collect all the records here

    for directory in data_directories:
        if not os.path.isdir(directory):
            print(f"Directory {directory} does not exist, skipping.")
            continue

        for filename in tqdm(os.listdir(directory)):
            if filename.endswith(".pickle") and filename != "old_trips.pickle":
                filepath = os.path.join(directory, filename)

                try:
                    with open(filepath, 'rb') as file:
                        trips_dict = pickle.load(file)
                        # trips_dict format: { route_name: {station_name: [trip_tuple, ...]}, ... }

                        for route_name, stations_info in trips_dict.items():
                            guessed_transport = parse_transport_name(route_name)

                            for station_name, trip_list in stations_info.items():
                                for trip_tuple in trip_list:
                                    if len(trip_tuple) == 4:
                                        trip_transport, trip_datetime, is_canceled, trip_delay_raw = trip_tuple
                                    elif len(trip_tuple) == 3:
                                        trip_transport = guessed_transport
                                        trip_datetime, is_canceled, trip_delay_raw = trip_tuple
                                    else:
                                        # Unknown format
                                        continue

                                    if isinstance(trip_delay_raw, timedelta):
                                        delay_minutes = trip_delay_raw.total_seconds() / 60.0
                                    elif isinstance(trip_delay_raw, (int, float)):
                                        delay_minutes = float(trip_delay_raw)
                                    else:
                                        # Incorrect format
                                        continue

                                    # datetime
                                    if not isinstance(trip_datetime, datetime):
                                        continue

                                    record = {
                                        'route': route_name,
                                        'station': station_name,
                                        'transport': parse_transport_name(trip_transport),
                                        'datetime': trip_datetime,
                                        'is_canceled': bool(is_canceled),
                                        'delay': delay_minutes
                                    }

                                    from_path_records.append(record)

                except Exception as e:
                    print(f"[ERROR] Error while processing {filepath} -> {e}")

    print(f"Total {len(from_path_records)} records received.")

    # Save to file
    with open(output_file, "wb") as f_out:
        pickle.dump(from_path_records, f_out)

    print(f"Standardized data is stored in '{output_file}'.")
    return from_path_records


def filter_data_by_transport_and_min_trips(
    standardized_data,
    allowed_transport_types, 
    min_record_threshold=2
):
    """
    Filters standardized records by the list of permitted transport types
    and the minimum number of unique trips:
    - take the first "first station" of the route,
    - count unique datetimes there,
    - if it is less than min_record_threshold -> we throw out the entire route).
    Returns the filtered list.
    """

    
    from collections import OrderedDict
    routes_map = {}  # { route_name: OrderedDict(station_name -> set_of_datetimes) }

    for rec in standardized_data:
        route_name = rec['route']
        st_name = rec['station']
        dt = rec['datetime']
        tr = rec['transport']

        if tr not in allowed_transport_types:
            continue

        if route_name not in routes_map:
            routes_map[route_name] = OrderedDict()
        if st_name not in routes_map[route_name]:
            routes_map[route_name][st_name] = set()
        routes_map[route_name][st_name].add(dt)

   
    valid_routes = set()

    for route_name, stations_dict in routes_map.items():
        # We take the first station (in order of addition)
        if not stations_dict:
            continue
        first_station = next(iter(stations_dict))
        unique_datetimes_count = len(stations_dict[first_station])

        if unique_datetimes_count >= min_record_threshold:
            valid_routes.add(route_name)

    # Now collect the final list of records from standardized_data,
    # leaving only those with a route in valid_routes.
    filtered_records = [r for r in standardized_data if r['route'] in valid_routes
                        and r['transport'] in allowed_transport_types]

    return filtered_records



