# project-kiwi

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

conn.getImagery()

# Result:
# [{'id': 'fff907e728f7', 'project': '85c5eb85e76d', 'name': 'example', 'url': 'https://project-kiwi-tiles.s3.amazonaws.com/fff907e728f7/{z}/{x}/{y}', 'ref': 'False', 'status': 'live', 'invert_y': 1}]
```

### Notes
Visit https://project-kiwi.org/manage/ to get an api key (registration required).