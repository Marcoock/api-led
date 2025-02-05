from flask import Flask, request, jsonify
from flask_cors import CORS  

app = Flask(__name__)
CORS(app)

# Variable global para almacenar el estado del LED
estado_led = {"estado": "apagado"}

@app.route('/encender', methods=['GET'])
def encender_led():
    estado_led["estado"] = "encendido"
    return jsonify(estado_led)

@app.route('/apagar', methods=['GET'])
def apagar_led():
    estado_led["estado"] = "apagado"
    return jsonify(estado_led)

@app.route('/estado', methods=['GET'])
def obtener_estado():
    return jsonify(estado_led)

@app.route('/')
def inicio():
    return "API en Vercel - Control de Arduino"

if __name__ == '__main__':
    app.run(debug=False)
