from sqlalchemy.orm import mapped_column, relationship, Mapped
from database.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from models.user_model import User

class GitHubInstallation(Base):
    __tablename__ = "github_installations"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    installation_id: Mapped[int] = mapped_column(unique=True, index=True, nullable=False)

    account_login: Mapped[str | None] = mapped_column(nullable=True)
    account_id: Mapped[int | None] = mapped_column(nullable=True)
    
    #nullable is true since github webhook returns installation info but not user info, so we can have installations without associated users
    #we will link the installation to the user
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user: Mapped["User"] = relationship("User", back_populates="github_installations")