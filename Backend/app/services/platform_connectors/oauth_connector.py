# provider_connector.py
from abc import ABC, abstractmethod

class oauthConnector(ABC):

    @abstractmethod
    async def connect(self, request, db):
        pass

    @abstractmethod
    async def callback(self, code, request, db):
        pass

    @abstractmethod
    async def get_valid_token(self, connection, db=None): #db is optional for GitHub since we can check token validity without DB while gitlab needs it so we set db=none for github and gitlab will use it
        pass

    @abstractmethod
    async def is_token_valid(self, connection):
        pass

    @abstractmethod
    async def disconnect(self, request, db):
        pass