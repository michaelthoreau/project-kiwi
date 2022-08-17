from pydantic import BaseModel
from typing import List, Optional


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
            annotation_id = data['id']

        
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