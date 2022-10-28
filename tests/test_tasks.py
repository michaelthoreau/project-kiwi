import sys,os
sys.path.insert(0, os.getcwd())
from projectkiwi.connector import Connector
from projectkiwi.models import Task

from test_basics import TEST_URL

QUEUE_ID = 27

def test_get_tasks():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    tasks1 = conn.getTasks(queue_id = QUEUE_ID)

    assert len(tasks1) > 1, "Couldn't load tasks"

    tasks2 = conn.getTasks(queue_id = QUEUE_ID)

    assert len(tasks2) > 1, "Couldn't load tasks"

    # tasks should be random but repeatable for a user
    assert tasks1 == tasks2, "Task ordering not correct"



def test_get_task():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    task = conn.getTask(queue_id = QUEUE_ID)

    assert isinstance(task, Task), "Couldn't load task"



def test_get_next_task():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    task = conn.getNextTask(queue_id = QUEUE_ID)

    assert isinstance(task, Task), "Couldn't load task"

    task2 = conn.getNextTask(queue_id = QUEUE_ID)

    assert task.zxy == task2.zxy, "Repeated calls to get_next_task should give the same task"