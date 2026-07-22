from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from rainroute_data.parsers.radar_latlon import RadarCoordinateGrid


@dataclass(frozen=True)
class RadarStationMatch:
    y: int
    x: int
    grid_latitude: float
    grid_longitude: float
    distance_km: float


def haversine_distance_km(
    latitude_1: float,
    longitude_1: float,
    latitude_2: np.ndarray,
    longitude_2: np.ndarray,
) -> np.ndarray:
    radius_km = 6371.0088

    lat1 = np.deg2rad(latitude_1)
    lon1 = np.deg2rad(longitude_1)
    lat2 = np.deg2rad(latitude_2)
    lon2 = np.deg2rad(longitude_2)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        np.sin(delta_lat / 2.0) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(delta_lon / 2.0) ** 2
    )

    return 2.0 * radius_km * np.arcsin(np.sqrt(a))


def nearest_radar_cell(
    *,
    station_latitude: float,
    station_longitude: float,
    latitude: RadarCoordinateGrid,
    longitude: RadarCoordinateGrid,
) -> RadarStationMatch:
    if latitude.shape != longitude.shape:
        raise ValueError(
            "Latitude and longitude grid shapes must match"
        )

    distances = haversine_distance_km(
        station_latitude,
        station_longitude,
        latitude.values,
        longitude.values,
    )

    flat_index = int(np.nanargmin(distances))
    y, x = np.unravel_index(flat_index, distances.shape)

    return RadarStationMatch(
        y=int(y),
        x=int(x),
        grid_latitude=float(latitude.values[y, x]),
        grid_longitude=float(longitude.values[y, x]),
        distance_km=float(distances[y, x]),
    )
