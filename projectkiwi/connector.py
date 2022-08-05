import requests
import json
import numpy as np
from PIL import Image
import io
from typing import List
from projectkiwi.tools import getOverlap, splitZXY
from projectkiwi.models import Annotation
import threading
import queue




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
        return np.asarray(Image.open(io.BytesIO(tileContent)))


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
            zxy: str,
            url: str = None,
            imagery_id: str = None,
            max_zoom: int = 22,
            num_threads: int = 4
    ) -> np.ndarray:
        """Get a tile of imagery with resolution dictated by the choice of zoom

        Args:
            zxy (str): zxy for tile e.g. 12/345/678
            url (str, optional): url template e.g. https://tile.openstreetmap.org/${z}/${x}/${y}.png . Defaults to None.
            imagery_id (str, optional): imagery id for project kiwi managed imagery. Defaults to None.
            max_zoom (int, optional): full resolution tiles to use. Defaults to 22.
            num_threads (int, optional): number of threads for downloading. Defaults to 4.

        Raises:
            RuntimeError: raised if no tiles available.

        Returns:
            np.ndarray: the tile, e.g. [1024,1024,3]
        """    
        
        q1 = queue.Queue()
        q2 = queue.Queue()

        def worker(q1, q2):
            while True:
                try:
                    i, j, url = q1.get(timeout=10)
                    tile = self.getTile(url)
                    q2.put((i,j,tile))
                    q1.task_done()
                except queue.Empty as e:
                    return
                except Exception as e:
                    q2.put((i,j,None))
                    q1.task_done()


        z,x,y = splitZXY(zxy)

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
        
        for i in range(tile_width):
            for j in range(tile_width):
                z_prime = max_zoom
                x_prime = x*tile_width + i
                y_prime = (y+1)*tile_width - (j+1)

                imgUrl = urlTemplate
                imgUrl = imgUrl.replace("{z}", str(z_prime))
                imgUrl = imgUrl.replace("{x}", str(x_prime))
                imgUrl = imgUrl.replace("{y}", str(y_prime))

                q1.put((i, j, imgUrl))
        
        for _ in range(num_threads):
            threading.Thread(target=worker, args=(q1, q2)).start()
        q1.join()
        
        success, fails = 0, 0
        numTiles = (tile_width*tile_width)
        for _ in range(numTiles):
            i, j, tile = q2.get(timeout=1)
            if tile is not None:
                channels = tile.shape[-1]
                returnImg[(tile_width - (j+1))*256:(tile_width - j)*256, i*256:(i+1)*256, 0:channels] = tile
                success += 1
            else:
                returnImg[(tile_width - (j+1))*256:(tile_width - j)*256, i*256:(i+1)*256 :] = np.zeros((256, 256, 4))
                fails += 1

        if fails == numTiles:
            raise RuntimeError("No valid tiles loaded here")

        # always return uint8
        returnImg = returnImg.astype(np.uint8)

        # if type is RGBA, remove alpha
        if channels <= 3:
            return returnImg[:,:,0:channels]
        elif channels > 3:
            return returnImg[:,:,:3]

    
    def getAnnotations(self, project=None):
        """Get all annotations in a project

        Returns:
            List[Annotation]: annotations
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
            for id, data in annotationsDict.items():
                annotations.append(Annotation.from_dict(data, id))

            return annotations

        except Exception as e:
            print("Error: Could not load annotations")
            raise e


    def getPredictions(self, project=None):
        """Get all predictions in a project

        Returns:
            List[Annotation]: predictions
        """
        
        annotations = self.getAnnotations(project=project)

        return [annotation for annotation in annotations if annotation.confidence != None]



    def getAnnotationsForTile(
            self,
            annotations: List[Annotation],
            zxy: str,
            overlap_threshold: float = 0.2
        ) -> List[Annotation]:
        """ Filter a set of annotations for those that have overlap with some tile

        Args:
            annotations (List[Annotation]): All annotations
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

    def getTasks(self, queue_id: int) -> List[dict]:
        """Get a list of tasks in a queue.

        Args:
            queue_id (int): The ID of the queue

        Returns:
            List[dict]: list of tasks, each is a dict
        """        
       
        route = "get_tasks"
        params = {'key': self.key, "queue_id": queue_id}

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        jsonResponse = r.json()
        return jsonResponse['task']


    def addAnnotation(self, annotation: Annotation, project: str) -> int:
        """Add an annotation to a project

        Args:
            annotation (Annotation): the annotation to add (note that not everything is mandatory)
            project (str): project id

        Returns:
            int: annotation id if successful
        """        
        route = "add_annotation"
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        annoDict = dict(annotation)
        annoDict['project'] = project
        annoDict['key'] = self.key
        r = requests.post(self.url + route, data=json.dumps(annoDict), headers=headers)
        r.raise_for_status()
        jsonResponse = r.json()
        return jsonResponse['annotation_id']
    

    def addPrediction(self, annotation: Annotation, project: str) -> int:
        """Add a prediction to a project

        Args:
            annotation (Annotation): an annotation object with a confidence value
            project (str): project id

        Returns:
            int: annotation id if successful
        """       

        assert not annotation.confidence is None, "No confidence for prediction"
        route = "add_prediction"
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        annoDict = dict(annotation)
        annoDict['project'] = project
        annoDict['key'] = self.key
        r = requests.post(self.url + route, data=json.dumps(annoDict), headers=headers)
        r.raise_for_status()
        jsonResponse = r.json()
        return jsonResponse['annotation_id']