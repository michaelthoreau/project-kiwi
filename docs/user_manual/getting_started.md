# Getting Started

Below are a few examples of some basic usage to get started with.


### Installation
```Bash
pip install projectkiwi
```

--- 

### Getting Started
Register and get your api key from [https://project-kiwi.org/api_key/](https://project-kiwi.org/api_key/)
```Python
import projectkiwi

# register and get your api key from https://project-kiwi.org/api_key/
conn = projectkiwi.connector("****api_key****")

imagery = conn.getImagery()

# Result:
# [{'id': 'fff907e728f7', 'project': '85c5eb85e76d', 'name': 'example', 'url': 'https://project-kiwi-tiles.s3.amazonaws.com/fff907e728f7/{z}/{x}/{y}', 'ref': 'False', 'status': 'live', 'invert_y': 1}]
```

---

### List Tiles
```Python
import projectkiwi

conn = projectkiwi.connector("****api_key****")

tiles = conn.getTiles("daac5f5b83b8")
print("tiles: {}".format(len(tiles)))
# tiles: 10424

print("top5: ", tiles[:5])
# top5:  
# [
#   {'url': 'https://project-kiwi-tiles.s3.amazonaws.com/daac5f5b83b8/1/0/0', 'zxy': '1/0/0'}, 
#   {'url': 'https://project-kiwi-tiles.s3.amazonaws.com/daac5f5b83b8/2/0/1', 'zxy': '2/0/1'}, 
#   {'url': 'https://project-kiwi-tiles.s3.amazonaws.com/daac5f5b83b8/3/1/3', 'zxy': '3/1/3'}, 
#   {'url': 'https://project-kiwi-tiles.s3.amazonaws.com/daac5f5b83b8/4/2/6', 'zxy': '4/2/6'}, 
#   {'url': 'https://project-kiwi-tiles.s3.amazonaws.com/daac5f5b83b8/5/5/12', 'zxy': '5/5/12'}
# ]
```

---

### Tiles as numpy arrays

<!-- ![example](figs/example.png) -->
![example](https://raw.githubusercontent.com/michaelthoreau/projectkiwi/main/figs/example.png)


```Python
import projectkiwi
import matplotlib.pyplot as plt

conn = projectkiwi.connector("****api_key****")

tileDict = conn.getTileDict("daac5f5b83b8")
plt.imshow(conn.getTile(tileDict['16/11658/24927']))
plt.title('16/11658/24927')
```

---

### Adding Imagery

```Python
imageryId = conn.addImagery("../odm_orthophoto.tif", "python upload")

while True:
    status = conn.getImageryStatus(imageryId)
    print("status: ", status)
    if status == "live":
        break
    time.sleep(1.0)

# Result
# status:  awaiting processing
# status:  processing
# status:  normalising
# status:  normalisation complete
# status:  normalisation complete
# status:  staging tile: 1/16
# status:  staging tile: 1/16
# status:  live upto zoom 16
# status:  live upto zoom 16
# status:  live upto zoom 16
# status:  live upto zoom 16
# status:  staging tile: 1/1834
# status:  staging tile: 301/1834
# status:  staging tile: 601/1834
# status:  staging tile: 901/1834
# status:  staging tile: 1201/1834
# status:  staging tile: 1501/1834
# status:  staging tile: 1801/1834
# status:  live
```


### Notes
Visit https://project-kiwi.org/api_key/ to get an api key (registration required).

See a list of supported formats here (creation column):
https://gdal.org/drivers/raster/index.html
