# Flask API app
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return 'Research Assistant Backend Running!'
