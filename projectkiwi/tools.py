import math
from typing import List
import numpy as np

def deg2num(lat_deg, lon_deg, zoom):
  lat_rad = math.radians(lat_deg)
  n = 2.0 ** zoom
  xtile = (lon_deg + 180.0) / 360.0 * n
  ytile = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
  return (xtile, ytile)

def num2deg(xtile, ytile, zoom):
  n = 2.0 ** zoom
  lon_deg = xtile / n * 360.0 - 180.0
  lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
  lat_deg = math.degrees(lat_rad)
  return (lat_deg, lon_deg)


def getBboxLatLng(coords: List[List]):
    """Get bounding box for a polygon. DIFFERENT REFERENCES BETWEEN INPUT AND OUTPUT

    Args:
        coords (List[List]): list of points (x,y) = (lng,lat) with bottom left reference (e.g. [[lng,lat], [lng,lat]])

    Returns:
        x1 (float): closest distance from left reference
        x2 (float): furthest distance from left reference
        y1 (float): closest distance from top reference
        y2 (float): furthest distance from top reference

    """    

    coords = np.array(coords)
    x1 = np.min(coords[:,0])
    x2 = np.max(coords[:,0])
    y1 = np.max(coords[:,1])
    y2 = np.min(coords[:,1])

    return x1, x2, y1, y2


def getBboxTileCoords(coords: List[List], zxy: str):
    """Get bounding box for a polygon. output is in tile coordinates

    Args:
        coords (List[List]): list of points (x,y) = (lng,lat) with bottom left reference (e.g. [[lng,lat], [lng,lat]])

    Returns:
        x1 (float): closest distance from tile left side
        x2 (float): furthest distance from tile left side
        y1 (float): closest distance from tile top side
        y2 (float): furthest distance from tile top side

    """    

    # get bounding box (top left reference)
    x1, x2, y1, y2 = getBboxLatLng(coords)

    z = int(zxy.split("/")[0])
    x = int(zxy.split("/")[1])
    y = int(zxy.split("/")[2])

    # get annotation bounding box in tile coordinates
    x1, y1 = deg2num(y1, x1, z)
    x2, y2 = deg2num(y2, x2, z)

    x1 -= x
    x2 -= x
    y1 -= y
    y2 -= y

    return x1, y1, x2, y2


def getOverlap(coords: List[List], zxy: str) -> float:


    x1, x2, y1, y2 = getBboxTileCoords(coords, zxy)

    # get intersection area
    x_overlap = np.clip(x2, 0, 1) - np.clip(x1, 0, 1)
    y_overlap = np.clip(y2, 0, 1) - np.clip(y1, 0, 1)

    # get annotation area
    annotation_area = abs((x2-x1)*(y2-y1))
    overlap_area = (x_overlap*y_overlap) / annotation_area
    return overlap_area

    
