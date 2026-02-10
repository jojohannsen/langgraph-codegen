import BaseModel, Field from pydantic

class FieldToDefine(BaseModel):
    name: str = Field(description="name of the data field")
    description: str = Field(description="purpose of the data field")
    data_type: str = Field(description="data type to use for this field")

class DataStructureToDefineState(BaseModel):
    name: str = Field(description="name of data structure we are defining")
    fields: list[FieldToDefine] = field(description="list of fields to define")
