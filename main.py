#import mvg_api as mvg
#print(mvg.get_id_for_station("Hauptbahnhof"))

import datetime
from pyhafas.types.nearby import LatLng
import pyhafas.types.fptf
from pyhafas import HafasClient
from pyhafas.profile import DBProfile
import numpy as np
from tqdm import tqdm
import pickle
import time

client = HafasClient(DBProfile())

# Find all stations in Munich
# Year_delay = 0
# Month_delay = 0
# Day_delay = 0

# start_datetime = datetime.date.today().replace(year=datetime.date.today().year-Year_delay)
# start_datetime = datetime.datetime(year=start_datetime.year, month=start_datetime.month-Month_delay, day=start_datetime.day-Day_delay, hour=5, minute=0)


def get_all_stations_in_radius_13(location=LatLng(48.140364, 11.558744)):
    stations_5km = np.array([[station.id, station.name, station.latitude, station.longitude] \
                        for station in client.nearby(location=location, max_walking_distance=5000)])
    stations_5_8km = np.array([[station.id, station.name, station.latitude, station.longitude] \
                        for station in client.nearby(location=location, min_walking_distance=5001, max_walking_distance=8000)])
    stations_8_11km = np.array([[station.id, station.name, station.latitude, station.longitude] \
                        for station in client.nearby(location=location, min_walking_distance=8001, max_walking_distance=11000)])
    stations_11_13km = np.array([[station.id, station.name, station.latitude, station.longitude] \
                        for station in client.nearby(location=location, min_walking_distance=11001, max_walking_distance=13000)])
    all_stations = np.row_stack([stations_5km, stations_5_8km, stations_8_11km, stations_11_13km])
    
    return all_stations

def get_last_saved_trips(station_id, timedelta=datetime.timedelta(minutes=15)):
    # The delay of departure is saved for only 15 Minutes
    departures = client.departures(
        station=station_id,
        date=datetime.datetime.now() - timedelta,
        duration=timedelta.total_seconds()/60,
        products={
            'long_distance_express': True,
            'regional_express': True,
            'regional': True,
            'suburban': True,
            'bus': True,
            'ferry': False,
            'subway': True,
            'tram': True,
            'taxi': False
        }
    )
    #print(departures[0:10])
    return departures

def get_new_trips(stations, start_datetime, old_trips):
    trips = {}
    number_trips_saved = 0
    for st in tqdm(stations):
        duration_time = (datetime.datetime.now() - start_datetime)
        new_st_trips = get_last_saved_trips(station_id=st[0], timedelta=duration_time)
        for trip in new_st_trips:
            trip_key = (trip.name if trip.name is not None else "Undefined") + " nach " + (trip.direction if trip.direction is not None else "Undefined")

            # Get the time of this type of trip in old_trips:
            old_time = None
            if trip_key in old_trips:
                if trip.station.name in old_trips[trip_key]:
                    old_time = old_trips[trip_key][trip.station.name][-1][1]

            # If we already saved later trip, it means that current trip is not new and we don't need to save it
            if (old_time is None) or ((old_time is not None) and trip.dateTime > old_time):

                # Now save this trip in according place in trips dictionary
                if trip_key in trips:
                    if trip.station.name in trips[trip_key]:
                        trips[trip_key][trip.station.name].append((trip_key.split(" ")[0], trip.dateTime, trip.cancelled, trip.delay if trip.delay is not None else 0))
                    else: 
                        trips[trip_key][trip.station.name] = [(trip_key.split(" ")[0], trip.dateTime, trip.cancelled, trip.delay if trip.delay is not None else 0)]
                else: 
                    trips[trip_key] = {trip.station.name: [(trip_key.split(" ")[0], trip.dateTime, trip.cancelled, trip.delay if trip.delay is not None else 0)]}
                number_trips_saved += 1    
    return trips, number_trips_saved


all_stations_in_Munich = get_all_stations_in_radius_13()
print(all_stations_in_Munich.shape)

terminate = False
try:
    with open(f'Saved trips\old_trips.pickle', 'rb') as file:
        old_trips = pickle.load(file)
        print("old_trips.pickle file found")
except: 
    old_trips = {}
    print("old_trips.pickle file not found")

while not terminate:
    new_trips, number_trips_saved = get_new_trips(all_stations_in_Munich, datetime.datetime.now() - datetime.timedelta(minutes=15), old_trips=old_trips)
    with open(f'Saved trips/saved_trips_{datetime.datetime.now().year}_{datetime.datetime.now().month}_' \
              + f'{datetime.datetime.now().day}_{datetime.datetime.now().hour}_' \
              + f'{datetime.datetime.now().minute}.pickle', 'wb') as file:
        pickle.dump(new_trips, file, protocol=pickle.HIGHEST_PROTOCOL)
    
    with open(f'Saved trips/old_trips.pickle', 'wb') as file:
        pickle.dump(new_trips, file, protocol=pickle.HIGHEST_PROTOCOL)

    old_trips = new_trips
    print(f"Saved {number_trips_saved} trips")
    time.sleep(600)

#print(new_trips)
