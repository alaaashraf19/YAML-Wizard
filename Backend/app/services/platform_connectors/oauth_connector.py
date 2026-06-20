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
    async def get_valid_token(self, connection, db=None):
        pass

    @abstractmethod
    async def is_token_valid(self, connection):
        pass