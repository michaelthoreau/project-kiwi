from re import L
import requests
import json
import numpy as np
from PIL import Image
import io
from typing import List
from projectkiwi.tools import getOverlap, num2deg, splitZXY, urlFromZxy
from projectkiwi.models import Annotation, Project, ImageryLayer, Tile, Task, Label
import threading
import queue




class Connector():
    def __init__(self, key, url="https://projectkiwi.io/"):
        """constructor

        Args:
            key (str): API key.
            url (str, optional): url for api, in case of multiple instances. Defaults to "https://projectkiwi.io/".
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


    
    def getTile(self,
            imagery_id: str,
            z: int,
            x: int,
            y: int,
            tile_size: int = 256,
            tile_buffer: int = 0
        ) -> np.ndarray:
        """Download a tile given the z,x,y and id

        Args:
            imagery_id (str): id of the imagery
            z (int): zoom
            x (int): x tile
            y (int): y tile
            tile_size (int): width or height of the square tile
            tile_buffer (int): number of pixels to read each side of the tile


        Returns:
            np.ndarray: numpy array of tile
        """

        url = urlFromZxy(z, x, y, imagery_id, self.url)

        params={
            'key': self.key,
            'tile_size': tile_size,
            'tile_buffer': tile_buffer
        }

        r = requests.get(url, params=params)
        r.raise_for_status()
        tileContent = r.content
        return np.asarray(Image.open(io.BytesIO(tileContent)))
        




    def getTileList(self,
            imagery_id: str,
            project_id: str,
            zoom: int) -> List[Tile]:
        """Get a list of tiles for a given imagery id

        Args:
            imageryId (str): ID of the imagery to retrieve a list of tiles for
            zoom (int): Zoom level

        Returns:
            List[Tile]: A list of tiles with zxy and url
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
            tiles.append(
                Tile.from_zxy(
                    zxy = tile['zxy'], 
                    imagery_id = imagery_id,
                    url = tile['url'])
            )
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
        """ Add imagery to projectkiwi.io

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
                imagery_id: str,
                zxy: str,
                max_zoom: int = 22,
                padding: int = 0
        ) -> np.ndarray:
        """Get a tile as higher resolution, as specified by the max zoom.

        Args:
            imagery_id (str): The ID of the imagery
            zxy (str): zxy string to specify the tile e.g. 12/345/678
            max_zoom (int, optional): Maximum zoom. Defaults to 22.
            padding (int, optional): Number of pixels to read on each side of the tile. Defaults to 0.

        Returns:
            np.ndarray: Image data for the tile.
        """            

        z,x,y = splitZXY(zxy)
        tile_width = 2**(max_zoom - z)
        width = 256*tile_width

        return self.getTile(imagery_id, z, x, y, tile_size=width, tile_buffer=padding)



    
    def getAnnotations(self, project_id: str) -> List[Annotation]:
        """Get all annotations in a project

        Args:
            project_id (str): id for the project to get the predictions for

        Returns:
            List[Annotation]: annotations

        Example:
            All the annotations for a project can be retrieved using this function. Replace the project id listed below with your own.

            >>> annotations = conn.getAnnotations(project_id = "51f696a5361f")
            >>> print(annotations[0])
            Annotation(shape='Polygon', label_id=374, coordinates=[[-87.612448, 41.867452], [-87.605238, 41.867452], [-87.605238, 41.852301], [-87.612448, 41.852301], [-87.612448, 41.867452]], url=None, imagery_id=None, confidence=None, id=3720, label_name='airport', label_color='rgb(10, 184, 227)')
            >>> print(annotations[0].geoJSON()) # as geoJSON
            {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[-87.612448, 41.867452], [-87.605238, 41.867452], [-87.605238, 41.852301], [-87.612448, 41.852301], [-87.612448, 41.867452]]}, "properties": {"label_id": 374, "name": "airport"}}

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

        Example:
            All predictions in a project can be retrieved as follows. Replace the project id shown below with your own.

            >>> predictions = conn.getPredictions(project_id="51f969a5361f")
            >>> print(predictions)
            [Annotation(shape='Polygon', label_id=374, coordinates=[[-87.612448, 41.867452], [-87.605238, 41.867452], [-87.605238, 41.852301], [-87.612448, 41.852301], [-87.612448, 41.867452]], url=None, imagery_id=None, confidence=0.69, id=259184, label_name='airport', label_color='rgb(10, 184, 227)')]

        """
        
        annotations = self.getAnnotations(project_id=project_id)

        return [annotation for annotation in annotations if annotation.confidence != None]



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

        Example:
            Predictions are annotation objects with a confidence value between 0 and 1. The following example creates
            a prediction for an already existing object class.

                >>> from projectkiwi.models import Annotation
                >>> prediction = Annotation(shape='Polygon', 
                ...                        label_id=374, 
                ...                        coordinates=[
                ...                            [-87.612448, 41.867452], 
                ...                            [-87.605238, 41.867452], 
                ...                            [-87.605238, 41.852301], 
                ...                            [-87.612448, 41.852301], 
                ...                            [-87.612448, 41.867452]],
                ...                        confidence=0.69
                ...                        )
                >>> id = conn.addPrediction(prediction, project="51f969a5361f")
                >>> print(f"prediction id: {id}")
                prediction id: 259185
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

    def getLabels(self, project_id: str) -> List[Label]:
        """Get all labels in a project

        Args:
            project_id (str): id for the project to get the labels for

        Returns:
            List[Label]: labels
        """

        route = "api/get_labels"
        params = {
            'key': self.key,
            'project_id': project_id
        }

        r = requests.get(self.url + route, params=params)
        r.raise_for_status()

        try:
            labels = []
            labelsJSON = r.json()
            for label in labelsJSON:
                labels.append(Label(**label))
            assert len(labelsJSON) == len(labels), "ERROR: could not parse labels"
            return labels

        except Exception as e:
            print("Error: Could not load labels")
            raise e
    


    def addLabel(self, name: str, project_id: str, color: str = None) -> Label:
        """ add a label to the project

        Args:
            name (str): name of the label e.g. object class
            project_id (str): id of the project that the label will belong to
            color (str, optional): Color string for the label e.g. rgb(255, 0, 100), will be selected randomly if not supplied. Defaults to None.

        Returns:
            Label: the label including it's id
        """        

        if color is None:
            rgb = list(np.random.choice(range(256), size=3))
            min_rgb = np.array(rgb).min()
            max_rgb = np.array(rgb).max()
            for i,c in enumerate(rgb):
                if c == min_rgb:
                    rgb[i] = 0
                if c == max_rgb:
                    rgb[i] = 256
            color = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"


        labelDict = {}
        labelDict['key'] = self.key
        labelDict['project_id'] = project_id
        labelDict['name'] = name
        labelDict['status'] = 'active'
        labelDict['color'] = color

        route = "api/add_label"
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}


        r = requests.post(self.url + route, data=json.dumps(labelDict), headers=headers)
        r.raise_for_status()
        jsonResponse = r.json()
        return Label(**jsonResponse)