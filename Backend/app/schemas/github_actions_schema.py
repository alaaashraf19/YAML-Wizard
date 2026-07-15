from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field

#expressions ${{ ... }}
class Expression(BaseModel):
    kind: Literal["literal", "ref", "call", "binop", "unop"]
    #literal
    value: Optional[Any] = None
    #ref
    path: Optional[list[str]] = None
    #functions calls
    fn: Optional[str] = None
    args: Optional[list["Expression"]] = None
    #binary operations 
    op: Optional[str] = None
    left: Optional["Expression"] = None
    right: Optional["Expression"] = None
    #unary operations
    operand: Optional["Expression"] = None

ExprOrLiteral = Union[str, int, float, bool, Expression]
# Resolve the forward reference inside Expression
Expression.model_rebuild()

#triggers
class TriggerFilters(BaseModel):
    branches: Optional[list[str]] = None
    branches_ignore: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    tags_ignore: Optional[list[str]] = None
    paths: Optional[list[str]] = None
    paths_ignore: Optional[list[str]] = None
    types: Optional[list[str]] = None
    cron: Optional[list[str]] = None
    workflows: Optional[list[str]] = None  #workflow_run

class Trigger(BaseModel):
    event: str
    filters: TriggerFilters = Field(default_factory=TriggerFilters)
    raw: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


#inputs and outputs
class Input(BaseModel):
    name: str
    description: Optional[str] = None
    type: Literal["string", "number", "boolean", "choice", "environment"] = "string"
    required: bool = False
    default: Optional[ExprOrLiteral] = None
    options: Optional[list[str]] = None  # for type=choice

class Output(BaseModel):
    name: str
    description: Optional[str] = None
    value: Expression

#defaults, permissions and concurrency
class Defaults(BaseModel):
    shell: Optional[str] = None
    working_directory: Optional[str] = None

class Permissions(BaseModel):
    mode: Literal["all", "read-all", "write-all", "none", "custom"] = "custom"
    scopes: Optional[dict[str, Literal["read", "write", "none"]]] = None

class Concurrency(BaseModel):
    group: ExprOrLiteral
    cancel_in_progress: bool = False

#runner, container and environment
class Runner(BaseModel):
    type: Literal["github-hosted", "self-hosted"] = "github-hosted"
    labels: list[str] = Field(default_factory=list)  #["ubuntu-latest"]
    group: Optional[str] = None

class ContainerCredentials(BaseModel):
    username: Optional[ExprOrLiteral] = None
    password: Optional[ExprOrLiteral] = None

class Container(BaseModel):
    image: str
    credentials: Optional[ContainerCredentials] = None
    env: dict[str, ExprOrLiteral] = Field(default_factory=dict)
    ports: list[str] = Field(default_factory=list)
    volumes: list[str] = Field(default_factory=list)
    options: Optional[str] = None

class Environment(BaseModel):
    name: str
    url: Optional[ExprOrLiteral] = None

#matrix and strategy
class Matrix(BaseModel):
    dimensions: dict[str, list[ExprOrLiteral]] = Field(default_factory=dict)
    include: list[dict[str, ExprOrLiteral]] = Field(default_factory=list)
    exclude: list[dict[str, ExprOrLiteral]] = Field(default_factory=list)

class Strategy(BaseModel):
    matrix: Optional[Matrix] = None
    fail_fast: bool = True
    max_parallel: Optional[int] = None

#Reusable workflow call
class ReusableWorkflowCall(BaseModel):
    ref: str  #path to another workflow
    with_: dict[str, ExprOrLiteral] = Field(default_factory=dict, alias="with")
    secrets: Union[dict[str, Expression], Literal["inherit"], None] = None

    model_config = {"populate_by_name": True}

#Steps
class Step(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    kind: Literal["action", "shell"]

    #actio: ref like actions/checkout@v4
    ref: Optional[str] = None

    #shell
    shell: Optional[str] = None  #bash,...
    run: Optional[str] = None

    with_: dict[str, ExprOrLiteral] = Field(default_factory=dict, alias="with")
    env: dict[str, ExprOrLiteral] = Field(default_factory=dict)
    if_: Optional[Expression] = Field(default=None, alias="if")
    working_directory: Optional[str] = None
    continue_on_error: bool = False
    timeout_minutes: Optional[int] = None

    raw: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

#Job
class Job(BaseModel):
    id: str
    name: Optional[str] = None
    needs: list[str] = Field(default_factory=list)
    if_: Optional[Expression] = Field(default=None, alias="if")

    runner: Optional[Runner] = None  # None when the job is a reusable-workflow call
    container: Optional[Container] = None
    services: dict[str, Container] = Field(default_factory=dict)

    environment: Optional[Environment] = None
    permissions: Optional[Permissions] = None
    concurrency: Optional[Concurrency] = None
    strategy: Optional[Strategy] = None

    env: dict[str, ExprOrLiteral] = Field(default_factory=dict)
    defaults: Optional[Defaults] = None

    secrets_used: list[str] = Field(default_factory=list)
    timeout_minutes: Optional[int] = None
    continue_on_error: bool = False

    steps: list[Step] = Field(default_factory=list)
    outputs: dict[str, Expression] = Field(default_factory=dict)

    # when this job is a reusable-workflow call instead of a steps-based job.
    uses: Optional[ReusableWorkflowCall] = None

    raw: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class Pipeline(BaseModel):
    name: Optional[str] = None

    triggers: list[Trigger] = Field(default_factory=list)
    inputs: list[Input] = Field(default_factory=list)
    outputs: list[Output] = Field(default_factory=list)

    env: dict[str, ExprOrLiteral] = Field(default_factory=dict)
    defaults: Optional[Defaults] = None
    permissions: Optional[Permissions] = None
    concurrency: Optional[Concurrency] = None

    jobs: list[Job] = Field(default_factory=list)

    raw: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

