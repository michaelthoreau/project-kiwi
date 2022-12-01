from turtle import st
from pydantic import BaseModel
from typing import List, Optional
import json

class Annotation(BaseModel):  
    shape: str
    label_id: int
    coordinates: List[List[float]]
    url: Optional[str]
    imagery_id: Optional[str]
    confidence: Optional[float]
    id: Optional[int]
    label_name: Optional[str]
    label_color: Optional[str]

    @classmethod
    def from_dict(cls, data: dict, annotation_id: int = None):
        coordinates = []
        for point in data['coordinates']:
            coordinates.append([float(point[0]), float(point[1])])

        
        imagery_id = data['imagery_id']
        if imagery_id == "NULL":
            imagery_id = None

        confidence = data['confidence']
        if confidence == "NULL":
            confidence = None
        
        if annotation_id is None:
            annotation_id = int(data['id'])

        
        return cls(
            id = annotation_id,
            shape = data['shape'],
            label_id = data['label_id'],
            label_name = data['label_name'],
            label_color = data['label_color'],
            coordinates = coordinates,
            url = data['url'],
            imagery_id = data['imagery_id'],
            confidence=confidence
        )
    
    def geoJSON(self) -> str:
        """Convert the annotation to a geoJSON string

        Returns:
            str: geoJSON representation

        Example:

            >>>
        """

        geojson = {
            "type": "Feature",
            "geometry": {
                "type": self.shape,
                "coordinates": self.coordinates
            },
            "properties": {
                "label_id": self.label_id
            }
        }

        if self.confidence is not None:
            geojson['properties']['confidence'] = self.confidence
        
        if self.label_name is not None:
            geojson['properties']['name'] = self.label_name

        return json.dumps(geojson)






class Project(BaseModel):
    name: str
    id: str
    user_login: str

    @classmethod
    def from_dict(cls, data: dict):

        return cls(
            name = data['name'],
            id = data['project_id'],
            user_login = data['user_login']
        )

class ImageryLayer(BaseModel):
    id: str
    project: str
    name: str
    url: str
    attribution: str
    size_mb: Optional[float]
    bounds: Optional[List[float]]
    min_zoom: Optional[int]
    max_zoom: Optional[int]
    status: Optional[str]

class Tile(BaseModel):
    zxy: str
    imagery_id: str
    url: str
    z: int
    x: int
    y: int


    @classmethod
    def from_zxy(cls, 
            zxy: str, 
            imagery_id: str, 
            url: str):
        z = int(zxy.split("/")[0])
        x = int(zxy.split("/")[1])
        y = int(zxy.split("/")[2])

        return cls(
            zxy=zxy,
            imagery_id=imagery_id,
            url=url,
            z=z,
            x=x,
            y=y
        )



class Task(BaseModel):
    complete: bool
    id: int
    imagery_id: str
    queue: int
    submitter_login: Optional[str]
    zxy: str


class Label(BaseModel):
    id: Optional[int]
    project_id: str
    color: str
    name: str
    status: str

