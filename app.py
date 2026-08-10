import os

from dotenv import load_dotenv
from flask import Flask

load_dotenv()

app = Flask(__name__)


@app.get("/")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
