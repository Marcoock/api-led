import serial
import time
from flask import Flask, request, jsonify
from flask_cors import CORS  


app = Flask(__name__)
CORS(app)  

try:
    arduino = serial.Serial(port='COM7', baudrate=9600, timeout=1)
    time.sleep(2)  # Espera para que el puerto esté listo
    print("Conectado a Arduino en COM7")
except serial.SerialException as e:
    print(f"Error al conectar con Arduino: {e}")
    arduino = None  # Evita que el programa se caiga

@app.route('/encender', methods=['GET'])
def encender_led():
    if arduino:
        arduino.write(b'ON\n')
        return jsonify({"estado": "LED encendido"})
    else:
        return jsonify({"error": "No hay conexión con Arduino"}), 500

@app.route('/apagar', methods=['GET'])
def apagar_led():
    if arduino:
        arduino.write(b'OFF\n')
        return jsonify({"estado": "LED apagado"})
    else:
        return jsonify({"error": "No hay conexión con Arduino"}), 500

@app.route('/')
def inicio():
    return "API para controlar el LED en el pin 13 del Arduino"

if __name__ == '__main__':
    app.run(debug=False)  # Cambia debug=True a debug=False
