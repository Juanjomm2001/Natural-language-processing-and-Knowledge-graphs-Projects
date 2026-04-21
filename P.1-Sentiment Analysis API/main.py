from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class TextInput(BaseModel):
    text: str

@app.post("/v1/sentiment")
def analyze_sentiment(text: TextInput):
    lowered_text = text.text.lower()

    if 'god' in lowered_text or 'good' in lowered_text:
        return {"score": 3}
    elif 'dårlig' in lowered_text or 'bad' in lowered_text:
        return {"score": -3}
    else:
        return {"score": 0}