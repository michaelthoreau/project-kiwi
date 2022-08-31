import sys,os
sys.path.insert(0, os.getcwd())
from projectkiwi.connector import Connector
import numpy as np

TEST_URL = "https://sandbox.project-kiwi.org/api/"

def test_conn():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    assert not conn is None, "Failed to create connector"


def test_get_projects():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    projects = conn.getProjects()
    print("Projects: ", projects)

    assert len(projects) > 0, "No projects found"

def test_get_imagery():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = conn.getProjects()[0]

    imagery = conn.getImagery(project_id=project.id)

    assert len(imagery) >= 3, "Missing Imagery"


def test_get_tiles():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = conn.getProjects()[0]

    imagery = conn.getImagery(project_id=project.id)

    imagery_id = None
    for layer in imagery:
        if layer.name == "pytest":
            imagery_id = layer.id
            break
    
    assert not imagery_id is None, "no test imagery found"

    tiles = conn.getTileList(imagery_id, 13)

    assert len(tiles) > 0, "No tiles found"


def test_read_tile():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = conn.getProjects()[0]

    imagery = conn.getImagery(project_id=project.id)

    imagery_id = None
    for layer in imagery:
        if layer.name == "pytest":
            imagery_id = layer.id
            break
    
    assert not imagery_id is None, "no test imagery found"

    tileList = conn.getTileList(imagery_id, 13)

    assert len(tileList) > 0, "No tiles found"

    tile = conn.getTile(tileList[-1].url)
    assert isinstance(tile, np.ndarray), "Failed to load tile"
    assert len(tile.shape) == 3, "bad size for tile"



def test_read_super_tile():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = conn.getProjects()[0]

    imagery = conn.getImagery(project_id=project.id)

    pytest_layer = [layer for layer in imagery if layer.name == "pytest"][0]
    assert not pytest_layer is None, "no test imagery found"
    
    superTile = conn.getSuperTile(
            zxy         = "10/262/380", 
            url         = pytest_layer.url,
            max_zoom    = pytest_layer.max_zoom)

    assert isinstance(superTile, np.ndarray), "Failed to load tile"
    assert len(superTile.shape) == 3, "bad size for tile"


