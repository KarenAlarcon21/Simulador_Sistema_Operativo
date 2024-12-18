from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import memory_manager
import random
import math

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'

# Estados posibles para los hilos (mismo nombre que para procesos)
ESTADOS = ['Nuevo', 'Listo', 'Ejecutando', 'Bloqueado', 'Terminado']

# Recursos disponibles globales
RECURSOS_DISPONIBLES = ['Recurso1', 'Recurso2', 'Recurso3', 'Recurso4', 'Recurso5', 'Recurso6']

def generar_hilos(id_proceso, tamaño_inicial, recursos_requeridos, preeminencia):
    """
    Genera una lista de hilos para un proceso dado su tamaño.
    Regla:
      - 1-20  -> 1 hilo
      - 21-40 -> 2 hilos
      - 41-65 -> 3 hilos
    """
    if tamaño_inicial <= 20:
        num_hilos = 1
    elif tamaño_inicial <= 40:
        num_hilos = 2
    else:
        num_hilos = 3

    # División de tamaño entre hilos
    tam_por_hilo = math.ceil(tamaño_inicial / num_hilos)

    # Repartir recursos en orden (round-robin)
    hilos = []
    for i in range(num_hilos):
        recursos_hilo = recursos_requeridos[i::num_hilos]
        hilo_dict = {
            'id_hilo': f"{id_proceso}-h{i+1}",
            'tamaño_hilo_inicial': tam_por_hilo,
            'tamaño_hilo': tam_por_hilo,
            'recursos_hilo': recursos_hilo,
            'estado': 'Nuevo',
            'preeminencia': preeminencia,
            'recursos_obtenidos': [],
            'unidades_ejecutadas': 0,
            'recursos_faltantes': [],
            'proceso_id': id_proceso,
            'processor_id': None,  # Se asignará luego al ejecutar
            'veces_ejecutando': 0
        }
        hilos.append(hilo_dict)
    return hilos


class Proceso:
    def __init__(self, id_proceso, tamaño, recursos_requeridos, preeminencia=False):
        self.id = id_proceso
        self.tamaño = int(tamaño)         # Tamaño global del proceso en memoria
        self.tamaño_inicial = int(tamaño)
        self.recursos_requeridos = recursos_requeridos
        self.estado = 'Nuevo'
        self.preeminencia = preeminencia
        # Generar hilos según regla:
        self.hilos = generar_hilos(self.id, self.tamaño_inicial, recursos_requeridos, preeminencia)

    def __str__(self):
        return f"ID: {self.id}, Tamaño: {self.tamaño_inicial}, Estado: {self.estado}, Preeminencia: {self.preeminencia}"

    def to_dict(self):
        return {
            'id': self.id,
            'tamaño': self.tamaño,
            'tamaño_inicial': self.tamaño_inicial,
            'recursos_requeridos': self.recursos_requeridos,
            'estado': self.estado,
            'preeminencia': self.preeminencia,
            'hilos': self.hilos,
        }

    @staticmethod
    def from_dict(data):
        p = Proceso(data['id'], data['tamaño_inicial'], data['recursos_requeridos'], preeminencia=data.get('preeminencia', False))
        p.tamaño = data['tamaño']
        p.estado = data['estado']
        p.hilos = data.get('hilos', [])
        return p


def get_estado_simulacion():
    """
    Recupera el estado de la simulación de la sesión,
    o lo crea si no existe.
    """
    if 'estado_simulacion' not in session:
        session['estado_simulacion'] = {
            'recursos_disponibles_dict': {recurso: True for recurso in RECURSOS_DISPONIBLES},
            'nuevo': [],        # lista de hilos
            'listo': [],
            'ejecutando': [],
            'bloqueado': [],
            'terminado': [],
            'simulacion_en_curso': False,
            'simulacion_pausada': False,
        }
    return session['estado_simulacion']


def guardar_estado_simulacion(estado_simulacion):
    session['estado_simulacion'] = estado_simulacion


def id_ya_existe(id_proceso, estado_simulacion):
    """
    Verifica si ya existe un proceso con ese id en la simulación,
    revisando los hilos en todos los estados.
    """
    for estado in ESTADOS:
        for hilo in estado_simulacion[estado.lower()]:
            if hilo.get('proceso_id', '') == id_proceso:
                return True
    return False


@app.route('/')
def index():
    estado_simulacion = get_estado_simulacion()
    # Recolectar hilos por estado para la tabla
    procesos_por_estado = {}
    for estado in ESTADOS:
        procesos_por_estado[estado] = estado_simulacion[estado.lower()]

    simulacion_en_curso = estado_simulacion.get('simulacion_en_curso', False)
    simulacion_pausada = estado_simulacion.get('simulacion_pausada', False)
    return render_template(
        'index.html', 
        estados=ESTADOS, 
        procesos=procesos_por_estado, 
        simulacion_en_curso=simulacion_en_curso, 
        simulacion_pausada=simulacion_pausada
    )

@app.route('/agregar_proceso', methods=['GET', 'POST'])
def agregar_proceso():
    estado_simulacion = get_estado_simulacion()
    
    # Contar procesos únicos
    procesos_existentes = set()
    for estado in ESTADOS:
        for hilo in estado_simulacion[estado.lower()]:
            procesos_existentes.add(hilo.get('proceso_id', ''))
    
    numero_procesos = len(procesos_existentes)
    MAX_PROCESOS = 6  # Límite de procesos
    MAX_TAMANO = 65   # Tamaño máximo permitido
    
    if request.method == 'POST':
        if numero_procesos >= MAX_PROCESOS:
            error = f"Has alcanzado el límite máximo de {MAX_PROCESOS} procesos."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)
        
        id_proceso = request.form.get('id_proceso', '').lower()
        tamaño = request.form.get('tamaño', '')
        recursos_requeridos = request.form.getlist('recursos')
        preeminencia = request.form.get('preeminencia') == 'True'

        # Validación básica
        if not id_proceso or not tamaño.isdigit():
            error = "Por favor, ingrese un ID válido y un tamaño numérico."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)
        
        tamaño_int = int(tamaño)
        if tamaño_int > MAX_TAMANO:
            error = f"El tamaño del proceso no puede exceder {MAX_TAMANO}."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)
        
        if id_ya_existe(id_proceso, estado_simulacion):
            error = f"Ya existe un proceso con el ID '{id_proceso}'. Elija otro."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

        # Crear Proceso e hilos
        nuevo_proceso = Proceso(id_proceso, tamaño_int, recursos_requeridos, preeminencia=preeminencia)

        # Asignar memoria global al proceso (tamaño total)
        success, msg = memory_manager.create_process_memory(id_proceso, float(tamaño_int))
        if not success:
            error = f"No se pudo asignar memoria al proceso: {msg}"
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

        # Meter cada hilo en 'nuevo'
        for hilo_dict in nuevo_proceso.hilos:
            hilo_dict['estado'] = 'Nuevo'
            estado_simulacion['nuevo'].append(hilo_dict)

        guardar_estado_simulacion(estado_simulacion)
        return redirect(url_for('index'))
    else:
        # En la solicitud GET, verificar si ya se alcanzó el límite
        if numero_procesos >= MAX_PROCESOS:
            mensaje = f"Has alcanzado el límite máximo de {MAX_PROCESOS} procesos."
            return render_template('agregar_proceso.html', mensaje=mensaje, recursos=RECURSOS_DISPONIBLES, limite_alcanzado=True)
        else:
            return render_template('agregar_proceso.html', recursos=RECURSOS_DISPONIBLES)

@app.route('/iniciar_simulacion')
def iniciar_simulacion():
    estado_simulacion = get_estado_simulacion()

    if not estado_simulacion.get('simulacion_en_curso', False):
        nuevos_hilos = estado_simulacion.get('nuevo', [])
        procesos_terminados = estado_simulacion.get('terminado', [])
        estado_simulacion = {
            'recursos_disponibles_dict': {r: True for r in RECURSOS_DISPONIBLES},
            'nuevo': nuevos_hilos,
            'listo': [],
            'ejecutando': [],
            'bloqueado': [],
            'terminado': procesos_terminados,
            'simulacion_en_curso': True,
            'simulacion_pausada': False,
        }
    else:
        estado_simulacion['simulacion_pausada'] = False
        estado_simulacion['simulacion_en_curso'] = True

    # Mover hilos de 'Nuevo' a 'Listo'
    while estado_simulacion['nuevo']:
        hilo_dict = estado_simulacion['nuevo'].pop(0)
        hilo_dict['estado'] = 'Listo'
        estado_simulacion['listo'].append(hilo_dict)

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
    return '', 204


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
        procesos_por_estado[estado] = estado_simulacion[estado.lower()]

    simulacion_en_curso = estado_simulacion.get('simulacion_en_curso', False)
    simulacion_pausada = estado_simulacion.get('simulacion_pausada', False)

    return jsonify({
        'estados': ESTADOS,
        'procesos': procesos_por_estado,  # En realidad son hilos, pero conservamos la estructura
        'simulacion_en_curso': simulacion_en_curso,
        'simulacion_pausada': simulacion_pausada
    })


@app.route('/avanzar_simulacion')
def avanzar_simulacion():
    estado_simulacion = get_estado_simulacion()
    if not estado_simulacion.get('simulacion_en_curso', False):
        return jsonify({'simulacion_en_curso': False})

    if estado_simulacion.get('simulacion_pausada', False):
        # No avanzar, solo devolver estado
        procesos_por_estado = {}
        for estado in ESTADOS:
            procesos_por_estado[estado] = estado_simulacion[estado.lower()]
        return jsonify({
            'estados': ESTADOS,
            'procesos': procesos_por_estado,
            'simulacion_en_curso': True,
            'simulacion_pausada': True
        })

    # Paso de simulación
    desbloquear_procesos(estado_simulacion)
    asignar_procesos(estado_simulacion)
    ejecutar_procesos(estado_simulacion)

    # Verificar si ya no quedan hilos en listo, bloqueado o ejecutando
    if not estado_simulacion['listo'] and not estado_simulacion['bloqueado'] and not estado_simulacion['ejecutando']:
        estado_simulacion['simulacion_en_curso'] = False

    guardar_estado_simulacion(estado_simulacion)
    procesos_por_estado = {}
    for estado in ESTADOS:
        procesos_por_estado[estado] = estado_simulacion[estado.lower()]

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

    # Un único paso de simulación
    desbloquear_procesos(estado_simulacion)
    asignar_procesos(estado_simulacion)
    ejecutar_procesos(estado_simulacion)

    # Verificar fin de simulación
    if not estado_simulacion['listo'] and not estado_simulacion['bloqueado'] and not estado_simulacion['ejecutando']:
        estado_simulacion['simulacion_en_curso'] = False

    guardar_estado_simulacion(estado_simulacion)
    return redirect(url_for('index'))


def desbloquear_procesos(estado_simulacion):
    bloqueado = estado_simulacion['bloqueado']
    recursos_disponibles_dict = estado_simulacion['recursos_disponibles_dict']

    hilos_preeminentes = [h for h in bloqueado if h['preeminencia']]
    hilos_no_preeminentes = [h for h in bloqueado if not h['preeminencia']]

    # Desbloquear preeminentes primero
    for hilo in hilos_preeminentes:
        if recursos_disponibles_para_hilo(hilo, recursos_disponibles_dict):
            asignar_recursos_hilo(hilo, recursos_disponibles_dict)
            hilo['recursos_obtenidos'] = list(hilo['recursos_hilo'])
            bloqueado.remove(hilo)
            hilo['estado'] = 'Listo'
            hilo['recursos_faltantes'] = []
            estado_simulacion['listo'].append(hilo)
        else:
            hilo['recursos_faltantes'] = obtener_recursos_faltantes_hilo(hilo, recursos_disponibles_dict)

    # Desbloquear no preeminentes
    for hilo in hilos_no_preeminentes:
        if recursos_disponibles_para_hilo(hilo, recursos_disponibles_dict):
            asignar_recursos_hilo(hilo, recursos_disponibles_dict)
            hilo['recursos_obtenidos'] = list(hilo['recursos_hilo'])
            bloqueado.remove(hilo)
            hilo['estado'] = 'Listo'
            hilo['recursos_faltantes'] = []
            estado_simulacion['listo'].append(hilo)
        else:
            hilo['recursos_faltantes'] = obtener_recursos_faltantes_hilo(hilo, recursos_disponibles_dict)

    estado_simulacion['bloqueado'] = bloqueado


def asignar_procesos(estado_simulacion):
    listo = estado_simulacion['listo']
    ejecutando = estado_simulacion['ejecutando']
    bloqueado = estado_simulacion['bloqueado']
    recursos_disponibles_dict = estado_simulacion['recursos_disponibles_dict']

    # Separar hilos preeminentes de los no preeminentes
    hilos_preeminentes = [h for h in listo if h['preeminencia']]
    hilos_no_preeminentes = [h for h in listo if not h['preeminencia']]

    def intentar_asignar_hilo(hilo):
        """Intenta asignar el hilo a un procesador libre y gestiona bloqueo si no hay recursos."""
        # Detectar qué CPU están ya ocupados
        used_processor_ids = set(h['processor_id'] for h in ejecutando if h['processor_id'] is not None)
        # Procesadores libres (1, 2 y 3)
        available_processor_ids = [p for p in [1, 2, 3] if p not in used_processor_ids]

        # Si no hay CPU disponible, no se asigna todavía
        if not available_processor_ids:
            return False

        # 1) Si el hilo ya tiene todos sus recursos
        if set(hilo['recursos_hilo']).issubset(set(hilo['recursos_obtenidos'])):
            pass  # Pasa al siguiente paso: asignar CPU
        # 2) No los tiene, pero hay recursos disponibles
        elif recursos_disponibles_para_hilo(hilo, recursos_disponibles_dict):
            asignar_recursos_hilo(hilo, recursos_disponibles_dict)
            hilo['recursos_obtenidos'] = list(hilo['recursos_hilo'])
        else:
            # No logra obtener recursos; se bloquea
            hilo['estado'] = 'Bloqueado'
            hilo['recursos_faltantes'] = obtener_recursos_faltantes_hilo(hilo, recursos_disponibles_dict)
            bloqueado.append(hilo)
            return True  # Ya está gestionado (movido a bloqueado), no sigue en 'listo'

        # Asignar el primer procesador libre al hilo
        hilo['estado'] = 'Ejecutando'
        hilo['processor_id'] = available_processor_ids[0]
        hilo['veces_ejecutando'] += 1
        ejecutando.append(hilo)
        return True

    # Asignar primero hilos preeminentes
    for hilo in hilos_preeminentes[:]:
        if intentar_asignar_hilo(hilo):
            listo.remove(hilo)

    # Luego asignar hilos no preeminentes
    for hilo in hilos_no_preeminentes[:]:
        if intentar_asignar_hilo(hilo):
            listo.remove(hilo)

    # Actualizar el estado de la simulación
    estado_simulacion['listo'] = listo
    estado_simulacion['ejecutando'] = ejecutando
    estado_simulacion['bloqueado'] = bloqueado



def ejecutar_procesos(estado_simulacion):
    ejecutando = estado_simulacion['ejecutando']
    terminado = estado_simulacion['terminado']
    listo = estado_simulacion['listo']
    recursos_disponibles_dict = estado_simulacion['recursos_disponibles_dict']

    hilos_a_listo = []
    hilos_terminados = []

    for hilo in ejecutando:
        # Reducir tamaño del hilo
        tamaño_anterior = hilo['tamaño_hilo']
        hilo['tamaño_hilo'] -= 1
        hilo['unidades_ejecutadas'] += 1

        # Reducir en 1 unidad la memoria global del proceso en memory_manager
        cantidad_reducida = tamaño_anterior - hilo['tamaño_hilo']  # normalmente 1
        if cantidad_reducida > 0:
            success, msg = memory_manager.reduce_process_size(hilo['proceso_id'], cantidad_reducida)
            if not success:
                print(f"Error al reducir tamaño en memoria: {msg}")

        # Verificar si terminó
        if hilo['tamaño_hilo'] <= 0:
            hilo['estado'] = 'Terminado'
            liberar_recursos_hilo(hilo, recursos_disponibles_dict)
            hilo['recursos_obtenidos'] = []
            hilos_terminados.append(hilo)
        elif hilo['unidades_ejecutadas'] >= 5:
            # Interrupción
            hilo['estado'] = 'Listo'
            hilos_a_listo.append(hilo)
        else:
            hilo['estado'] = 'Ejecutando'

    # Sacar hilos de 'ejecutando' y reubicar
    for h in hilos_terminados:
        ejecutando.remove(h)
        liberar_recursos_hilo(h, recursos_disponibles_dict)
        h['processor_id'] = None  # dejarlo claro
        terminado.append(h)

    for h in hilos_a_listo:
        ejecutando.remove(h)
        if not h['preeminencia']:
            if random.random() < 0.2:
                liberar_recursos_hilo(h, recursos_disponibles_dict)
                h['recursos_obtenidos'].clear()
        h['unidades_ejecutadas'] = 0
        h['processor_id'] = None  # sale del CPU, libera su id
        listo.append(h)

    estado_simulacion['ejecutando'] = [h for h in ejecutando if h not in hilos_terminados and h not in hilos_a_listo]
    estado_simulacion['terminado'] = terminado
    estado_simulacion['listo'] = listo
    estado_simulacion['recursos_disponibles_dict'] = recursos_disponibles_dict

    # Verificar si un proceso (todos sus hilos) finalizó completamente
    chequear_procesos_completos(estado_simulacion)


def chequear_procesos_completos(estado_simulacion):
    """
    Libera la memoria del proceso si TODOS sus hilos están en 'terminado'.
    """
    terminado = estado_simulacion['terminado']  # hilos terminados

    # Recolectar los proceso_id que aún tienen hilos en otros estados
    procesos_vivos = set()
    for st in ['nuevo', 'listo', 'bloqueado', 'ejecutando']:
        for h in estado_simulacion[st]:
            procesos_vivos.add(h['proceso_id'])

    # En 'terminado' agrupar por proceso_id
    from collections import defaultdict
    hilos_terminados_por_proceso = defaultdict(int)
    for h in terminado:
        hilos_terminados_por_proceso[h['proceso_id']] += 1

    # Ver si hay un proceso_id que no está en procesos_vivos => todos sus hilos se terminaron
    for proceso_id, count_hilos in hilos_terminados_por_proceso.items():
        if proceso_id not in procesos_vivos:
            # Liberar memoria del proceso
            memory_manager.delete_process_memory(proceso_id)
            print(f"Proceso {proceso_id} COMPLETAMENTE terminado. Memoria liberada.")


def recursos_disponibles_para_hilo(hilo, recursos_disponibles_dict):
    for r in hilo['recursos_hilo']:
        if not recursos_disponibles_dict.get(r, True):
            return False
    return True


def obtener_recursos_faltantes_hilo(hilo, recursos_disponibles_dict):
    faltantes = []
    for r in hilo['recursos_hilo']:
        if not recursos_disponibles_dict.get(r, True):
            faltantes.append(r)
    return faltantes


def asignar_recursos_hilo(hilo, recursos_disponibles_dict):
    for r in hilo['recursos_hilo']:
        recursos_disponibles_dict[r] = False


def liberar_recursos_hilo(hilo, recursos_disponibles_dict):
    for r in hilo['recursos_hilo']:
        recursos_disponibles_dict[r] = True

@app.template_filter('ceil')
def ceil_filter(value):
    import math
    return math.ceil(value)

@app.route('/generar_reporte')
def generar_reporte():
    estado_simulacion = get_estado_simulacion()
    reporte_datos = []
    # Recorrer cada estado y cada hilo
    for estado in ESTADOS:
        for hilo in estado_simulacion[estado.lower()]:
            hilo_info = {
                'id': hilo['id_hilo'],
                'proceso_id': hilo['proceso_id'],
                'tamaño_hilo_inicial': hilo['tamaño_hilo_inicial'],
                'tamaño_hilo': hilo['tamaño_hilo'],
                'estado': hilo['estado'],
                'preeminencia': hilo['preeminencia'],
                'recursos_obtenidos': ', '.join(hilo['recursos_obtenidos']) if hilo['recursos_obtenidos'] else 'Ninguno',
                'recursos_faltantes': ', '.join(hilo['recursos_faltantes']) if hilo['recursos_faltantes'] else '',
                'processor_id': hilo['processor_id'] if hilo.get('processor_id') else '-',
                'veces_ejecutando': hilo.get('veces_ejecutando', 0)
            }
            reporte_datos.append(hilo_info)

    return render_template('reporte.html', reporte_datos=reporte_datos)


@app.route('/memoria')
def memoria():
    message = request.args.get('message', '')
    return render_template('memoria.html', 
                           ram=memory_manager.ram, 
                           rom=memory_manager.rom, 
                           processes=memory_manager.processes, 
                           message=message)


@app.route('/reiniciar_simulacion')
def reiniciar_simulacion():
    # Borrar estado de la simulación
    session.pop('estado_simulacion', None)
    # Reinicia la memoria
    memory_manager.init_memory()
    return redirect(url_for('index'))


# Inicializar la memoria
memory_manager.init_memory()

if __name__ == '__main__':
    app.run(debug=True)
