import sys,os
sys.path.insert(0, os.getcwd())
from projectkiwi.connector import Connector
from projectkiwi.models import  Annotation
from projectkiwi.tools import getBboxTileCoords, getAnnotationsForTile, coordsFromPolygon, bboxToPolygon
import numpy as np

from test_basics import TEST_URL


def test_read_annotations():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    annotations = conn.getAnnotations()

    assert len(annotations) >= 1, "Missing Annotations"


def test_read_annotations():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)
    
    project = [project for project in conn.getProjects() if project.name == "default"][0]

    annotations = conn.getAnnotations(project_id=project.id)

    assert len(annotations) >= 1, "Missing Annotations"


def test_annotations_in_tile():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    allAnnotations = conn.getAnnotations(project_id=project.id)

    annotations = getAnnotationsForTile(
            annotations=allAnnotations,
            zxy = "12/1051/1522",
            overlap_threshold=0.2)

    assert len(annotations) > 0, "No annotations found for tile"


def test_get_bboxes_for_tile():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    allAnnotations = conn.getAnnotations(project_id=project.id)

    tile_zxy = "12/1051/1522"
    annotations = getAnnotationsForTile(
            annotations=allAnnotations,
            zxy = tile_zxy,
            overlap_threshold=0.2)

    assert len(annotations) > 0, "No annotations found for tile"

    for annotation in annotations:
        bbox = getBboxTileCoords(annotation.coordinates, tile_zxy)
        assert len(bbox) == 4, "malformed bounding box"


def test_read_predictions():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]
    prediction = Annotation(
        shape="Polygon",
        label_id=374,
        imagery_id="93650ec6508a",
        coordinates=[
            [-87.612448, 41.867452], 
            [-87.605238, 41.867452], 
            [-87.605238, 41.852301], 
            [-87.612448, 41.852301], 
            [-87.612448, 41.867452]],
        confidence = 0.33
    )


    annotation_id = conn.addPrediction(prediction, project.id)
    assert annotation_id, "Failed to add prediction"


    predictions = conn.getPredictions(project_id=project.id)

    assert len(predictions) >= 1, "Missing predictions"


def test_dict_conversion():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    annotation = conn.getAnnotations(project_id=project.id)[0]

    annoDict = dict(annotation)
    newAnnotation = Annotation.from_dict(annoDict)
    assert annotation == newAnnotation, "Bad dict convesion"



def test_add_annotation():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    annotation = Annotation(
        shape="Polygon",
        label_id=374,
        imagery_id="93650ec6508a",
        coordinates=[
            [-87.612448, 41.867452], 
            [-87.605238, 41.867452], 
            [-87.605238, 41.852301], 
            [-87.612448, 41.852301], 
            [-87.612448, 41.867452]]
    )


    annotation_id = conn.addAnnotation(annotation, project.id)
    assert annotation_id, "Failed to add annotation"

def test_add_prediction():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    prediction = Annotation(
        shape="Polygon",
        label_id=374,
        imagery_id="93650ec6508a",
        coordinates=[
            [-87.612448, 41.867452], 
            [-87.605238, 41.867452], 
            [-87.605238, 41.852301], 
            [-87.612448, 41.852301], 
            [-87.612448, 41.867452]],
        confidence = 0.33
    )


    annotation_id = conn.addPrediction(prediction, project.id)
    assert annotation_id, "Failed to add prediction"



def test_remove_all_predictions():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    conn.removeAllPredictions(project.id)
    
    prediction = Annotation(
        shape="Polygon",
        label_id=374,
        imagery_id="93650ec6508a",
        coordinates=[
            [-87.612448, 41.867452], 
            [-87.605238, 41.867452], 
            [-87.605238, 41.852301], 
            [-87.612448, 41.852301], 
            [-87.612448, 41.867452]],
        confidence = 0.33
    )

    annotation_count_1 = len(conn.getAnnotations(project_id=project.id))

    annotation_id = conn.addPrediction(prediction, project.id)
    assert annotation_id, "Failed to add prediction"

    annotation_count_2 = len(conn.getAnnotations(project_id=project.id))

    assert annotation_count_2 - annotation_count_1 == 1, "Failed to add prediction"

    conn.removeAllPredictions(project.id)

    annotation_count_3 = len(conn.getAnnotations(project_id=project.id))

    assert (annotation_count_3 == annotation_count_1 and \
         annotation_count_3 == annotation_count_2 - 1), "Failed to remove predictions"
    


def test_add_bbox_prediction():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    tile_zxy = "14/4202/6087"

    predictions = [annotation for annotation in conn.getAnnotations(project_id=project.id) \
        if annotation.confidence != None]

    predictionsInTile = getAnnotationsForTile(
            annotations=predictions,
            zxy = tile_zxy,
            overlap_threshold=0.2)
    
    latLngPoly = coordsFromPolygon(bboxToPolygon(100, 100, 200, 200), tile_zxy, 256)

    prediction = Annotation(
        shape="Polygon",
        label_id=374,
        imagery_id="93650ec6508a",
        coordinates=latLngPoly,
        confidence = 0.66
    )

    annotation_id = conn.addPrediction(prediction, project.id)
    assert annotation_id, "Failed to add prediction"

    predictions = [annotation for annotation in conn.getAnnotations(project_id=project.id) \
        if annotation.confidence != None]

    predictionsInTile2 = getAnnotationsForTile(
            annotations=predictions,
            zxy = tile_zxy,
            overlap_threshold=0.2)
    
    assert len(predictionsInTile2) == len(predictionsInTile) + 1, "Failed to add prediction"


def test_get_bboxes_for_tile():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    allAnnotations = conn.getAnnotations(project_id=project.id)

    tile_zxy = "12/1051/1522"
    annotations = getAnnotationsForTile(
            annotations=allAnnotations,
            zxy = tile_zxy,
            overlap_threshold=0.2)

    assert len(annotations) > 0, "No annotations found for tile"

    for annotation in annotations:
        bbox = getBboxTileCoords(annotation.coordinates, tile_zxy)
        assert len(bbox) == 4, "malformed bounding box"