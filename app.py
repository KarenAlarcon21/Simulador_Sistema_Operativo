from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import random
import time

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'

# Estados posibles para un proceso
ESTADOS = ['Nuevo', 'Listo', 'Ejecutando', 'Bloqueado', 'Terminado']

# Lista de recursos disponibles
RECURSOS_DISPONIBLES = ['Recurso1', 'Recurso2', 'Recurso3', 'Recurso4', 'Recurso5', 'Recurso6']

class Proceso:
    def __init__(self, id_proceso, tamaño, recursos_requeridos):
        self.id = id_proceso
        self.tamaño = int(tamaño)
        self.tamaño_inicial = int(tamaño)  # Nuevo atributo
        self.recursos_requeridos = recursos_requeridos  # Lista de recursos
        self.estado = 'Nuevo'
        self.recursos_obtenidos = []
        self.unidades_ejecutadas = 0  # Contador de unidades ejecutadas en este ciclo
        self.recursos_faltantes = []  # Recursos faltantes si está bloqueado

    def __str__(self):
        return f"ID: {self.id}, Tamaño: {self.tamaño_inicial}, Restante: {self.tamaño}, Estado: {self.estado}"

    def to_dict(self):
        return {
            'id': self.id,
            'tamaño': self.tamaño,
            'tamaño_inicial': self.tamaño_inicial,
            'recursos_requeridos': self.recursos_requeridos,
            'estado': self.estado,
            'recursos_obtenidos': self.recursos_obtenidos,
            'unidades_ejecutadas': self.unidades_ejecutadas,
            'recursos_faltantes': self.recursos_faltantes,
        }

    @staticmethod
    def from_dict(data):
        proceso = Proceso(data['id'], data['tamaño_inicial'], data['recursos_requeridos'])
        proceso.tamaño = data['tamaño']
        proceso.estado = data['estado']
        proceso.recursos_obtenidos = data['recursos_obtenidos']
        proceso.unidades_ejecutadas = data['unidades_ejecutadas']
        proceso.recursos_faltantes = data.get('recursos_faltantes', [])
        return proceso

def get_estado_simulacion():
    if 'estado_simulacion' not in session:
        # Inicializar el estado de la simulación
        session['estado_simulacion'] = {
            'recursos_disponibles_dict': {recurso: True for recurso in RECURSOS_DISPONIBLES},
            'nuevo': [],
            'listo': [],
            'ejecutando': [],
            'bloqueado': [],
            'terminado': [],
            'simulacion_en_curso': False,
            'simulacion proceso':False,
        }
    return session['estado_simulacion']

def guardar_estado_simulacion(estado_simulacion):
    session['estado_simulacion'] = estado_simulacion

@app.route('/')
def index():
    estado_simulacion = get_estado_simulacion()
    procesos_por_estado = {}
    for estado in ESTADOS:
        procesos_por_estado[estado] = [Proceso.from_dict(p) for p in estado_simulacion[estado.lower()]]
    simulacion_en_curso = estado_simulacion.get('simulacion_en_curso', False)
    simulacion_pausada = estado_simulacion.get('simulacion_pausada', False)
    return render_template('index.html', estados=ESTADOS, procesos=procesos_por_estado, simulacion_en_curso=simulacion_en_curso, simulacion_pausada=simulacion_pausada)

@app.route('/agregar_proceso', methods=['GET', 'POST'])
def agregar_proceso():
    if request.method == 'POST':
        id_proceso = request.form.get('id_proceso').lower()
        tamaño = request.form.get('tamaño')
        recursos_requeridos = request.form.getlist('recursos')

        # Validar entradas
        if not id_proceso or not tamaño.isdigit():
            error = "Por favor, ingrese un ID válido y un tamaño numérico."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

        estado_simulacion = get_estado_simulacion()

        # Verificar si el ID ya existe
        if id_ya_existe(id_proceso, estado_simulacion):
            error = f"Ya existe un proceso con el ID '{id_proceso}'. Por favor, elija otro ID."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

        nuevo_proceso = Proceso(id_proceso, tamaño, recursos_requeridos)
        nuevo_proceso.estado = 'Nuevo'
        estado_simulacion['nuevo'].append(nuevo_proceso.to_dict())
        guardar_estado_simulacion(estado_simulacion)
        return redirect(url_for('index'))
    else:
        return render_template('agregar_proceso.html', recursos=RECURSOS_DISPONIBLES)

def id_ya_existe(id_proceso, estado_simulacion):
    for estado in ESTADOS:
        procesos = [Proceso.from_dict(p) for p in estado_simulacion[estado.lower()]]
        for proceso in procesos:
            if proceso.id == id_proceso:
                return True
    return False

@app.route('/iniciar_simulacion')
def iniciar_simulacion():
    estado_simulacion = get_estado_simulacion()
    # Mover procesos de 'Nuevo' a 'Listo'
    while estado_simulacion['nuevo']:
        proceso_dict = estado_simulacion['nuevo'].pop(0)
        proceso = Proceso.from_dict(proceso_dict)
        proceso.estado = 'Listo'
        estado_simulacion['listo'].append(proceso.to_dict())
    estado_simulacion['simulacion_en_curso'] = True
    guardar_estado_simulacion(estado_simulacion)
    return redirect(url_for('simulacion'))

@app.route('/simulacion')
def simulacion():
    return render_template('simulacion.html')

@app.route('/pausar_simulacion')
def pausar_simulacion():
    estado_simulacion = get_estado_simulacion()
    estado_simulacion['simulacion_pausada'] = True
    guardar_estado_simulacion(estado_simulacion)
    return '', 204  # Respuesta vacía con código de estado 204 No Content

@app.route('/reanudar_simulacion')
def reanudar_simulacion():
    estado_simulacion = get_estado_simulacion()
    estado_simulacion['simulacion_pausada'] = False
    guardar_estado_simulacion(estado_simulacion)
    return redirect(url_for('simulacion'))

@app.route('/obtener_estado')
def obtener_estado():
    estado_simulacion = get_estado_simulacion()
    procesos_por_estado = {}
    for estado in ESTADOS:
        procesos_por_estado[estado] = [p for p in estado_simulacion[estado.lower()]]
    simulacion_en_curso = estado_simulacion.get('simulacion_en_curso', False)
    simulacion_pausada = estado_simulacion.get('simulacion_pausada', False)
    return jsonify({
        'estados': ESTADOS,
        'procesos': procesos_por_estado,
        'simulacion_en_curso': simulacion_en_curso,
        'simulacion_pausada': simulacion_pausada
    })


@app.route('/avanzar_simulacion')
def avanzar_simulacion():
    estado_simulacion = get_estado_simulacion()
    if not estado_simulacion.get('simulacion_en_curso', False):
        return jsonify({'simulacion_en_curso': False})
    
    if estado_simulacion.get('simulacion_pausada', False):
        # No avanzar la simulación, solo devolver el estado actual
        procesos_por_estado = {}
        for estado in ESTADOS:
            procesos_por_estado[estado] = [p for p in estado_simulacion[estado.lower()]]
        return jsonify({
            'estados': ESTADOS,
            'procesos': procesos_por_estado,
            'simulacion_en_curso': True,
            'simulacion_pausada': True
        })
    
    # Realizar un paso de simulación
    desbloquear_procesos(estado_simulacion)
    asignar_procesos(estado_simulacion)
    ejecutar_procesos(estado_simulacion)

    # Verificar si la simulación ha terminado
    if not estado_simulacion['listo'] and not estado_simulacion['bloqueado'] and not estado_simulacion['ejecutando']:
        estado_simulacion['simulacion_en_curso'] = False

    guardar_estado_simulacion(estado_simulacion)

    procesos_por_estado = {}
    for estado in ESTADOS:
        procesos_por_estado[estado] = [p for p in estado_simulacion[estado.lower()]]

    return jsonify({
        'estados': ESTADOS,
        'procesos': procesos_por_estado,
        'simulacion_en_curso': estado_simulacion['simulacion_en_curso'],
        'simulacion_pausada': estado_simulacion.get('simulacion_pausada', False)
    })



@app.route('/siguiente_paso')
def siguiente_paso():
    estado_simulacion = get_estado_simulacion()
    if not estado_simulacion.get('simulacion_en_curso', False):
        return redirect(url_for('index'))

    # Realizar un paso de simulación
    desbloquear_procesos(estado_simulacion)
    asignar_procesos(estado_simulacion)
    ejecutar_procesos(estado_simulacion)

    # Verificar si la simulación ha terminado
    if not estado_simulacion['listo'] and not estado_simulacion['bloqueado'] and not estado_simulacion['ejecutando']:
        estado_simulacion['simulacion_en_curso'] = False

    guardar_estado_simulacion(estado_simulacion)
    return redirect(url_for('index'))

def desbloquear_procesos(estado_simulacion):
    bloqueado = [Proceso.from_dict(p) for p in estado_simulacion['bloqueado']]
    recursos_disponibles_dict = estado_simulacion['recursos_disponibles_dict']

    procesos_bloqueados = bloqueado[:]
    for proceso in procesos_bloqueados:
        if recursos_disponibles(proceso, recursos_disponibles_dict):
            # Asignar recursos y mover a 'Listo'
            asignar_recursos(proceso, recursos_disponibles_dict)
            proceso.recursos_obtenidos = proceso.recursos_requeridos[:]
            bloqueado.remove(proceso)
            proceso.estado = 'Listo'
            proceso.recursos_faltantes = []
            estado_simulacion['listo'].append(proceso.to_dict())
        else:
            # Actualizar recursos faltantes
            proceso.recursos_faltantes = obtener_recursos_faltantes(proceso, recursos_disponibles_dict)

    estado_simulacion['bloqueado'] = [p.to_dict() for p in bloqueado]


def asignar_procesos(estado_simulacion):
    listo = [Proceso.from_dict(p) for p in estado_simulacion['listo']]
    ejecutando = [Proceso.from_dict(p) for p in estado_simulacion['ejecutando']]
    recursos_disponibles_dict = estado_simulacion['recursos_disponibles_dict']

    procesos_listos = listo[:]
    for proceso in procesos_listos:
        if len(ejecutando) < 1:
            if proceso.recursos_obtenidos == proceso.recursos_requeridos:
                # El proceso ya tiene sus recursos, puede pasar a 'Ejecutando'
                listo.remove(proceso)
                proceso.estado = 'Ejecutando'
                ejecutando.append(proceso)
            elif recursos_disponibles(proceso, recursos_disponibles_dict):
                # Los recursos están disponibles, asignar recursos y pasar a 'Ejecutando'
                asignar_recursos(proceso, recursos_disponibles_dict)
                proceso.recursos_obtenidos = proceso.recursos_requeridos[:]
                listo.remove(proceso)
                proceso.estado = 'Ejecutando'
                ejecutando.append(proceso)
            else:
                # Los recursos no están disponibles, mover a 'Bloqueado'
                proceso.estado = 'Bloqueado'
                proceso.recursos_faltantes = obtener_recursos_faltantes(proceso, recursos_disponibles_dict)
                listo.remove(proceso)
                estado_simulacion['bloqueado'].append(proceso.to_dict())
        else:
            # CPU ocupado, el proceso permanece en 'Listo'
            pass

    estado_simulacion['listo'] = [p.to_dict() for p in listo]
    estado_simulacion['ejecutando'] = [p.to_dict() for p in ejecutando]


def ejecutar_procesos(estado_simulacion):
    ejecutando = [Proceso.from_dict(p) for p in estado_simulacion['ejecutando']]
    terminado = [Proceso.from_dict(p) for p in estado_simulacion['terminado']]
    listo = [Proceso.from_dict(p) for p in estado_simulacion['listo']]
    recursos_disponibles_dict = estado_simulacion['recursos_disponibles_dict']

    procesos_a_listo = []
    procesos_terminados = []
    for proceso in ejecutando:
        # Reducir tamaño en 1 unidad por ciclo
        proceso.tamaño -= 1
        proceso.unidades_ejecutadas += 1
        if proceso.tamaño <= 0:
            proceso.estado = 'Terminado'
            procesos_terminados.append(proceso)
        elif proceso.unidades_ejecutadas >= 5:
            # Ha ejecutado 5 unidades, decidir si libera recursos
            proceso.estado = 'Listo'
            procesos_a_listo.append(proceso)
        else:
            # Continúa ejecutando
            proceso.estado = 'Ejecutando'

    # Remover procesos de 'Ejecutando' y actualizar estados
    for proceso in procesos_terminados:
        ejecutando.remove(proceso)
        liberar_recursos(proceso, recursos_disponibles_dict)
        terminado.append(proceso)
        proceso.recursos_obtenidos.clear()

    for proceso in procesos_a_listo:
        ejecutando.remove(proceso)
        if random.random() < 0.2:
            # El proceso libera sus recursos
            liberar_recursos(proceso, recursos_disponibles_dict)
            proceso.recursos_obtenidos.clear()
        # Si no libera los recursos, los mantiene
        listo.append(proceso)
        proceso.unidades_ejecutadas = 0  # Reiniciar contador de unidades ejecutadas

    estado_simulacion['ejecutando'] = [p.to_dict() for p in ejecutando]
    estado_simulacion['terminado'] = [p.to_dict() for p in terminado]
    estado_simulacion['listo'] = [p.to_dict() for p in listo]
    estado_simulacion['recursos_disponibles_dict'] = recursos_disponibles_dict

def recursos_disponibles(proceso, recursos_disponibles_dict):
    for recurso in proceso.recursos_requeridos:
        if not recursos_disponibles_dict.get(recurso, True):
            return False
    return True

def obtener_recursos_faltantes(proceso, recursos_disponibles_dict):
    faltantes = []
    for recurso in proceso.recursos_requeridos:
        if not recursos_disponibles_dict.get(recurso, True):
            faltantes.append(recurso)
    return faltantes


def asignar_recursos(proceso, recursos_disponibles_dict):
    for recurso in proceso.recursos_requeridos:
        recursos_disponibles_dict[recurso] = False

def liberar_recursos(proceso, recursos_disponibles_dict):
    for recurso in proceso.recursos_requeridos:
        recursos_disponibles_dict[recurso] = True

@app.route('/generar_reporte')
def generar_reporte():
    estado_simulacion = get_estado_simulacion()
    reporte = "\n\n"
    for estado in ESTADOS:
        procesos = [Proceso.from_dict(p) for p in estado_simulacion[estado.lower()]]
        for proceso in procesos:
            if proceso:
                recursos_obtenidos = ', '.join(proceso.recursos_obtenidos) if proceso.recursos_obtenidos else 'Ninguno'
                reporte += f"ID: {proceso.id}, Tamaño Inicial: {proceso.tamaño_inicial}, Tamaño Restante: {proceso.tamaño}, Estado: {proceso.estado}, Recursos Obtenidos: {recursos_obtenidos}"
                if proceso.estado == 'Bloqueado':
                    recursos_faltantes = ', '.join(proceso.recursos_faltantes)
                    reporte += f", Faltan Recursos: {recursos_faltantes}"
                reporte += "\n"
    return render_template('reporte.html', reporte=reporte)

@app.route('/reiniciar_simulacion')
def reiniciar_simulacion():
    # Reiniciar el estado de la simulación
    session.pop('estado_simulacion', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
