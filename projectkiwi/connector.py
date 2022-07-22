import logging
from matplotlib import projections
import requests
import json
import numpy as np
from PIL import Image
import io
from pydantic import BaseModel
from typing import List, Optional
from projectkiwi.tools import getOverlap

class Annotation(BaseModel):
    id: int
    shape: str
    label_id: int
    label_name: str
    label_color: str
    coordinates: List[List[float]]
    what3words: Optional[str]
    url: Optional[str]
    imagery_id: Optional[str]

    @classmethod
    def from_dict(cls, annotation_id: int, data: dict):
        coordinates = []
        for point in data['coordinate']:
            coordinates.append([float(point[0]), float(point[1])])

        
        what3words = data['what3words']
        if what3words == "none":
            what3words = None
        
        imagery_id = data['imagery_id']
        if imagery_id == "NULL":
            imagery_id = None

        
        return cls(
            id = annotation_id,
            shape = data['shape'],
            label_id = data['label_id'],
            label_name = data['label_name'],
            label_color = data['label_color'],
            coordinates = coordinates,
            what3words = data['what3words'],
            url = data['url'],
            imagery_id = data['imagery_id']
        )



class Connector():
    def __init__(self, key, url="https://project-kiwi.org/api/"):
        """constructor

        Args:
            key (str): API key.
            url (str, optional): url for api, in case of multiple instances. Defaults to "https://project-kiwi.org/api/".

        Raises:
            ValueError: API key must be supplied.
        """        
        if key is None:
            raise ValueError("API key missing")

        self.key = key
        self.url = url


    def getImagery(self, project=None):
        """Get a list of imagery

        Args:
            project (str, optional): ID of the project to get all the imagery for, by default, all projects associated with user.

        Returns:
            json: list of imagery
        """        
        route = "get_imagery"
        params = {'key': self.key}
        if not project is None:
            params['project'] = project
        else:
            projects = self.getProjects()
            assert len(projects) > 0, "No projects found"
            assert len(projects) == 1, "Multiple projects found, please specify a single project"
            params['project'] = projects[0]

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        jsonResponse = r.json()
        return jsonResponse


    def getTiles(self, imageryId: str):
        """Get a list of tiles for a given imagery id

        Args:
            imageryId (str): ID of the imagery to retrieve a list of tiles for

        Returns:
            list: list of tile urls
        """        
        route = "get_tile_list"
        params = {'key': self.key, 'imagery_id': imageryId}

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        jsonResponse = r.json()
        return jsonResponse

    def getTile(self, url):
        """Get a tile in numpy array form

        Args:
            url (str): url of the tile

        Returns:
            np.array: numpy array containing the tile
        """
        r = requests.get(url)
        r.raise_for_status()
        tileContent = r.content
        return np.array(Image.open(io.BytesIO(tileContent)))


    def getTileDict(self, imageryId: str):
        """Get a dictionary of tiles for a given imagery id

        Args:
            imageryId (str): ID of the imagery to retrieve a list of tiles for

        Returns:
            dict: a dictionary of tiles with zxy keys
        """        
        route = "get_tile_list"
        params = {'key': self.key, 'imagery_id': imageryId}

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        jsonResponse = r.json()
        dict = {}
        for tile in jsonResponse:
            dict[tile['zxy']] = tile['url']
        return dict



    def getImageryStatus(self, imageryId: str):
        """ Get the status of imagery

        Args:
            imageryId (str): Imagery id

        Returns:
            str: status
        """        
        route = "get_imagery_status"
        params = {'key': self.key, 'imagery_id': imageryId}

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        return r.json()['status']


    def setImageryStatus(self, imageryId: str, status: str):
        """Set the status for imagery e.g. when the upload is complete

        Args:
            imageryId (str): Imagery id
            status (str): status e.g. "awaiting processing"
        """
        route = "set_imagery_status" 
        params = {'key': self.key, 'imagery_id': imageryId, 'status': status}

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()

    def getProjects(self):
        """Get a list of projects you have access to

        Returns:
            List: projects
        """
        route = "get_projects" 
        params = {'key': self.key}

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()

        try:
            projects = r.json()['projects']
            assert len(projects) > 0, "Error: No projects found"
            return projects
        except Exception as e:
            print("Error: Could not find projects")
            raise e
        

    def addImagery(self, filename: str, name: str):
        """ Add imagery to project-kiwi.org

        Args:
            filename (str): Path to the file to be uploaded
            name (str): Name for the imagery

        Returns:
            int: imagery id
        """       
        
        # get presigned upload url
        route = "get_imagery_upload_url"
        params = {'key': self.key, 'filename': filename, 'name': name}
        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        jsonResponse = r.json()
        url = jsonResponse['url']
        
        # upload
        r = requests.put(url, data=open(filename, 'rb'), headers={'Content-type': ''})
        r.raise_for_status()

        # set the status - triggers processing
        self.setImageryStatus(jsonResponse['imagery_id'], "awaiting processing")
        return jsonResponse['imagery_id']
    

    def getSuperTile(self, 
            z: int, 
            x: int, 
            y: int,
            url: str = None,
            imagery_id: str = None,
            max_zoom: int = 22
    ) -> np.ndarray:
        
        # make urls
        if url is None:
            assert not imagery_id is None, "Please specify either an imagery id or url"
            urlTemplate = "https://project-kiwi-tiles.s3.amazonaws.com/" + imagery_id + "/{z}/{x}/{y}"
        else:
            urlTemplate = url
        

        tile_width = 2**(max_zoom - z)
        width = 256*tile_width
        assert width < 10000, "Resultant image would be too large (100MP limit), try reducing max zoom or increasing super tile zoom"
        height = width
        channels = 4  # assume 4 channels to begin with

        returnImg = np.zeros((width, height, channels))
        
        numTiles = (tile_width*tile_width)
        success = 0
        fails = 0
        for i in range(tile_width):
            for j in range(tile_width):
                z_prime = max_zoom
                x_prime = x*tile_width + i
                y_prime = (y+1)*tile_width - j

                imgUrl = urlTemplate
                imgUrl = imgUrl.replace("{z}", str(z_prime))
                imgUrl = imgUrl.replace("{x}", str(x_prime))
                imgUrl = imgUrl.replace("{y}", str(y_prime))
                print(imgUrl)

                try:
                    tile = self.getTile(imgUrl)
                    channels = tile.shape[-1]
                    returnImg[(tile_width - (j+1))*256:(tile_width - j)*256, i*256:(i+1)*256, 0:channels] = tile
                    success += 1
                except Exception as e:
                    returnImg[(tile_width - (j+1))*256:(tile_width - j)*256, i*256:(i+1)*256 :] = np.zeros((256, 256, 4))
                    fails += 1
                    print(f"Failed to load: {imgUrl}")
        if fails == numTiles:
            raise RuntimeError("No valid tiles loaded here")
        return returnImg[:,:,0:channels]

    
    def getAnnotations(self, project=None):
        """Get all annotations in a project

        Returns:
            List: annotations
        """
        route = "get_annotations" 
        params = {'key': self.key, }
        if not project is None:
            params['project'] = project
        else:
            projects = self.getProjects()
            assert len(projects) > 0, "No projects found"
            assert len(projects) == 1, "Multiple projects found, please specify a single project"
            params['project'] = projects[0]

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()

        try:
            annotations = []
            annotationsDict = r.json()
            for key, item in annotationsDict.items():
                annotations.append(Annotation.from_dict(key, item))

            return annotations

        except Exception as e:
            print("Error: Could not load annotations")
            raise e

    def getAnnotationsForTile(
            self,
            project: str,
            zxy: str,
            overlap_threshold: float = 0.0,
            imagery_id: Optional[str] = None
        ) -> List[Annotation]:

        # get annotations
        annotations = self.getAnnotations(project=project)

        annotationsInTile = []

        # filter annotations
        for annotation in annotations:
            if not imagery_id is None:
                if annotation.imagery_id != imagery_id:
                    continue
            
            # check overlap with tile
            if getOverlap(annotation.coordinates, zxy) < overlap_threshold:
                continue

            annotationsInTile.append(annotation)

        return annotationsInTile
