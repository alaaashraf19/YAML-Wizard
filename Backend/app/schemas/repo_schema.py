from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Platform(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"