import math
from typing import List, Union
import numpy as np
from warnings import warn
from . import models
from PIL import Image, ImageDraw
from shapely.geometry import Polygon

def deg2num(lat_deg: float, lon_deg:  float, zoom: int):
    """Convert lat,lng to xyz tile coordinates.
    reference: https://developers.planet.com/docs/planetschool/xyz-tiles-and-slippy-maps/

    Args:
        lat_deg (float): latitude in decimal degrees
        lon_deg (float): longitude in decimal degrees
        zoom (int): zoom level e.g. 19

    Returns:
        x_tile (float): x in tile coordinates at specified zoom level
        y_tile (float): y in tile coordinates at specified zoom level
    """

    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = (lon_deg + 180.0) / 360.0 * n
    ytile = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return xtile, ytile



def num2deg(xtile: Union[float, int], ytile: Union[float, int], zoom: int):
    """convert x, y, tile coordinates to lat, lng. 
    ref: https://developers.planet.com/docs/planetschool/xyz-tiles-and-slippy-maps/

    Args:
        xtile (Union[float, int]): x position
        ytile (Union[float, int]): y position
        zoom (int): zoom level e.g. 19

    Returns:
        lat_deg (float): latitude in decimal degrees
        lng_deg (float): longitude in decimal degrees
    """
    n = 2.0 ** zoom
    lng_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lng_deg



def getBboxLatLng(coords: List[List]):
    """Get bounding box for a polygon.

    Args:
        coords (List[List]): list of points (x,y) = (lng,lat) with bottom left reference (e.g. [[lng,lat], [lng,lat]])

    Returns:
        x1 (float): closest distance from left reference
        y1 (float): closest distance from top reference
        x2 (float): furthest distance from left reference
        y2 (float): furthest distance from top reference

    """    

    coords = np.array(coords)
    x1 = np.min(coords[:,0])
    y1 = np.max(coords[:,1])
    x2 = np.max(coords[:,0])
    y2 = np.min(coords[:,1])

    return x1, y1, x2, y2



def getBboxTileCoords(coords: List[List], zxy: str):
    """Get bounding box for a polygon. output is in tile coordinates

    Args:
        coords (List[List]): list of points (x,y) = (lng,lat) with bottom left reference (e.g. [[lng,lat], [lng,lat]])

    Returns:
        x1 (float): closest distance from tile left side
        y1 (float): closest distance from tile top side
        x2 (float): furthest distance from tile left side
        y2 (float): furthest distance from tile top side

    """    

    # get bounding box (top left reference)
    x1, y1, x2, y2 = getBboxLatLng(coords)

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


def getOverlap(coords: List[List], zxy: str):
    """ Get the portion of a bounding box that is inside a tile

    Args:
        coords (List[List]): list of points in the polygon (lat,lng)
        zxy (str): tile e.g. 12/345/678

    Returns:
        float: overlap [0,1]
    """
    x1, y1, x2, y2 = getBboxTileCoords(coords, zxy)

    # get intersection area
    x_overlap = np.clip(x2, 0, 1) - np.clip(x1, 0, 1)
    y_overlap = np.clip(y2, 0, 1) - np.clip(y1, 0, 1)

    # get annotation area
    annotation_area = abs((x2-x1)*(y2-y1))
    
    if annotation_area == 0:
        return 0

    return (x_overlap*y_overlap) / annotation_area


def getAnnotationsForTile(
            annotations: List[models.Annotation],
            zxy: str,
            overlap_threshold: float = 0.2
        ) -> List[models.Annotation]:
        """ Filter a set of annotations for those that have overlap with some tile

        Args:
            annotations (List[Annotation]): Annotations to filter
            zxy (str): The tile e.g. 12/345/678
            overlap_threshold (float, optional): How much overlap. Defaults to 0.2.

        Returns:
            List[Annotation]: All the annotations that have enough overlap with the specified tile
        """        

        annotationsInTile = []

        # filter annotations
        for annotation in annotations:
            # check overlap with tile
            overlap = getOverlap(annotation.coordinates, zxy)
            if overlap < overlap_threshold:
                continue
            annotationsInTile.append(annotation)

        return annotationsInTile

def bboxFromCoords(coordinates: List[List], zxy: str, tile_size: int, clip: bool = False):
    """ Get a bounding box from a polygon (lng, lat)

    Args:
        coordinates (List[List]): List of points in polygon (lng, lat)
        zxy (str): Tile zxy
        tile_size (int): size of tile, e.g. 256
        clip (Optional[bool]): Clip the boxes to the edge of the tiles

    Returns:
        x1 (int): top-left x coordinate
        y1 (int): top-left y coordinate
        x2 (int): bottom-right x coordinate
        y2 (int): bottom-right y coordinate
    """

    bbox = getBboxTileCoords(coordinates, zxy)
    
    [x1, y1, x2, y2] = bbox
    
    if clip:
        x1 = np.clip(bbox[0], 0, 1)
        y1 = np.clip(bbox[1], 0, 1)
        x2 = np.clip(bbox[2], 0, 1)
        y2 = np.clip(bbox[3], 0, 1)

    x1 *= tile_size
    y1 *= tile_size
    x2 *= tile_size
    y2 *= tile_size

    return x1, y1, x2, y2


def bboxToCoco(x1: int, y1: int, x2: int, y2: int):
    """ Convert two-point bbox to coco format

    Args:
        x1 (int): top-left x coordinate
        y1 (int): top-left y coordinate
        x2 (int): bottom-right x coordinate
        y2 (int): bottom-right y coordinate

    Returns:
        x (int): top-left x coordinate
        y (int): top-left y coordinate
        w (int): box width
        h (int): box height
    """

    w = int(x2-x1)
    h = int(y2-y1)
    
    return x1, y1, w, h



def yx_to_xy(yx: List[List]) -> List[List]:
    """" switch the ordering in our array, explicitely so we dont forget

    Args:
        yx (List[List]): [[y,x], [y,x]]

    Returns:
        List[List]: [[x,y], [x,y]]
    """
    return [[x,y] for y,x in yx]

def bboxToPolygon(x1, y1, x2, y2):
    """ Get a 4 point polygon from a bounding box.

    Args:
        x1 (float): left edge
        y1 (float): top edge
        x2 (float): right edge
        y2 (float): bottom edge

    Returns:
        List[List[float]]: polygon
    """
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]]

def coordsFromPolygon(
        polygon: List[List[float]],
        zxy: str, 
        tile_size: int,
        padding: int = 0) -> List[List[float]]:
    """ get a lat/lng polygon from a polygon in a tile

    Args:
        polygon (List[List[float]]): coordinates in the image [[y,x],[y,x]]
        zxy (str): zxy string for the tile e.g. 12/34/567
        width (int): width of the tile
        height (int): height of the tile
        padding (int, optional): number of extra pixels around the edge of the tile. Defaults to 0.

    Returns:
        List[List[float]]: coordinates in [[lng,lat],[lng,lat]] format
    """


    z,x,y = splitZXY(zxy)

    points_lat_lng = []
    for (x1,y1) in polygon:

      x1 -= padding
      y1 -= padding

      # Normalise
      x1 /= tile_size
      y1 /= tile_size

      # add task corner x,y
      x1 += x
      y1 += y

      # convert to lat,lng
      lat, lng = num2deg(x1, y1, z)
      points_lat_lng.append([lng, lat])

    return points_lat_lng

def coordsFromBbox(
        x1: int, 
        y1: int, 
        x2: int, 
        y2: int, 
        zxy: str, 
        width: int, 
        height: int) -> List[List[float]]:
    """Get lng,lat coordinate list from a bounding box and width height

    Args:
        x1 (int): left edge
        y1 (int): top edge
        x2 (int): right edge
        y2 (int): bottom edge
        zxy (str): tile e.g. 12/345/678
        width (int): tile width in pixels
        height (int): tile height in pixels


    Returns:
        List[List[float]]: coordinate for polygon

    """

    warn('This function is deprecated, consider a combination of bboxToPolygon and coordsFromPolygon', DeprecationWarning, stacklevel=2)


    z,x,y = splitZXY(zxy)
    x1 /= width
    y1 /= height
    x2 /= width
    y2 /= height
    points = [[x+x1, y+y1],
        [x+x2, y+y1],
        [x+x2, y+y2],
        [x+x1, y+y2],
        [x+x1, y+y1]]
    points_lat_lng = []
    for point in points:
        lat, lng = num2deg(point[0], point[1], z)
        points_lat_lng.append([lng, lat])
    return points_lat_lng


def latLngToImgCoords(coords: List[List], zxy: str, tile_size: int) -> List[List]:
    """ convert a list of coordinates to pixel coordinates in a tile

    Args:
        coords (List[List]): coordinates e.g. [[lng,lat], [lng, lat]]
        zxy (str): tile zxy string e.g. 12/34/567
        tile_size (int): width of the tile e.g. 256 - dont forget padding

    Returns:
        List[List]: _description_
    """

    tile_z, tile_x, tile_y = splitZXY(zxy)

    coords_tile = []
    # get annotation bounding box in tile coordinates
    for (x, y) in coords:
      x_prime, y_prime = deg2num(y, x, tile_z)
      coords_tile.append([x_prime - tile_x, y_prime - tile_y])

    coords_img = []
    for (x,y) in coords_tile:
      coords_img.append((int(x*tile_size), int(y*tile_size)))

    return coords_img

  

def splitZXY(zxy: str):
    """ Split an zxy string up in to z,x,y component

    Args:
        zxy (str): zxy string e.g. 12/345/678

    Returns:
        z: tile zoom level
        x: tile x
        y: tile y

    Example:
        Consider splitting the zxy string "12/345/678"::

            z, x, y = splitZXY("12/345/678")
            print(z,x,y)
            # result: 12, 345, 678

    """

    z = int(zxy.split("/")[0])
    x = int(zxy.split("/")[1])
    y = int(zxy.split("/")[2])

    return z, x, y


def urlFromZxy(z: int, x: int, y: int, imagery_id: str, baseUrl: str, serverless: bool = True) -> str:
    """Generate a url given a zxy and an imagery id

    Args:
        z (int): zoom
        x (int): x tile
        y (int): y tile
        imagery_id (str): id of the imagery
        baseUrl (str): base url e.g. https://projectkiwi.io/
        serverless (bool): whether to use tiles from lambda or direct from the api. Defaults to True.

    Returns:
        str: url to download the tile, however api key is still required as a param
    """
    if serverless:
        return f"https://api.projectkiwi.io/get_tile/{imagery_id}/{z}/{x}/{y}"
    else:
        return f"{baseUrl}/api/get_tile/{imagery_id}/{z}/{x}/{y}"


def maskFromPolygon(polygon: List[List], width: int, height: int) -> np.ndarray:
    """generates a binary mask from a polygon in image coordinates

    Args:
        polygon (List[List]): list of points in the polygon, image coordinates
        width (int): width of the output mask
        height (int): height of the output mask

    Returns:
        np.ndarray: the binary image
    """    
    im = Image.new('L', (width, height), 0)
    ImageDraw.Draw(im).polygon(polygon, outline=1, fill=1)
    mask = np.array(im)
    return mask


def bbox_iou(box1: List, box2: List) -> float:
    """calculate the intersection over union of two bounding boxes

    Args:
        box1 (List): first box
        box2 (List): second box

    Returns:
        float: the iou
    """    
    return iou(    [
                    [box1[0], box1[1]], 
                    [box1[2], box1[1]], 
                    [box1[2], box1[3]], 
                    [box1[0], box1[3]]
                    ],
                   [
                    [box2[0], box2[1]], 
                    [box2[2], box2[1]], 
                    [box2[2], box2[3]], 
                    [box2[0], box2[3]]
                    ])


def iou(poly1: List[List], poly2: List[List]) -> float:
    """ calculate the iou of each polygon

    Args:
        poly1 (List[List]): list of points in the first polygon e.g. [[x,y], [x,y]]
        poly2 (List[List]): list of points in the second polygon e.g. [[x,y], [x,y]]

    Returns:
        float: iou between the polygons.
    """
    
    poly1 = Polygon(poly1)
    poly2 = Polygon(poly2)
    intersection = poly1.intersection(poly2).area
    if intersection == 0:
      return 0
    union = poly1.union(poly2).area
    return intersection / union