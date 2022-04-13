# projectkiwi

Tools to interact with project-kiwi.org

---

### Installation
```Bash
pip install projectkiwi
```

--- 

### Getting Started
```Python
import projectkiwi

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

![example](figs/example.png)

```Python
import projectkiwi
import matplotlib.pyplot as plt

conn = projectkiwi.connector("****api_key****")

tileDict = conn.getTileDict("daac5f5b83b8")
plt.imshow(conn.getTile(tileDict['16/11658/24927']))
plt.title('16/11658/24927')
```


### Notes
Visit https://project-kiwi.org/manage/ to get an api key (registration required).