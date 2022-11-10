import sys,os
sys.path.insert(0, os.getcwd())
from projectkiwi.connector import Connector
from projectkiwi.tools import splitZXY
import numpy as np
import requests

TEST_URL = "https://sandbox.project-kiwi.org/"

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

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    imagery = conn.getImagery(project_id=project.id)

    assert len(imagery) >= 3, "Missing Imagery"


def test_get_tiles():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]


    imagery = conn.getImagery(project_id=project.id)

    imagery_id = None
    for layer in imagery:
        if layer.name == "pytest":
            imagery_id = layer.id
            break
    
    assert not imagery_id is None, "no test imagery found"

    tiles = conn.getTileList(imagery_id, project.id, 13)

    assert len(tiles) > 0, "No tiles found"


def test_get_tile():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    imagery = conn.getImagery(project_id=project.id)

    imagery_id = None
    for layer in imagery:
        if layer.name == "pytest":
            imagery_id = layer.id
            break
    
    assert not imagery_id is None, "no test imagery found"

    tileList = conn.getTileList(imagery_id, project.id, 13)

    assert len(tileList) > 0, "No tiles found"

    z,x,y = splitZXY(tileList[-1].zxy)
    tile = conn.getTile(imagery_id, z, x, y)
    assert isinstance(tile, np.ndarray), "Failed to load tile"
    assert len(tile.shape) == 3, "bad size for tile"



def test_read_super_tile():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    imagery = conn.getImagery(project_id=project.id)

    pytest_layer = [layer for layer in imagery if layer.name == "pytest"][0]
    assert not pytest_layer is None, "no test imagery found"

    ZXY = "13/2101/3045"
    z,x,y = splitZXY(ZXY)
    smallTile = conn.getTile(pytest_layer.id, z,x,y)
    assert np.mean(smallTile) > 0, "Test tile not present"
    
    superTile = conn.getSuperTile(
            zxy = ZXY, 
            imagery_id = pytest_layer.id,
            max_zoom = 14,
            padding = 0)

    assert isinstance(superTile, np.ndarray), "Failed to load tile"
    assert len(superTile.shape) == 3, "bad size for tile"

    assert abs(np.mean(superTile) - np.mean(smallTile)) < 5, "supertile and small tile not matching"


def test_read_super_tile_padded():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    imagery = conn.getImagery(project_id=project.id)

    pytest_layer = [layer for layer in imagery if layer.name == "pytest"][0]
    assert not pytest_layer is None, "no test imagery found"

    ZXY = "13/2101/3045"
    z,x,y = splitZXY(ZXY)
    smallTile = conn.getTile(pytest_layer.id, z,x,y)
    assert np.mean(smallTile) > 0, "Test tile not present"
    
    superTile = conn.getSuperTile(
            zxy = ZXY, 
            imagery_id = pytest_layer.id,
            max_zoom = 14,
            padding = 20)

    assert isinstance(superTile, np.ndarray), "Failed to load tile"
    assert len(superTile.shape) == 3, "bad size for tile"

    assert superTile.shape[0] == superTile.shape[1] == 512+2*20, "Padded image is wrong size"



def test_add_imagery():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    before_imagery = conn.getImagery(project_id=project.id)

    url = "https://project-kiwi-web.s3.amazonaws.com/example-imagery/sammamish_river_ortho.tif"
    response = requests.get(url, stream=True)

    with open("sammamish_river_ortho.tif", "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    imagery_id = conn.addImagery("sammamish_river_ortho.tif", "sammamish river", project.id)

    imagery = conn.getImagery(project_id=project.id)
    assert imagery_id in [layer.id for layer in imagery], "Failed to upload imagery"
    
   

def test_get_imagery_url():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    imagery = conn.getImagery(project_id=project.id)

    for image in imagery:
        assert image.url == conn.getImageryUrl(image.id, project.id), "Failed to get imagery url"

    assert len(imagery) > 0, "No imagery, test invalid"


def test_read_labels():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    labels = conn.getLabels(project_id=project.id)

    assert len(labels) >= 1, "Missing Labels"

def test_add_label():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    project = [project for project in conn.getProjects() if project.name == "default"][0]

    label = conn.addLabel("labelName", project.id)
    assert label.name == "labelName", "Could not create label"
    assert label.id is not None, "Could not create label"


    label = conn.addLabel("labelName", project.id, color="rgb(0, 100, 200)")
    assert label.name == "labelName", "Could not create label"
    assert label.id is not None, "Could not create label"
    assert label.color == "rgb(0, 100, 200)", "Wrong color"
