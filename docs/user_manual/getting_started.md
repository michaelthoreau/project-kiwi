# Getting Started

Below are a few examples of some basic usage to get started with the API.
### Installation
```Bash
pip install projectkiwi -y
```
---

### Getting Started
Register and get your api key from [https://project-kiwi.org/account/](https://project-kiwi.org/account/)
```python
from projectkiwi.connector import Connector

conn = Connector(key="****key****", url="https://sandbox.project-kiwi.org/api/")

imagery = conn.getImagery()
print(imagery)
```

---

### Add some data

Let's download some satellite imagery of chicago!
```Bash
wget https://download.osgeo.org/geotiff/samples/spot/chicago/SP27GTIF.TIF
```

Upload to project kiwi
```Python
imageryId = conn.addImagery("SP27GTIF.TIF", "python upload")
import time
while True:
    status = conn.getImageryStatus(imageryId)
    print("status: ", status)
    if status == "live":
        break
    time.sleep(0.5)
```

---

### List Tiles
```Python
tiles = conn.getTileList("2bdf45d8b8da", 13)
print("tiles: {}".format(len(tiles)))
print("top5: ", tiles[:5])
```

---

### Tiles as numpy arrays
```python
import matplotlib.pyplot as plt

tile = conn.getTileList("2bdf45d8b8da", 13)[0]
img = conn.getTile(tile['url'])
plt.imshow(img[:,:,0], cmap="gray")
plt.title(tile['zxy'])
```


See a list of supported raster imagery formats here (creation column):
https://gdal.org/drivers/raster/index.html
