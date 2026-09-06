from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.responses.create(
    model="gpt-5.6-luna",
    input="Ты карьерный консультант. В одном предложении скажи, какие навыки нужны Junior Backend Developer."
)

print(response.output_text)