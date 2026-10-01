'''
Pydantic BaseModel for each tool
'''

from pydantic import BaseModel, Field


class CalculatorParams(BaseModel):
    '''
    Parameters for Calculator tool
    '''
    expression: str = Field(
        description="Mathematical expression to evaluate (e.g. '2 + 3 * 4')",
        min_length=1,
    )

class GetDatetimeParams(BaseModel):
    '''
    Parameters for GetDatetime tool
    '''
    timezone: str = Field(
        default="UTC",
        description="Timezone for the current date and time (e.g 'UTC', 'Europe/Bucharest')",   
        min_length=1
    )

class WebSearchParams(BaseModel):
    '''
    Parameters for WebSearch tool
    '''
    query: str = Field(
        description="Search terms to look up on the web",
        min_length=2,
    )

    max_results: int = Field(
        default=5,
        description="Maximum number of results to return",
        ge=1,
        le=20,
    )