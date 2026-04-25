from database.base import Base
from sqlalchemy import Column, ForeignKey, Integer, String

class GitHubInstallation(Base):
    __tablename__ = "github_installations"
    id = Column(Integer, primary_key=True, index=True)
    installation_id = Column(Integer, unique=True, index=True)
    account_login = Column(String, index=True)
    account_id = Column(Integer, unique=True, index=True)
    #nullable is true since github webhook returns installation info but not user info, so we can have installations without associated users
    #we will link the installation to the user
    #to be yet checked!!!
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)