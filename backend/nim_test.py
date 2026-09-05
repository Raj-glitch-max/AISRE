import os

from openai import OpenAI


MODEL = os.getenv(
    "NIM_MODEL",
    "nvidia/nemotron-3-ultra-550b-a55b",
)

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ["NVIDIA_API_KEY"],
)


response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": "Explain in one sentence why Docker containers are useful.",
        }
    ],
    temperature=0.2,
    max_tokens=200,
)

print(response.choices[0].message.content)
