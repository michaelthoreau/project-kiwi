from projectkiwi.tools import (
        bboxFromCoords,
        getAnnotationsForTile,
        latLngToImgCoords,
        maskFromPolygon,
        bbox_iou)

from PIL import Image
from pathlib import Path
import numpy as np
import numpy as np
import torch
from PIL import Image
import torch
from PIL import Image
from typing import List



class ProjectKiwiDataSet(object):

    def imgToTensor(self, img):
        if img.shape[-1] == 2:
            img = np.dstack((img[:,:,0], img[:,:,0], img[:,:,0]))
        assert img.shape[-1] == 3, f"Image must have three channels. expected: [h, w, 3] got: {img.shape}"
        img = torch.as_tensor(np.array(img), dtype=torch.float32)/255

        return img.permute(2, 0, 1)

    def getTaskTile(self, task):
        imageFile = str(self.cache_location / f"{self.imagery_id}" / f"padding_{self.padding}" / Path(task.zxy + ".png"))
        if not Path(imageFile).exists():
            # we can request a "super tile", which covers the same area but is at a higher resolution than a standard tile
            tile = self.conn.getSuperTile(self.imagery_id, task.zxy, self.max_zoom, self.padding)

            if tile.shape[2] == 4:
                tile = tile[:,:,:3]
            im = Image.fromarray(tile)
            Path(imageFile).parent.mkdir(parents=True, exist_ok=True)
            im.save(imageFile)
        else:
            im = Image.open(imageFile)
            tile = np.array(im)
        return tile

    def getAnnotations(self, project_id):
        annotationsAndPredictions = self.conn.getAnnotations(project_id)

        self.label_ids = []
        self.label_names = []
        for annotation in annotationsAndPredictions:
            if not annotation.label_id in self.label_ids:
                self.label_names.append(annotation.label_name)
                self.label_ids.append(annotation.label_id)

        # filter out predictions, we dont want to train on these
        self.annotations = [annotation for annotation in annotationsAndPredictions \
                    if annotation.confidence is None and annotation.shape == "Polygon"]


    def __init__(self, conn, tasks, project_id, imagery_id, max_zoom, 
            cache_location=Path("./cache"),
            padding = 0,
            inference = False,
            make_masks = True,
            transforms = None):
        self.conn = conn
        self.tasks = tasks
        self.imagery_id = imagery_id
        self.max_zoom = max_zoom
        self.cache_location = cache_location
        cache_location.mkdir(exist_ok=True)
        self.padding = padding
        self.inference = inference
        self.getAnnotations(project_id)
        self.make_masks = make_masks
        self.transforms = transforms
        


    def __getitem__(self, idx):
        task = self.tasks[idx]
        tile = self.getTaskTile(task)
        
        img = self.imgToTensor(tile)
        
        if self.inference == True:
            target = None
        else:
            annotationsForTile = getAnnotationsForTile(self.annotations, task.zxy, overlap_threshold=0.9)

            labels = []
            boxes = []
            isCrowd = []
            if self.make_masks:
                masks = np.zeros((len(annotationsForTile), tile.shape[0], tile.shape[1]))
            for i,annotation in enumerate(annotationsForTile):
                boxes.append(bboxFromCoords(annotation.coordinates, task.zxy, tile.shape[0], clip=False))

                # reserve label 0 for background
                labels.append(self.label_names.index(annotation.label_name) + 1)
                isCrowd.append(0)
                
                if self.make_masks:
                    poly = latLngToImgCoords(annotation.coordinates, task.zxy, tile.shape[0])
                    poly = [(x, y) for x,y in poly]
                    mask = maskFromPolygon(poly, tile.shape[0], tile.shape[1])
                    masks[i,:,:] = mask
               

            boxes = torch.as_tensor(boxes, dtype=torch.float32)
            labels = torch.as_tensor(labels, dtype=torch.int64)
            image_id = torch.tensor([idx])

            # empty targets for tiles without annotations
            if len(boxes) == 0:
                area = torch.zeros((1,), dtype=torch.int64)
                boxes = torch.zeros((0, 4), dtype=torch.float32)
            else:
                area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0])
            
            isCrowd = torch.as_tensor(isCrowd, dtype=torch.int64)

            target = {
                "boxes": boxes,
                "labels": labels,
                "image_id": image_id,
                "area": area,
                "iscrowd": isCrowd
            }

            if self.make_masks:
                target['masks'] = torch.as_tensor(masks, dtype=torch.uint8)

            if self.transforms is not None:
                img, target = self.transforms(img, target)

        return img, target, task

    def __len__(self):
        return len(self.tasks)




def scoreThresholding(boxes: List, scores: List, class_ids: List, masks: List = None, threshold = 0.1):
    """ apply a score threshold a list of boxes etc

    Args:
        boxes (List): bounding boxes for the objects
        scores (List): scores between 0 and 1
        class_ids (List): class ids
        masks (List, optional): masks if there is a mask-rcnn output. Defaults to None.
        threshold (float, optional): the threshold to apply, objects with scores below this omitted. Defaults to 0.1.

    Returns:
        _type_: the boxes, scores, ids and optionally masks
    """    
    returnBoxes, returnScores, returnIds = ([], [], [])
    if masks is None:
        returnMasks = None
    else:
        returnMasks = []

    for i, (box, score, class_id) in enumerate(zip(boxes, scores, class_ids)):

        if score > threshold:
            returnBoxes.append(box)
            returnScores.append(score)
            returnIds.append(class_id)
            if not masks is None:
                returnMasks.append(masks[i])

    return returnBoxes, returnScores, returnIds, returnMasks



def boxSizeFiltering(boxes: List, scores: List, class_ids: List, masks: List = None, min_side_length = 5):
    """ apply a filter on the smallest allowable side length for bounding boxes

    Args:
        boxes (List): bounding boxes for the objects
        scores (List): scores between 0 and 1
        class_ids (List): class ids
        masks (List, optional): masks if there is a mask-rcnn output. Defaults to None.
        min_side_length (int, optional): minimum allowed side length in pixels. Defaults to 5.

    Returns:
        _type_: the boxes, scores, ids and optionally masks
    """    
    returnBoxes, returnScores, returnIds = ([], [], [])
    if masks is None:
        returnMasks = None
    else:
        returnMasks = []

    for i, (box, score, class_id) in enumerate(zip(boxes, scores, class_ids)):
        [x1, y1, x2, y2] = [int(box[0]), int(box[1]), int(box[2]), int(box[3])]

        if y2-y1 >= min_side_length and x2-x1 >= min_side_length:
            returnBoxes.append(box)
            returnScores.append(score)
            returnIds.append(class_id)
            if not masks is None:
                returnMasks.append(masks[i])
    return returnBoxes, returnScores, returnIds, returnMasks




def nonMaximumSuppression(boxes: List, scores: List, class_ids: List, masks: List = None,
    iou_threshold = 0.3):
    """ apply non-maximum suppression to the output of an object detector

    Args:
        boxes (List): bounding boxes for the objects
        scores (List): scores between 0 and 1
        class_ids (List): class ids
        masks (List, optional): masks if there is a mask-rcnn output. Defaults to None.
        iou_threshold (float, optional): maximum overlap permitted, objects with a greater overlap with a higher confidence box will be omitted. Defaults to 0.3.

    Returns:
        _type_: the boxes, scores, ids and optionally masks
    """   

    returnBoxes, returnScores, returnIds = ([], [], [])
    if masks is None:
        returnMasks = None
    else:
        returnMasks = []

    for i, (box, score, class_id) in enumerate(zip(boxes, scores, class_ids)):
        skip = False
        for j, (box2, score2) in enumerate(zip(boxes, scores)):
            if i != j and score2 > score:
                if bbox_iou(box, box2) > iou_threshold:
                    skip = True
        
        if not skip: 
            returnBoxes.append(box)
            returnScores.append(score)
            returnIds.append(class_id)
            if not masks is None:
                returnMasks.append(masks[i])

    return returnBoxes, returnScores, returnIds, returnMasks

