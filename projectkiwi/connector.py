import requests
import json
import numpy as np
from PIL import Image
import io
from typing import List
from projectkiwi.tools import getOverlap, splitZXY, urlFromZxy
from projectkiwi.models import Annotation, Project, ImageryLayer, TilePath, Task
import threading
import queue




class Connector():
    def __init__(self, key, url="https://project-kiwi.org/"):
        """constructor

        Args:
            key (str): API key.
            url (str, optional): url for api, in case of multiple instances. Defaults to "https://project-kiwi.org/api/".
        """

        self.key = key
        self.url = url


    def getImagery(self, project_id: str) -> List[ImageryLayer]:
        """Get a list of imagery layers for a project

        Args:
            project (str): ID of the project to get all the imagery for.

        Returns:
            List[ImageryLayer]: list of imagery layers
        """        
        
        route = "api/get_imagery"
        params = {
            'key': self.key, 
            'project_id': project_id
        }

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        imageryList = r.json()
        imagery = []
        for layer in imageryList:
            imagery.append(ImageryLayer(**layer))
        assert len(imageryList) == len(imagery), "Failed to parse imagery"
        return imagery


    def readTile(self, url) -> np.ndarray:
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
    
    def getTile(self, 
            z: int,
            x: int,
            y: int,
            imagery_id: str
        ) -> np.ndarray:
        """Download a tile given the z,x,y and id

        Args:
            z (int): zoom
            x (int): x tile
            y (int): y tile
            imagery_id (str): id of the imagery

        Returns:
            np.ndarray: numpy array of tile
        """        

        url = urlFromZxy(z, x, y, imagery_id, self.url, self.key)
        
        return self.readTile(url)



    def getTileList(self, 
            imagery_id: str, 
            project_id: str,
            zoom: int) -> List[TilePath]:
        """Get a list of tiles for a given imagery id

        Args:
            imageryId (str): ID of the imagery to retrieve a list of tiles for
            zoom (int): Zoom level

        Returns:
            List[TilePath]: A list of tiles with zxy and url
        """
        route = "api/get_tile_list"
        params = {
            'key': self.key, 
            'imagery_id': imagery_id, 
            'project_id': project_id,
            'zoom': zoom}

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        tileList = r.json()
        tiles = []
        for tile in tileList:
            tiles.append(TilePath(**tile))
        assert len(tiles) == len(tileList), "Failed to parse tiles"
        return tiles


    def getImageryStatus(self, imagery_id: str) -> str:
        """ Get the status of imagery

        Args:
            imagery_id (str): Imagery id

        Returns:
            str: status
        """        
        route = "api/get_imagery_status"
        params = {'key': self.key, 'imagery_id': imagery_id}

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        return r.json()['status']


    def getProjects(self) -> List[Project]:
        """Get a list of projects for a user

        Returns:
            List[Projects]: projects
        """
        route = "api/get_projects" 
        params = {'key': self.key}

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()

        try:
            projectList = r.json()
            assert len(projectList) > 0, "Error: No projects found"
            projects = []
            for proj in projectList:
                projects.append(Project(**proj))
            assert len(projectList) == len(projects), \
                    f"Error: Could not parse projects, {projectList}"
            return projects
        except Exception as e:
            print("Error: Could not get projects")
            raise e
        

    def addImagery(self, filename: str, name: str, project_id: str) -> str:
        """ Add imagery to project-kiwi.org

        Args:
            filename (str): Path to the file to be uploaded
            name (str): Name for the imagery
            project_id (str): Id of the project to add the layer to

        Returns:
            str: imagery id
        """       
        
        # get presigned upload url
        route = "api/get_imagery_upload_url"
        params = {
            'key': self.key, 
            'filename': filename, 
            'name': name,
            'project_id': project_id
        }
        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        jsonResponse = r.json()
        url = jsonResponse['url']
        
        # upload
        with open(filename, 'rb') as data:
            r = requests.put(url, data=data, headers={'Content-type': ''})
            r.raise_for_status()

        return jsonResponse['imagery_id']
    

    def getSuperTile(self, 
            zxy: str,
            url: str,
            max_zoom: int = 22,
            num_threads: int = 4
    ) -> np.ndarray:
        """Get a tile of imagery with resolution dictated by the choice of zoom

        Args:
            zxy (str): zxy for tile e.g. 12/345/678
            url (str): url template e.g. https://tile.openstreetmap.org/${z}/${x}/${y}.png
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
                    tile = self.readTile(url)
                    q2.put((i,j,tile))
                    q1.task_done()
                except queue.Empty as e:
                    return
                except Exception as e:
                    q2.put((i,j,None))
                    q1.task_done()


        z,x,y = splitZXY(zxy)
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

                imgUrl = url
                imgUrl = imgUrl.replace("{s}.", "")
                imgUrl = imgUrl.replace("{z}", str(z_prime))
                imgUrl = imgUrl.replace("{x}", str(x_prime))
                imgUrl = imgUrl.replace("{y}", str(y_prime))
                imgUrl = imgUrl.replace("{key}", self.key)

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

    
    def getAnnotations(self, project_id: str) -> List[Annotation]:
        """Get all annotations in a project
        Args:
            project_id (str): id for the project to get the predictions for

        Returns:
            List[Annotation]: annotations
        """

        route = "api/get_annotations"
        params = {
            'key': self.key,
            'project_id': project_id
        }

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()

        try:
            annotations = []
            annotationsDict = r.json()
            for annotation_id, data in annotationsDict.items():
                annotations.append(Annotation.from_dict(data, annotation_id))
            assert len(annotationsDict) == len(annotations), "ERROR: could not parse annotations"
            return annotations

        except Exception as e:
            print("Error: Could not load annotations")
            raise e


    def getPredictions(self, project_id: str) -> List[Annotation]:
        """Get all predictions in a project
        Args:
            project_id (str): id for the project to get the predictions for
        Returns:
            List[Annotation]: predictions
        """
        
        annotations = self.getAnnotations(project_id=project_id)

        return [annotation for annotation in annotations if annotation.confidence != None]



    def getAnnotationsForTile(
            self,
            annotations: List[Annotation],
            zxy: str,
            overlap_threshold: float = 0.2
        ) -> List[Annotation]:
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

    def getTasks(self, queue_id: int) -> List[Task]:
        """Get a list of tasks in a queue.

        Args:
            queue_id (int): The ID of the queue

        Returns:
            List[Task]: list of tasks
        """        
       
        route = "api/get_tasks"
        params = {'key': self.key, "queue_id": queue_id}

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        data = r.json()
        assert data['success'] == True, "Failed to get tasks"
        
        taskList = data['task']
        tasks = []
        for task in taskList:
            tasks.append(Task(**task))
        
        assert len(tasks) == len(taskList), "Failed to parse tasks"

        return tasks
    
    def getTask(self, queue_id: int) -> List[Task]:
        """Get a random task for a queue.

        Args:
            queue_id (int): The ID of the queue

        Returns:
            Task: task
        """        
       
        route = "api/get_task"
        params = {'key': self.key, "queue_id": queue_id}

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        data = r.json()
        assert data['success'] == True, "Failed to get tasks"
        
        task = data['task']

        return Task(**task)

    def getNextTask(self, queue_id: int) -> List[Task]:
        """Get a predictable next task for a queue.

        Args:
            queue_id (int): The ID of the queue

        Returns:
            Task: task
        """        
       
        route = "api/get_next_task"
        params = {'key': self.key, "queue_id": queue_id}

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        data = r.json()
        assert data['success'] == True, "Failed to get tasks"
        
        task = data['task']

        return Task(**task)


    def addAnnotation(self, annotation: Annotation, project: str) -> int:
        """Add an annotation to a project

        Args:
            annotation (Annotation): the annotation to add (note that not everything is mandatory)
            project (str): project id

        Returns:
            int: annotation id if successful
        """        
        route = "api/add_annotation"
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        annoDict = dict(annotation)
        annoDict['project_id'] = project
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
        route = "api/add_prediction"
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        annoDict = dict(annotation)
        annoDict['project_id'] = project
        annoDict['key'] = self.key
        r = requests.post(self.url + route, data=json.dumps(annoDict), headers=headers)
        r.raise_for_status()
        jsonResponse = r.json()
        return jsonResponse['annotation_id']

    def getImageryUrl(self, imagery_id: str, project_id: str) -> str:
        """Get the url for imagery from it's id

        Args:
            imagery_id (str): Id for the imagery
            project_id (str): Project to look in

        Returns:
            str: The url template
        """        
        imagery = self.getImagery(project_id)
        imagery_url = [image.url for image in imagery if image.id == imagery_id][0]
        return imagery_url
        
    def removeAllPredictions(self, project_id: str):
        """Remove all predictions in a project

        Args:
            project_id (str): project id
        """    

        route = "api/remove_all_predictions" 
        params = {'key': self.key, 'project_id': project_id}

        r = requests.delete(self.url + route, 
                headers={'Content-Type': 'application/json'},
                data=json.dumps(params))
        r.raise_for_status()
