from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# Configurar CORS para permitir peticiones desde cualquier origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# URL del script Python que correrá en tu laptop como puente con el Arduino
LAPTOP_SERVER_URL = "http://127.0.0.1:5000"

@app.get("/")
def home():
    return {"mensaje": "API en la nube lista para controlar el Arduino"}

@app.get("/encender")
def encender_led():
    try:
        response = requests.get(f"{LAPTOP_SERVER_URL}/encender")
        return response.json()
    except Exception as e:
        return {"error": f"No se pudo conectar con la laptop: {str(e)}"}

@app.get("/apagar")
def apagar_led():
    try:
        response = requests.get(f"{LAPTOP_SERVER_URL}/apagar")
        return response.json()
    except Exception as e:
        return {"error": f"No se pudo conectar con la laptop: {str(e)}"}
