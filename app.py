from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from memory_manager import MAX_PROCESS_SIZE
import memory_manager
import random
import math

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'

# Estados posibles para un proceso
ESTADOS = ['Nuevo', 'Listo', 'Ejecutando', 'Bloqueado', 'Terminado']

# Lista de recursos disponibles
RECURSOS_DISPONIBLES = ['Recurso1', 'Recurso2', 'Recurso3', 'Recurso4', 'Recurso5', 'Recurso6']

class Proceso:
    def __init__(self, id_proceso, tamaño, recursos_requeridos, preeminencia=False):
        self.id = id_proceso
        self.tamaño = int(tamaño)
        self.tamaño_inicial = int(tamaño)  # Nuevo atributo
        self.recursos_requeridos = recursos_requeridos  # Lista de recursos
        self.estado = 'Nuevo'
        self.preeminencia=preeminencia
        self.recursos_obtenidos = []
        self.unidades_ejecutadas = 0  # Contador de unidades ejecutadas en este ciclo
        self.recursos_faltantes = []  # Recursos faltantes si está bloqueado
        self.veces_ejecutando = 0

    def __str__(self):
        return f"ID: {self.id}, Tamaño: {self.tamaño_inicial}, Restante: {self.tamaño}, Estado: {self.estado}, Preeminencia: {self.preeminencia}"

    def to_dict(self):
        return {
            'id': self.id,
            'tamaño': self.tamaño,
            'tamaño_inicial': self.tamaño_inicial,
            'recursos_requeridos': self.recursos_requeridos,
            'estado': self.estado,
            'preeminencia': self.preeminencia,
            'recursos_obtenidos': self.recursos_obtenidos,
            'unidades_ejecutadas': self.unidades_ejecutadas,
            'recursos_faltantes': self.recursos_faltantes,
            'veces_ejecutando': self.veces_ejecutando,
        }

    @staticmethod
    def from_dict(data):
        proceso = Proceso(data['id'], data['tamaño_inicial'], data['recursos_requeridos'],preeminencia=data.get('preeminencia', False))
        proceso.tamaño = data['tamaño']
        proceso.estado = data['estado']
        proceso.recursos_obtenidos = data['recursos_obtenidos']
        proceso.unidades_ejecutadas = data['unidades_ejecutadas']
        proceso.recursos_faltantes = data.get('recursos_faltantes', [])
        proceso.veces_ejecutando = data.get('veces_ejecutando', 0)
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
            'simulacion_pausada':False,
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
    estado_simulacion = get_estado_simulacion()
    
    # Contar procesos únicos
    procesos_existentes = set()
    for estado in ESTADOS:
        for proceso in estado_simulacion[estado.lower()]:
            procesos_existentes.add(proceso.get('id', ''))
    
    numero_procesos = len(procesos_existentes)
    MAX_PROCESOS = 6  # Límite de procesos
    MAX_TAMANO = 65

    if request.method == 'POST':

        if numero_procesos >= MAX_PROCESOS:
            error = f"Has alcanzado el límite máximo de {MAX_PROCESOS} procesos."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

        id_proceso = request.form.get('id_proceso').lower()
        tamaño = request.form.get('tamaño')
        recursos_requeridos = request.form.getlist('recursos')
        preeminencia = request.form.get('preeminencia') == 'True'  # Capturar el valor de preeminencia

        # Validar entradas
        if not id_proceso or not tamaño.isdigit():
            error = "Por favor, ingrese un ID válido y un tamaño numérico."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)
        
        tamaño_int = int(tamaño)
        if tamaño_int > MAX_TAMANO:
            error = f"El tamaño del proceso no puede exceder {MAX_TAMANO}."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

        if tamaño_int < 1:
            error = "El tamaño dígitado para el proceso no se encuentra dentro del rango permitido (1 a 65 kb)."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

        estado_simulacion = get_estado_simulacion()

        # Verificar si el ID ya existe
        if id_ya_existe(id_proceso, estado_simulacion):
            error = f"Ya existe un proceso con el ID '{id_proceso}'. Por favor, elija otro ID."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

        # Crear el proceso en la simulación del sistema operativo
        nuevo_proceso = Proceso(id_proceso, tamaño, recursos_requeridos, preeminencia=preeminencia)
        nuevo_proceso.estado = 'Nuevo'
        estado_simulacion['nuevo'].append(nuevo_proceso.to_dict())
        guardar_estado_simulacion(estado_simulacion)

        # Asignar memoria al proceso en la simulación de memoria
        success, msg = memory_manager.create_process_memory(id_proceso, float(tamaño))
        if not success:
            # Si no se pudo asignar memoria, eliminar el proceso del estado actual
            estado_simulacion['nuevo'].pop()
            guardar_estado_simulacion(estado_simulacion)
            error = f"No se pudo asignar memoria al proceso: {msg}"
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)
        return redirect(url_for('index'))
    else:
        if numero_procesos >= MAX_PROCESOS:
            mensaje = f"Has alcanzado el límite máximo de {MAX_PROCESOS} procesos."
            return render_template('agregar_proceso.html', mensaje=mensaje, recursos=RECURSOS_DISPONIBLES, limite_alcanzado=True)
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
    
    if not estado_simulacion.get('simulacion_en_curso', False):
        # Guardar los procesos nuevos que se hayan agregado después de que la simulación anterior terminó
        nuevos_procesos = estado_simulacion.get('nuevo', [])
        # Preservar los procesos terminados
        procesos_terminados = estado_simulacion.get('terminado', [])
        # Reiniciar el estado de la simulación, excepto 'terminado'
        estado_simulacion = {
            'recursos_disponibles_dict': {recurso: True for recurso in RECURSOS_DISPONIBLES},
            'nuevo': nuevos_procesos,
            'listo': [],
            'ejecutando': [],
            'bloqueado': [],
            'terminado': procesos_terminados,  # Preservamos los procesos terminados
            'simulacion_en_curso': True,
            'simulacion_pausada': False,
        }
    else:
        # Si la simulación está en curso, simplemente asegurarse de que no esté pausada
        estado_simulacion['simulacion_pausada'] = False
        estado_simulacion['simulacion_en_curso'] = True

    # Mover procesos de 'Nuevo' a 'Listo'
    while estado_simulacion['nuevo']:
        proceso_dict = estado_simulacion['nuevo'].pop(0)
        proceso = Proceso.from_dict(proceso_dict)
        proceso.estado = 'Listo'
        estado_simulacion['listo'].append(proceso.to_dict())
    
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

    # Separar procesos con y sin preeminencia
    procesos_preeminentes = [p for p in bloqueado if p.preeminencia]
    procesos_no_preeminentes = [p for p in bloqueado if not p.preeminencia]

    # Intentar desbloquear procesos preeminentes primero
    for proceso in procesos_preeminentes:
        if recursos_disponibles(proceso, recursos_disponibles_dict):
            asignar_recursos(proceso, recursos_disponibles_dict)
            proceso.recursos_obtenidos = proceso.recursos_requeridos[:]
            bloqueado.remove(proceso)
            proceso.estado = 'Listo'
            proceso.recursos_faltantes = []
            estado_simulacion['listo'].append(proceso.to_dict())
        else:
            proceso.recursos_faltantes = obtener_recursos_faltantes(proceso, recursos_disponibles_dict)

    # Luego intentar desbloquear procesos sin preeminencia
    for proceso in procesos_no_preeminentes:
        if recursos_disponibles(proceso, recursos_disponibles_dict):
            asignar_recursos(proceso, recursos_disponibles_dict)
            proceso.recursos_obtenidos = proceso.recursos_requeridos[:]
            bloqueado.remove(proceso)
            proceso.estado = 'Listo'
            proceso.recursos_faltantes = []
            estado_simulacion['listo'].append(proceso.to_dict())
        else:
            proceso.recursos_faltantes = obtener_recursos_faltantes(proceso, recursos_disponibles_dict)

    estado_simulacion['bloqueado'] = [p.to_dict() for p in bloqueado]


def asignar_procesos(estado_simulacion):
    listo = [Proceso.from_dict(p) for p in estado_simulacion['listo']]
    ejecutando = [Proceso.from_dict(p) for p in estado_simulacion['ejecutando']]
    recursos_disponibles_dict = estado_simulacion['recursos_disponibles_dict']

    # Separar procesos con y sin preeminencia
    procesos_preeminentes = [p for p in listo if p.preeminencia]
    procesos_no_preeminentes = [p for p in listo if not p.preeminencia]

    # Asignar procesos preeminentes primero
    for proceso in procesos_preeminentes:
        if len(ejecutando) < 1:
            if proceso.recursos_obtenidos == proceso.recursos_requeridos:
                listo.remove(proceso)
                proceso.estado = 'Ejecutando'
                proceso.veces_ejecutando += 1
                ejecutando.append(proceso)
            elif recursos_disponibles(proceso, recursos_disponibles_dict):
                asignar_recursos(proceso, recursos_disponibles_dict)
                proceso.recursos_obtenidos = proceso.recursos_requeridos[:]
                listo.remove(proceso)
                proceso.estado = 'Ejecutando'
                proceso.veces_ejecutando += 1
                ejecutando.append(proceso)
            else:
                proceso.estado = 'Bloqueado'
                proceso.recursos_faltantes = obtener_recursos_faltantes(proceso, recursos_disponibles_dict)
                listo.remove(proceso)
                estado_simulacion['bloqueado'].append(proceso.to_dict())

    # Si no hay procesos preeminentes o la CPU está libre, asignar los demás
    if len(ejecutando) < 1:
        for proceso in procesos_no_preeminentes:
            if len(ejecutando) < 1:
                if proceso.recursos_obtenidos == proceso.recursos_requeridos:
                    listo.remove(proceso)
                    proceso.estado = 'Ejecutando'
                    proceso.veces_ejecutando += 1
                    ejecutando.append(proceso)
                elif recursos_disponibles(proceso, recursos_disponibles_dict):
                    asignar_recursos(proceso, recursos_disponibles_dict)
                    proceso.recursos_obtenidos = proceso.recursos_requeridos[:]
                    listo.remove(proceso)
                    proceso.estado = 'Ejecutando'
                    proceso.veces_ejecutando += 1
                    ejecutando.append(proceso)
                else:
                    proceso.estado = 'Bloqueado'
                    proceso.recursos_faltantes = obtener_recursos_faltantes(proceso, recursos_disponibles_dict)
                    listo.remove(proceso)
                    estado_simulacion['bloqueado'].append(proceso.to_dict())

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
         # Almacenar el tamaño anterior
        tamaño_anterior = proceso.tamaño
        # Reducir tamaño en 1 unidad por ciclo
        proceso.tamaño -= 1
        proceso.unidades_ejecutadas += 1

        # Calcular la cantidad reducida
        cantidad_reducida = tamaño_anterior - proceso.tamaño
        # Actualizar la asignación de memoria
        success, msg = memory_manager.reduce_process_size(proceso.id, cantidad_reducida)
        if not success:
            print(f"Error al reducir el tamaño del proceso en memoria: {msg}")

        if proceso.tamaño <= 0:
            proceso.estado = 'Terminado'
            procesos_terminados.append(proceso)
            # Eliminar el proceso de la memoria
            memory_manager.delete_process_memory(proceso.id)
        elif proceso.unidades_ejecutadas >= 5:
            # Ha ejecutado 5 unidades, debe ser interrumpido
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
        if not proceso.preeminencia:
            # Solo los procesos sin preeminencia tienen probabilidad de liberar recursos
            if random.random() < 0.2:
                liberar_recursos(proceso, recursos_disponibles_dict)
                proceso.recursos_obtenidos.clear()
        # Los procesos con preeminencia retienen sus recursos
        listo.append(proceso)
        proceso.unidades_ejecutadas = 0  # Reiniciar contador de unidades ejecutadas


    estado_simulacion['ejecutando'] = [p.to_dict() for p in ejecutando if p not in procesos_terminados and p not in procesos_a_listo]
    estado_simulacion['terminado'].extend([p.to_dict() for p in procesos_terminados])
    estado_simulacion['listo'].extend([p.to_dict() for p in procesos_a_listo])
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

# Crear el filtro personalizado
@app.template_filter('ceil')
def ceil_filter(value):
    return math.ceil(value)

@app.route('/generar_reporte')
def generar_reporte():
    estado_simulacion = get_estado_simulacion()
    reporte_datos = []

    for estado in ESTADOS:
        procesos = [Proceso.from_dict(p) for p in estado_simulacion[estado.lower()]]
        for proceso in procesos:
            proceso_info = {
                'id': proceso.id,
                'tamaño_inicial': proceso.tamaño_inicial,
                'tamaño_restante': proceso.tamaño,
                'estado': proceso.estado,
                'preeminencia': proceso.preeminencia,
                'recursos_obtenidos': ', '.join(proceso.recursos_obtenidos) if proceso.recursos_obtenidos else 'Ninguno',
                'recursos_faltantes': ', '.join(proceso.recursos_faltantes) if proceso.recursos_faltantes else '',
                'veces_ejecutando': proceso.veces_ejecutando,
            }
            reporte_datos.append(proceso_info)

    return render_template('reporte.html', reporte_datos=reporte_datos)

@app.route('/memoria')
def memoria():
    message = request.args.get('message', '')
    return render_template('memoria.html', ram=memory_manager.ram, rom=memory_manager.rom, processes=memory_manager.processes, message=message)

@app.route('/reiniciar_simulacion')
def reiniciar_simulacion():
    # Reinicia el estado de la simulación de procesos
    session.pop('estado_simulacion', None)
    
    # Reinicia el estado de la memoria
    memory_manager.init_memory()  # Esta es la llamada para limpiar la memoria

    return redirect(url_for('index'))

# Inicializar la memoria una vez al inicio
memory_manager.init_memory()


if __name__ == '__main__':
    app.run(debug=True)
