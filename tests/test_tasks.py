import sys,os
sys.path.insert(0, os.getcwd())
from projectkiwi.connector import Connector
from projectkiwi.models import Task

from test_basics import TEST_URL


def test_get_tasks():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    tasks = conn.getTasks(queue_id = 14)

    assert len(tasks) > 1, "Couldn't load tasks"

def test_get_task():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    task = conn.getTask(queue_id = 14)

    assert isinstance(task, Task), "Couldn't load task"



def test_get_next_task():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    task = conn.getNextTask(queue_id = 14)

    assert isinstance(task, Task), "Couldn't load task"

    task2 = conn.getNextTask(queue_id = 14)

    assert task.zxy == task2.zxy, "Repeated calls to get_next_task should give the same task"