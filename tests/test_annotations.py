import sys,os

from sqlalchemy import over
sys.path.insert(0, os.getcwd())
from projectkiwi.connector import Connector
import numpy as np

from test_basics import TEST_URL

from projectkiwi.tools import getBboxTileCoords

def test_read_annotations():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    annotations = conn.getAnnotations()

    assert len(annotations) >= 1, "Missing Annotations"



def test_read_annotations():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    annotations = conn.getAnnotations()

    assert len(annotations) >= 1, "Missing Annotations"


def test_annotations_in_tile():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = conn.getProjects()[0]

    allAnnotations = conn.getAnnotations(project=project)

    annotations = conn.getAnnotationsForTile(
            annotations=allAnnotations,
            zxy = "12/1051/1522",
            overlap_threshold=0.2)

    assert len(annotations) > 0, "No annotations found for tile"



def test_get_bboxes_for_tile():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = conn.getProjects()[0]

    allAnnotations = conn.getAnnotations(project=project)

    tile_zxy = "12/1051/1522"
    annotations = conn.getAnnotationsForTile(
            annotations=allAnnotations,
            zxy = tile_zxy,
            overlap_threshold=0.2)

    assert len(annotations) > 0, "No annotations found for tile"

    for annotation in annotations:
        bbox = getBboxTileCoords(annotation.coordinates, tile_zxy)
        assert len(bbox) == 4, "malformed bounding box"