import instructor
from openai import OpenAI
from pydantic import BaseModel

# Enables `response_model`
#client = instructor.patch(OpenAI())
client = instructor.patch(
    OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    ),
    mode=instructor.Mode.JSON,
)

class UserDetail(BaseModel):
    name: str
    age: int


user = client.chat.completions.create(
    model="solar",
    response_model=UserDetail,
    messages=[
        {"role": "user", "content": "Extract Jason is 25 years old"},
    ],
)

assert isinstance(user, UserDetail)
assert user.name == "Jason"
assert user.age == 25

print(user)