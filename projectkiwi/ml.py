import sys
sys.path.append('../../projectkiwi/')

import projectkiwi
from projectkiwi.tools import (
        coordsFromPolygon,
        bboxToPolygon,
        yx_to_xy)
from projectkiwi.data import ProjectKiwiDataSet, scoreThresholding, boxSizeFiltering, nonMaximumSuppression

from tqdm import tqdm
from pathlib import Path
import numpy as np
from random import shuffle
import numpy as np
import torch
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
import sys
import torch
import torchvision.models.detection.mask_rcnn
import threading


from skimage import measure
from skimage.measure import approximate_polygon



class BaseDetector(object):
    """Base detector model. This class can be instantiated for training/running detectors on data directly from projectkiwi.io

    Args:
        conn (Connector): A connection object from projectkiwi.connector.
        project_id (str): Id of the project to work with.
        imagery_id (str): Id of the imagery to get tiles from.
        max_zoom (int): Maximum zoom level to request data for, higher zoom will result in higher resolution inputs.
        tile_padding (int): Number of additional pixels to use request on each side of the tile.
        cache_location (str): Downloaded tiles and model checkpoints will be stored here.
        batch_size (int, optional): Batch size. Defaults to 4.
        model_load_path (str, optional): Path to a trained model to load. Defaults to None.
        device (str, optional): Device descriptor to use for training/inference e.g. 'cuda'. Defaults to None.
        transforms (_type_, optional): Transforms to use, from projectkiwi.transforms. Defaults to None.

    Raises:
        ValueError: If a model is specified to load but it cant be found/loaded, a valueError will be raised.
    """       

    def threadAddPrediction(self, prediction):
        self.conn.addPrediction(prediction, self.project_id)

    @staticmethod
    def collate_fn(batch):
        return tuple(zip(*batch))

    def get_model(self, num_classes, weights: str = "DEFAULT"):
        raise NotImplementedError("Please use a child class of this one")
    
    def load_model_from_path(self, path: Path):
        state = torch.load(path)
        print(f"Loading model from file: {path}")
        self.model = self.get_model(state['num_classes'], weights=None)
        self.model.load_state_dict(state['state_dict'])
        self.class_names = state['class_names']


    def __init__(self, 
            conn, 
            project_id, 
            imagery_id, 
            max_zoom, 
            tile_padding, 
            cache_location, 
            batch_size = 4, 
            model_load_path = None, 
            device = None, 
            transforms = None):     

        self.conn = conn
        self.project_id = project_id
        self.imagery_id = imagery_id
        self.max_zoom = max_zoom
        self.tile_padding = tile_padding
        self.model = None
        self.cache_location = Path(cache_location)
        self.batch_size = batch_size
        self.class_names = None
        self.label_ids = None
        self.transforms = transforms
        self.model_load_path = model_load_path
        
        if device != None:
            self.device = torch.device(device)
            print(f"Using device: {self.device}")
        else:
            self.device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
            print(f"Using device: {self.device}")

        self.model_save_path = Path(self.cache_location / f"{self.project_id}_{self.model_name}.kiwi")
        if self.model_load_path != None:
            if Path(self.model_load_path).exists():
                self.load_model_from_path(self.model_load_path)
            else:
                raise ValueError(f"No model found in location: {self.model_load_path}")



    def train(self, tasks, max_epochs: int = 100, resume=True, patience: int = 5) -> Path:
        """Train the object detection model on data and annotations from projectkiwi.io.

        Args:
            tasks (List[Task]): List of tasks to use for training.
            max_epochs (int, optional): Maximum number of epochs to train for.. Defaults to 100.
            resume (bool, optional): Resume training. Defaults to True.
            patience (int, optional): Number of epochs to train for without any improvement. Defaults to 5.

        Returns:
            Path: Path to the trained model checkpoint.

        Example:
            
            >>> conn = Connector(API_KEY)
            >>> detector = ObjectDetectionModel(conn,
            ...    project_id = PROJECT_ID, 
            ...    imagery_id = IMAGERY_ID, 
            ...    max_zoom = MAX_ZOOM, 
            ...    tile_padding = 50, 
            ...    cache_location = "./cache",
            ...    batch_size=4)
            >>> tasks = conn.getTasks(QUEUE_ID)
            >>> complete_tasks = [task for task in tasks if task.complete == True]
            >>> detector.train(complete_tasks, max_epochs = 20)
        """        

        print(f"Training for up to {max_epochs} epochs.")
        shuffle(tasks)

        assert len(tasks) > 0, "Please complete at least one task before training"

        num_examples = len(tasks)
        train_size = round(num_examples*0.8)
        test_size = num_examples - train_size

        dataset_train = ProjectKiwiDataSet(
                self.conn,
                tasks[:train_size],
                self.project_id,
                self.imagery_id,
                self.max_zoom,
                self.cache_location,
                make_masks=self.masks_required,
                transforms = self.transforms)

        data_loader_train = torch.utils.data.DataLoader(
                dataset_train,
                batch_size=self.batch_size,
                shuffle=True,
                num_workers=4,
                collate_fn=self.collate_fn)

        if test_size > 0:
            dataset_test = ProjectKiwiDataSet(
                    self.conn,
                    tasks[train_size:],
                    self.project_id,
                    self.imagery_id,
                    self.max_zoom,
                    self.cache_location,
                    make_masks=self.masks_required)
            data_loader_test = torch.utils.data.DataLoader(
                dataset_test,
                batch_size=self.batch_size,
                shuffle=True,
                num_workers=4,
                collate_fn=self.collate_fn)

        self.class_names = dataset_train.label_names
        self.label_ids = dataset_train.label_ids

        if self.model is None and resume is True:
            if not self.model_load_path is None:
                if Path(self.model_load_path).exists():
                    self.load_model_from_path(self.model_load_path)
            elif Path(self.model_save_path).exists():
                self.load_model_from_path(self.model_save_path)
            else:
                print("Initialising model with generic pre-trained weights.")
                self.model = self.get_model(num_classes = len(self.class_names)+1)
        elif resume is False:
            print("Initialising model with generic pre-trained weights.")
            self.model = self.get_model(num_classes = len(self.class_names)+1)
        self.model.to(self.device)

        # construct an optimizer
        params = [p for p in self.model.parameters() if p.requires_grad]
        optimizer = torch.optim.SGD(params, lr=0.001, momentum=0.9, weight_decay=0.0005)

        val_history = []


        for epoch in range(max_epochs):
            
            self.model.train()
            train_losses = []
            for images, targets, _ in data_loader_train:
                images = list(image.to(self.device) for image in images)
                targets = [{k: v.to(self.device) for k, v in t.items()} for t in targets]
                loss_dict = self.model(images, targets)
                losses = sum(loss for loss in loss_dict.values())
                train_losses.append(losses.item())
                
                optimizer.zero_grad()
                losses.backward()
                optimizer.step()

            train_loss = np.mean(train_losses)

            
            val_losses = []
            if test_size > 0:
                for images, targets, _ in data_loader_test:
                    images = list(image.to(self.device) for image in images)
                    targets = [{k: v.to(self.device) for k, v in t.items()} for t in targets]
                    loss_dict = self.model(images, targets)
                    val_losses.append(sum(loss for loss in loss_dict.values()).item())
                
                val_loss = np.mean(val_losses)
                
                val_history.append(val_loss)
                if len(val_history) >= patience:
                    if np.min(val_history[-patience:]) > np.min(val_history):
                        print("stagnation detected, ending training!")
                        break

                print(f"Epoch {epoch+1}  Train loss: {train_loss:2.3f}  Val loss: {val_loss:2.3f}")
        
        print(f"Saving model to: {self.model_save_path}")
        state = {
            'num_classes': len(dataset_train.label_names)+1,
            'state_dict': self.model.state_dict(),
            'class_names': self.class_names
        }
        torch.save(state, self.model_save_path)

        return self.model_save_path

    
    def predict(self, tasks, remove_preds: bool = True):
        """Run prediction on a set of tasks on project-kiwi.org, and upload any predictions.

        Args:
            tasks (_type_): Tasks to run the model on. e.g. tasks in a queue.
            remove_preds (bool, optional): Remove all predictions in a project. Defaults to True.

        Example:
            >>> conn = Connector(API_KEY)
            >>> detector = ObjectDetectionModel(conn,
            ...    project_id = PROJECT_ID, 
            ...    imagery_id = IMAGERY_ID, 
            ...    max_zoom = MAX_ZOOM, 
            ...    tile_padding = 50, 
            ...    cache_location = "./cache",
            ...    model_load_path="model.kiwi",
            ...    batch_size=4)
            >>> tasks = conn.getTasks(QUEUE_ID)
            >>> incomplete_tasks = [task for task in tasks if task.complete == False]
            >>> detector.predict(incomplete_tasks)
        """        
        
        if remove_preds:
            print("Removing all predictions from project.")
            self.conn.removeAllPredictions(self.project_id)

        if self.label_ids is None:
            self.label_ids = []

            # get/make label ids for labels the model was trained on.
            labels = self.conn.getLabels(self.project_id)
            for class_name in self.class_names:
                label_id = None
                for label in labels:
                    if label.name == class_name:
                        label_id = label.id
                        break
                if label_id is None:
                    print(f"Creating label for: {class_name}")
                    label = self.conn.addLabel(
                            project_id = self.project_id,
                            name = class_name)
                    self.label_ids.append(label.id)
                else:
                    self.label_ids.append(label.id)


        dataset = ProjectKiwiDataSet(self.conn, tasks, self.project_id, self.imagery_id, self.max_zoom, self.cache_location, self.tile_padding, inference=True, make_masks=False)
        data_loader_inference = torch.utils.data.DataLoader(dataset, batch_size=self.batch_size, shuffle=False, num_workers=4, collate_fn=self.collate_fn)

        self.model.to(self.device)
        self.model.eval()


        for images, _, tasks in tqdm(data_loader_inference, desc="Doing inference"):
            images = list(image.to(self.device) for image in images)
            results = self.model(images)
            for result, task in zip(results, tasks):

                tile_size = 256*2**(self.max_zoom - int(projectkiwi.tools.splitZXY(task.zxy)[0]))
                class_ids = result['labels'].detach().cpu().numpy()
                boxes = result['boxes'].detach().cpu().numpy()
                scores = result['scores'].detach().cpu().numpy()
                if self.masks_required:
                    masks = result['masks'].detach().cpu().numpy()
                else:
                    masks = None
                boxes, scores, class_ids, masks = scoreThresholding(boxes, scores, class_ids, masks)
                boxes, scores, class_ids, masks = boxSizeFiltering(boxes, scores, class_ids, masks)
                boxes, scores, class_ids, masks = nonMaximumSuppression(boxes, scores, class_ids, masks)
                
                if self.masks_required:
                    for box, score, class_id, mask in zip(boxes, scores, class_ids, masks):
                        contours = measure.find_contours(mask[0,:,:], 0.5)
                        if len(contours) == 0:
                            continue
                        contour = contours[0].astype(int)
                        approx_contour = yx_to_xy(approximate_polygon(contour, tolerance=5))

                        if len(approx_contour) < 4:
                            continue
                        
                        poly_latlng = coordsFromPolygon(approx_contour, task.zxy, tile_size, self.tile_padding)

                        
                        if poly_latlng[0] != poly_latlng[-1]:
                            continue

                        prediction = projectkiwi.models.Annotation(
                            shape="Polygon",
                            label_id=self.label_ids[class_id-1],
                            imagery_id=self.imagery_id,
                            coordinates=poly_latlng,
                            confidence = score)

                        threading.Thread(target=self.threadAddPrediction, args=(prediction,)).start()
                else:
                    for box, score, class_id in zip(boxes, scores, class_ids):
                        x1, y1, x2, y2 = [int(box[0]), int(box[1]), int(box[2]), int(box[3])]

                        latLngPoly = coordsFromPolygon(bboxToPolygon(x1, y1, x2, y2), task.zxy, tile_size, self.tile_padding)

                        # get the prediction ready
                        prediction = projectkiwi.models.Annotation(
                            shape="Polygon",
                            label_id=self.label_ids[class_id-1],
                            imagery_id=self.imagery_id,
                            coordinates=latLngPoly,
                            confidence = score)

                        # add the prediction (in a new thread for speeed)
                        threading.Thread(target=self.threadAddPrediction, args=(prediction,)).start()



class InstanceSegmentationModel(BaseDetector):
    """Mask R-CNN model. This class can be instantiated for training/running instance segmentation models on data directly from project-kiwi.org.

    Args:
        conn (Connector): A connection object from projectkiwi.connector.
        project_id (str): Id of the project to work with.
        imagery_id (str): Id of the imagery to get tiles from.
        max_zoom (int): Maximum zoom level to request data for, higher zoom will result in higher resolution inputs.
        tile_padding (int): Number of additional pixels to use request on each side of the tile.
        cache_location (str): Downloaded tiles and model checkpoints will be stored here.
        batch_size (int, optional): Batch size. Defaults to 4.
        model_load_path (str, optional): Path to a trained model to load. Defaults to None.
        device (str, optional): Device descriptor to use for training/inference e.g. 'cuda'. Defaults to None.
        transforms (_type_, optional): Transforms to use, from projectkiwi.transforms. Defaults to None.

    Raises:
        ValueError: If a model is specified to load but it cant be found/loaded, a valueError will be raised.
    """

    masks_required = True
    model_name = "instance_seg"

    def get_model(self, num_classes, weights: str = "DEFAULT"):
        # load an instance segmentation model pre-trained on COCO
        model = torchvision.models.detection.maskrcnn_resnet50_fpn(weights=weights)

        # get number of input features for the classifier
        in_features = model.roi_heads.box_predictor.cls_score.in_features

        # replace the pre-trained head with a new one
        model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

        # now get the number of input features for the mask classifier
        in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
        hidden_layer = 256

        # and replace the mask predictor with a new one
        model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask, hidden_layer, num_classes)

        return model

class ObjectDetectionModel(BaseDetector):
    """Faster R-CNN model. This class can be instantiated for training/running object detection models on data directly from projectkiwi.io.

    Args:
        conn (Connector): A connection object from projectkiwi.connector.
        project_id (str): Id of the project to work with.
        imagery_id (str): Id of the imagery to get tiles from.
        max_zoom (int): Maximum zoom level to request data for, higher zoom will result in higher resolution inputs.
        tile_padding (int): Number of additional pixels to use request on each side of the tile.
        cache_location (str): Downloaded tiles and model checkpoints will be stored here.
        batch_size (int, optional): Batch size. Defaults to 4.
        model_load_path (str, optional): Path to a trained model to load. Defaults to None.
        device (str, optional): Device descriptor to use for training/inference e.g. 'cuda'. Defaults to None.
        transforms (_type_, optional): Transforms to use, from projectkiwi.transforms. Defaults to None.

    Raises:
        ValueError: If a model is specified to load but it cant be found/loaded, a valueError will be raised.
    """

    masks_required = False
    model_name = "obj_detector"

    def get_model(self, num_classes, weights: str = "DEFAULT"):
        # load an instance segmentation model pre-trained pre-trained on COCO
        model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=weights)

        # get number of input features for the classifier
        in_features = model.roi_heads.box_predictor.cls_score.in_features
        
        # replace the pre-trained head with a new one
        model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

        return model
