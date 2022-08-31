import sys,os
sys.path.insert(0, os.getcwd())
from projectkiwi.connector import Connector


from test_basics import TEST_URL


def test_get_tasks():
    API_KEY = os.environ['PROJECT_KIWI_API_KEY']

    conn = Connector(API_KEY, TEST_URL)

    tasks = conn.getTasks(queue_id = 15)
    print(tasks)

    assert len(tasks) > 1, "Couldn't load tasks"