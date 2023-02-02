

Connecting To the API
---------------------

To work with project kiwi via the python API, you will need to register and get your API key from `here <https://projectkiwi.io/account/#developer>`__.

.. code:: python

  # import the Connector class
  from projectkiwi.connector import Connector

  # connect to the API
  conn = Connector(key="****key****")


----


Uploading Data
--------------

Our platform is designed to work with GeoTIFF files, you can find some examples `here <https://projectkiwi.io/developer/uploading_imagery/>`__. Either upload your data to a project through the web interface or via the API:

.. code:: python

  # get all the projects
  projects = conn.getProjects()

  # add the data to the first project
  imagery_id = conn.addImagery("./path/to/mydata.tif", "My layer Name", projects[0].id)


----

Reading Tiles as Numpy Arrays
-----------------------------

.. image:: https://projectkiwi.io/imgs/figs/getTile.png
  :width: 300pt
  :align: center


.. code:: python
  
  import matplotlib.pyplot as plt

  project = conn.getProjects()[0]

  imagery = conn.getImagery(project.id)[0]

  # get a list of valid tiles
  tile = conn.getTileList(imagery.id, project.id, zoom=17)[0]

  # download the tile in numpy format
  numpy_tile = conn.getTile(tile.imagery_id, tile.z, tile.x, tile.y)

  # show the tile
  plt.imshow(numpy_tile)




----

Reading Annotations
-----------------------------

.. code:: python
  
  # choose a project
  project = projects[0]

  # read all annotations in a project
  annotations = conn.getAnnotations(project.id)

  # get annotations as geojson
  print(annotations[0].geoJSON())

  # result
  {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [-87.612448, 41.867452],
            [-87.605238, 41.867452],
            [-87.605238, 41.852301],
            [-87.612448, 41.852301],
            [-87.612448, 41.867452]
        ]
    },
    "properties": {
        "label_id": 374,
        "name": "airport"
    }
  }