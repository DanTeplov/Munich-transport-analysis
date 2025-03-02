from data_preparation  import (
    create_or_load_standardized_data,
    filter_data_by_transport_and_min_trips,
)

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

data_folders = ["Saved trips", "From_AWS"]
standardized_data_file = "standardized_data.pickle"

standardized_data = create_or_load_standardized_data(data_folders, standardized_data_file)

all_transport_types = ['ICE', 'STR', 'Bus', 'U', 'RE', 'NJ', 'BRB', 'EN']
allowed_transports = ["STR", "Bus", "U"] # Types of transport that interest us
min_record_threshold = 3  # Minimum number of records to include a route in the analysis


# 3) Filtering
filtered_data = filter_data_by_transport_and_min_trips(standardized_data, allowed_transports, min_record_threshold)
print(f"After filtering, there are {len(filtered_data)} records left")


def analyze_delays_by_time_of_day_for_each_transport(standardized_data):
    """
    For each type of transport construct a separate graph of average delay by hours of the day.
    """
    df = pd.DataFrame(standardized_data)
    df = df[df["is_canceled"] == False]  # To analyze only the uncancelled trips

    # Add an hour
    df["hour_of_day"] = df["datetime"].dt.hour

    transports = df["transport"].unique()
    for t in transports:
        df_t = df[df["transport"] == t].copy()
        if df_t.empty:
            continue

        # Группируем по часу
        hour_group = df_t.groupby("hour_of_day")["delay"].mean().reset_index()

        plt.figure(figsize=(8, 5))
        plt.bar(hour_group["hour_of_day"], hour_group["delay"], 
                color='skyblue', edgecolor='black')
        plt.xlabel("Time of day", fontsize=12)
        plt.ylabel("Average delay(min.)", fontsize=12)
        plt.title(f"{t}: Average delay by hours of the day", fontsize=14)
        plt.xticks(range(0, 24))
        plt.tight_layout()
        plt.show()


def analyze_delays_heatmap_for_each_transport(standardized_data):
    """
    Builds heat maps (day of week vs hour of day) separately for each transport.
    """
    df = pd.DataFrame(standardized_data)
    df = df[df["is_canceled"] == False]

    df["hour_of_day"] = df["datetime"].dt.hour
    df["day_of_week"] = df["datetime"].dt.weekday  # Monday=0, Sunday=6

    transports = df["transport"].unique()

    for t in transports:
        df_t = df[df["transport"] == t]
        if df_t.empty:
            continue

        pivot_data = df_t.pivot_table(
            index="hour_of_day",
            columns="day_of_week",
            values="delay",
            aggfunc="mean"
        )

        # Let's rename the columns for readability
        # 0=Mon, 6=Sun
        day_map = {
            0: "Mon",
            1: "Tue",
            2: "Wed",
            3: "Thu",
            4: "Fri",
            5: "Sat",
            6: "Sun",
        }
        pivot_data.rename(columns=day_map, inplace=True)

        plt.figure(figsize=(10, 8))
        sns.heatmap(
            pivot_data, 
            cmap="YlOrBr", 
            linewidths=.5, 
            annot=True,
            fmt=".1f"
        )
        plt.title(f"Heatmap of delays for {t} \n(day of week horizontally, hour of day vertically)")
        plt.xlabel("Day of the week")
        plt.ylabel("Time of day")
        plt.tight_layout()
        plt.show()


analyze_delays_by_time_of_day_for_each_transport(filtered_data)
analyze_delays_heatmap_for_each_transport(filtered_data)
