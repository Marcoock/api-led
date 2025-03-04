from flask import Flask, jsonify
import mysql.connector
import serial
import serial.tools.list_ports
import time
from datetime import datetime, timedelta
import threading
from flask_cors import CORS 
from flask import request 




app = Flask(__name__)
CORS(app)  


# Configurar conexión con Arduino (ajusta el puerto según tu sistema)
def encontrar_puerto_valido():
    puertos_disponibles = list(serial.tools.list_ports.comports())

    if not puertos_disponibles:
        print("No se encontraron puertos disponibles.")
        return None

    for puerto in puertos_disponibles:
        print(f"Probando puerto: {puerto.device}")
        try:
            arduino = serial.Serial(puerto.device, 9600, timeout=1)
            time.sleep(2)  # Esperar que Arduino se inicie
            arduino.close()  # Cerrar para confirmar que el puerto funciona
            return puerto.device  # Retorna el puerto válido
        except (serial.SerialException, OSError):
            print(f"No se pudo conectar en {puerto.device}. Probando siguiente...")

    print("No se pudo establecer conexión con ningún puerto.")
    return None

# Llamar a la función para encontrar el puerto
puerto_detectado = encontrar_puerto_valido()

if puerto_detectado:
    print(f"Conectando a Arduino en {puerto_detectado}...")
    arduino = serial.Serial(puerto_detectado, 9600, timeout=1)
    time.sleep(2)
else:
    print("No se pudo conectar a ningún puerto.")

# Configurar conexión con MySQL
def conectar_mysql():
    return mysql.connector.connect(
        host="localhost",
        user="root",       # Cambia esto por tu usuario de MySQL
        password="",  # Cambia esto por tu contraseña
        database="sit-ctv"       # Cambia esto por el nombre de tu base de datos
    )

# Función para obtener el pin de la válvula desde MySQL
def obtener_pin_valvula(id_valvula):
    conexion = conectar_mysql()
    cursor = conexion.cursor()

    cursor.execute("SELECT nombre, pin FROM valvula WHERE id = %s", (id_valvula,))
    resultado = cursor.fetchone()

    conexion.close()

    if resultado:
        nombre, pin = resultado
        return str(nombre), int(pin)  # Convertimos nombre a string explícitamente
    else:
        return None, None


        # Función para obtener la seccion desde MySQL
def obtener_seccion(value_seccion):
    conexion = conectar_mysql()
    cursor = conexion.cursor()

    query = """
    SELECT s.nombre, a.nombre, p.hora_activacion, p.frecuencia, p.duracion, v.id, a.id 
    FROM seccion AS s 
    INNER JOIN activacion AS a ON s.id = a.id_seccion 
    INNER JOIN programacion AS p ON p.id_activacion = a.id 
    INNER JOIN valvula AS v ON a.id_valvula = v.id 
    WHERE s.nombre = %s
    """
    
    cursor.execute(query, (value_seccion,))
    resultados = cursor.fetchall()  # 🔥 Ahora obtenemos **todas** las filas
    conexion.close()

    if resultados:
        datos = []
        for resultado in resultados:
            seccion, activacion, hora_activacion, frecuencia, duracion, id_valvula, id_activacion = resultado
            datos.append({
                "seccion": seccion,
                "activacion": activacion,
                "hora_activacion": hora_activacion.strftime('%H:%M:%S') if isinstance(hora_activacion, datetime) else str(hora_activacion),
                "frecuencia": frecuencia.strftime('%H:%M:%S') if isinstance(frecuencia, datetime) else str(frecuencia),
                "duracion": duracion.strftime('%H:%M:%S') if isinstance(duracion, datetime) else str(duracion),
                "id_valvula": id_valvula,
                "id_activacion": id_activacion,
            })
        return datos
    else:
        return None

def obtener_seccion_por_valvula(id_valvula):
    conexion = conectar_mysql()
    cursor = conexion.cursor()

    query = """
    SELECT s.nombre, a.nombre, p.hora_activacion, p.frecuencia, p.duracion, a.id 
    FROM seccion AS s 
    INNER JOIN activacion AS a ON s.id = a.id_seccion 
    INNER JOIN programacion AS p ON p.id_activacion = a.id 
    WHERE a.id_valvula = %s
    """
    
    cursor.execute(query, (id_valvula,))
    resultados = cursor.fetchall()  # 🔥 Obtenemos **todas** las filas
    conexion.close()

    if resultados:
        datos = []
        for resultado in resultados:
            seccion, activacion, hora_activacion, frecuencia, duracion, id_activacion = resultado
            datos.append({
                "seccion": seccion,
                "activacion": activacion,
                "hora_activacion": hora_activacion.strftime('%H:%M:%S') if isinstance(hora_activacion, datetime) else str(hora_activacion),
                "frecuencia": frecuencia.strftime('%H:%M:%S') if isinstance(frecuencia, datetime) else str(frecuencia),
                "duracion": duracion.strftime('%H:%M:%S') if isinstance(duracion, datetime) else str(duracion),
                "id_activacion": id_activacion,
            })
        return datos
    else:
        return None

def actualizar_hora_activacion(id_activacion, nueva_hora):
    """
    Actualiza el campo hora_activacion en la tabla programacion para el registro indicado.
    nueva_hora es un objeto de tipo datetime.time.
    """
    conexion = conectar_mysql()
    cursor = conexion.cursor()
    query = "UPDATE programacion SET hora_activacion = %s WHERE id_activacion = %s"
    # Convertir a string en formato HH:MM:SS
    nuevo_valor = nueva_hora.strftime("%H:%M:%S")
    cursor.execute(query, (nuevo_valor, id_activacion))
    conexion.commit()
    conexion.close()
    print(f"Se actualizó la hora de activación a {nuevo_valor} para id_activacion {id_activacion}")

# -----------

def monitorear_valvulas():
    """
    Hilo en segundo plano que monitorea la base de datos y activa/desactiva válvulas automáticamente
    """
    while True:
        conexion = conectar_mysql()
        cursor = conexion.cursor()
        ahora = datetime.now().time()  # Obtener la fecha y hora actual
        ahora = datetime.now().time().replace(microsecond=0)  # Eliminamos microsegundos

        # print(ahora)

        # Obtener todas las programaciones activas
        query = """
        SELECT v.id, v.nombre, v.pin, p.hora_activacion, p.frecuencia, p.duracion, p.id_activacion
        FROM valvula AS v
        INNER JOIN activacion AS a ON v.id = a.id_valvula
        INNER JOIN programacion AS p ON p.id_activacion = a.id
        """
        cursor.execute(query)
        programaciones = cursor.fetchall()
        conexion.close()

        for valvula in programaciones:
            id_valvula, nombre, pin, hora_activacion, frecuencia, duracion, id_activacion = valvula

            # Verificar si hora_activacion es None
            if hora_activacion is None:
                # print(f"Hora de activación no definida para la válvula {nombre} (Pin {pin}), saltando.")
                continue  # Si es None, pasamos al siguiente registro
            # Convertir timedelta a string con formato HH:MM:SS
            hora_activacion_str = str(hora_activacion)  # '18:00:00'
            if len(hora_activacion_str) == 7:  # Corrige formatos tipo '8:00:00' a '08:00:00'
                hora_activacion_str = "0" + hora_activacion_str

            # Convertir a datetime.time
            hora_activacion = datetime.strptime(hora_activacion_str, "%H:%M:%S").time()


            # Comparar las horas: si la hora actual es igual o mayor que la hora de activación
            if ahora == hora_activacion:
                print(f"Activando válvula {nombre} (Pin {pin})")
                encender_valvula(id_valvula)

                # Esperar el tiempo de duración y luego apagar la válvula
                time.sleep(duracion.total_seconds())  # Convertir la duración a segundos

                print(f"Apagando válvula {nombre} (Pin {pin})")
                apagar_valvula(id_valvula)

                # Calcular la próxima activación
                siguiente_activacion = datetime.combine(datetime.today(), hora_activacion) + frecuencia
                nueva_hora = siguiente_activacion.time()  # Extraer solo la parte de la hora

                print(f"Próxima activación de la válvula {nombre} a las {nueva_hora}")

                # Actualizar el campo hora_activacion en la tabla programacion para este id_activacion
                actualizar_hora_activacion(id_activacion, nueva_hora)


        time.sleep(1)  # Revisar cada 10 segundos para optimizar rendimiento
# Iniciar el monitoreo en un hilo separado
hilo_monitoreo = threading.Thread(target=monitorear_valvulas, daemon=True)
hilo_monitoreo.start()

# Endpoint para encender una válvula
@app.route('/encender/<int:id_valvula>', methods=['GET'])
def encender_valvula(id_valvula):
    nombre, pin = obtener_pin_valvula(id_valvula)
    if pin is not None:
        comando = f"{nombre}_ON\n"
        arduino.write(comando.encode())  # Enviar comando a Arduino
        with app.app_context():  # Esto crea un contexto válido
            return jsonify({"mensaje": f"{id_valvula} encendida (Pin {pin}) dato enviado {comando}"})
    return jsonify({"error": " no encontrada"}), 404

# Endpoint para apagar una válvula
@app.route('/apagar/<int:id_valvula>', methods=['GET'])
def apagar_valvula(id_valvula):
    nombre, pin = obtener_pin_valvula(id_valvula)
    if pin is not None:
        comando = f"{nombre}_OFF\n"
        arduino.write(comando.encode())  # Enviar comando a Arduino
        with app.app_context():  # Esto crea un contexto válido
            return jsonify({"mensaje": f" {id_valvula} apagada (Pin {pin})"})
    return jsonify({"error": " no encontrada"}), 404

@app.route('/seccion/<string:value_seccion>', methods=['GET'])
def seccion(value_seccion):
    datos = obtener_seccion(value_seccion)
    
    if datos:
        return jsonify(datos)  # 🔥 Devuelve **todos los registros**
    else:
        return jsonify({"error": "No se encontró la sección"}), 404

@app.route('/seccion/valvula/<int:id_valvula>', methods=['GET'])
def seccion_por_valvula(id_valvula):
    datos = obtener_seccion_por_valvula(id_valvula)
    if datos:
        return jsonify(datos)
    else:
        return jsonify({"mensaje": "No se encontraron registros"}), 404

@app.route('/actualizar_programacion/<int:id_activacion>', methods=['POST'])
def actualizar_programacion(id_activacion):
    try:
        # Obtener datos enviados en la solicitud
        datos = request.json
        nueva_hora = datos.get("hora_activacion")
        nueva_frecuencia = datos.get("frecuencia")
        nueva_duracion = datos.get("duracion")

        if not ( nueva_frecuencia and nueva_duracion):
            return jsonify({"error": "Faltan datos para actualizar la programación"}), 400

        # Conectar a la base de datos
        conexion = conectar_mysql()
        cursor = conexion.cursor()

        # 🔹 Validar si la nueva hora de activación choca con otra programación
        query_validacion = """
        SELECT COUNT(*) FROM programacion 
        WHERE hora_activacion = %s AND id_activacion != %s
        """
        cursor.execute(query_validacion, (nueva_hora, id_activacion))
        existe_conflicto = cursor.fetchone()[0]

        if existe_conflicto > 0:
            conexion.close()
            return jsonify({"error": "La hora de activación ya está asignada a otra válvula"}), 409

        # 🔹 Actualizar los datos de la programación de la válvula específica
        query_actualizacion = """
        UPDATE programacion AS p
        INNER JOIN activacion AS a ON p.id_activacion = a.id
        SET p.hora_activacion = %s, p.frecuencia = %s, p.duracion = %s
        WHERE p.id_activacion = %s
        """
        cursor.execute(query_actualizacion, (nueva_hora, nueva_frecuencia, nueva_duracion, id_activacion))
        conexion.commit()
        filas_afectadas = cursor.rowcount
        conexion.close()

        if filas_afectadas > 0:
            return jsonify({"mensaje": "Programación actualizada correctamente"}), 200
        else:
            return jsonify({"error": "No se encontró programación para la válvula especificada"}), 404

    except Exception as e:
        return jsonify({"error": f"Error en la actualización: {str(e)}"}), 500

if __name__ == '__main__':
    
    app.run(debug=False)  # Cambia debug=True a debug=False