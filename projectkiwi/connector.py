import logging
import requests
import json


class connector():
    def __init__(self, key, url="https://project-kiwi.org/api/"):
        """constructor

        Args:
            key (str): API key.
            url (str, optional): url for api, in case of multiple instances. Defaults to "https://project-kiwi.org/api/".

        Raises:
            ValueError: API key must be supplied.
        """        
        if key is None:
            raise ValueError("API key missing")

        self.key = key
        self.url = url


    def getImagery(self, project=None):
        """Get a list of imagery

        Args:
            project (str, optional): ID of the project to get all the imagery for, by default, all projects associated with user.

        Returns:
            json: list of imagery
        """        
        route = "get_imagery"
        params = {'key': self.key}
        if not project is None:
            params['project'] = project
        r = requests.get(self.url + route, params=params)
        r.raise_for_status()
        jsonResponse = r.json()
        return jsonResponse



