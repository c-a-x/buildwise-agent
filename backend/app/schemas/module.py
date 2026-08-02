from pydantic import BaseModel


class ModuleStatus(BaseModel):
    key: str
    name: str
    agent_name: str
    status: str
    description: str
    planned_inputs: list[str]
    planned_outputs: list[str]
    available_endpoints: list[str]
