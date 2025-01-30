from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import memory_manager
import math
import random

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'

# Estados posibles (para tus hilos)
ESTADOS = ['Nuevo', 'Listo', 'Ejecutando', 'Bloqueado', 'Terminado']
RECURSOS_DISPONIBLES = ['Recurso1', 'Recurso2', 'Recurso3', 'Recurso4', 'Recurso5', 'Recurso6']

def generar_hilos(id_proceso, tamaño_inicial, recursos_requeridos, preeminencia):
    """
    Crea la lista de diccionarios con la información de los hilos de un proceso,
    pero NO asigna memoria aquí. Simplemente define la estructura.
    """
    if tamaño_inicial <= 20:
        num_hilos = 1
    elif tamaño_inicial <= 40:
        num_hilos = 2
    else:
        num_hilos = 3

    tam_por_hilo = math.ceil(tamaño_inicial / num_hilos)
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
            'processor_id': None,
            'veces_ejecutando': 0
        }
        hilos.append(hilo_dict)
    return hilos

# -------------- Manejo de Sesión / Estado de Simulación --------------
def get_estado_simulacion():
    if 'estado_simulacion' not in session:
        session['estado_simulacion'] = {
            'recursos_disponibles_dict': {r: True for r in RECURSOS_DISPONIBLES},
            'nuevo': [],
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
    for estado in ESTADOS:
        for hilo in estado_simulacion[estado.lower()]:
            if hilo.get('proceso_id', '') == id_proceso:
                return True
    return False

# -------------- Rutas --------------
@app.route('/')
def index():
    estado_simulacion = get_estado_simulacion()
    procesos_por_estado = {}
    for st in ESTADOS:
        procesos_por_estado[st] = estado_simulacion[st.lower()]

    simulacion_en_curso = estado_simulacion.get('simulacion_en_curso', False)
    simulacion_pausada = estado_simulacion.get('simulacion_pausada', False)

    return render_template('index.html',
                           estados=ESTADOS,
                           procesos=procesos_por_estado,
                           simulacion_en_curso=simulacion_en_curso,
                           simulacion_pausada=simulacion_pausada)

@app.route('/agregar_proceso', methods=['GET','POST'])
def agregar_proceso():
    estado_simulacion = get_estado_simulacion()

    # Contar procesos únicos
    procesos_existentes = set(h.get('proceso_id', '') for st in ESTADOS for h in estado_simulacion[st.lower()])
    numero_procesos = len(procesos_existentes)
    MAX_PROCESOS = 6
    MAX_TAMANO = 65

    if request.method == 'POST':
        if numero_procesos >= MAX_PROCESOS:
            error = f"Has alcanzado el límite de {MAX_PROCESOS} procesos."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

        id_proceso = request.form.get('id_proceso', '').lower()
        tamaño = request.form.get('tamaño', '')
        recursos_requeridos = request.form.getlist('recursos')
        preeminencia = request.form.get('preeminencia') == 'True'

        if not id_proceso or not tamaño.isdigit():
            error = "Por favor, ingrese ID y tamaño numérico."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

        tamaño_int = int(tamaño)
        if tamaño_int > MAX_TAMANO:
            error = f"El tamaño no puede exceder {MAX_TAMANO}."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

        if id_ya_existe(id_proceso, estado_simulacion):
            error = f"Ya existe un proceso con ID '{id_proceso}'."
            return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

        # Generamos los hilos localmente
        lista_hilos = generar_hilos(id_proceso, tamaño_int, recursos_requeridos, preeminencia)

        # Por cada hilo, reservamos memoria en memory_manager
        for hilo_dict in lista_hilos:
            success, msg = memory_manager.create_hilo_memory(
                process_id=id_proceso,
                hilo_id=hilo_dict['id_hilo'],
                size=float(hilo_dict['tamaño_hilo'])
            )
            if not success:
                error = f"No se pudo asignar memoria para el hilo {hilo_dict['id_hilo']}: {msg}"
                return render_template('agregar_proceso.html', error=error, recursos=RECURSOS_DISPONIBLES)

            # Si la memoria se asignó correctamente, pasamos este hilo a estado "Nuevo"
            estado_simulacion['nuevo'].append(hilo_dict)

        guardar_estado_simulacion(estado_simulacion)
        return redirect(url_for('index'))

    else:
        if numero_procesos >= MAX_PROCESOS:
            mensaje = f"Límite máximo de {MAX_PROCESOS} procesos alcanzado."
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
    for st in ESTADOS:
        procesos_por_estado[st] = estado_simulacion[st.lower()]

    return jsonify({
        'estados': ESTADOS,
        'procesos': procesos_por_estado,
        'simulacion_en_curso': estado_simulacion.get('simulacion_en_curso', False),
        'simulacion_pausada': estado_simulacion.get('simulacion_pausada', False)
    })

@app.route('/avanzar_simulacion')
def avanzar_simulacion():
    estado_simulacion = get_estado_simulacion()
    if not estado_simulacion.get('simulacion_en_curso', False):
        return jsonify({'simulacion_en_curso': False})

    if estado_simulacion.get('simulacion_pausada', False):
        # Sólo devolvemos estado, sin avanzar
        procesos_por_estado = {}
        for st in ESTADOS:
            procesos_por_estado[st] = estado_simulacion[st.lower()]
        return jsonify({
            'estados': ESTADOS,
            'procesos': procesos_por_estado,
            'simulacion_en_curso': True,
            'simulacion_pausada': True
        })

    # Simulación: desbloqueo, asignación y ejecución
    desbloquear_procesos(estado_simulacion)
    asignar_procesos(estado_simulacion)
    ejecutar_procesos(estado_simulacion)

    # Verificar si ya no hay hilos en listo, bloqueado o ejecutando
    if not estado_simulacion['listo'] and not estado_simulacion['bloqueado'] and not estado_simulacion['ejecutando']:
        estado_simulacion['simulacion_en_curso'] = False

    guardar_estado_simulacion(estado_simulacion)
    procesos_por_estado = {}
    for st in ESTADOS:
        procesos_por_estado[st] = estado_simulacion[st.lower()]

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

    desbloquear_procesos(estado_simulacion)
    asignar_procesos(estado_simulacion)
    ejecutar_procesos(estado_simulacion)

    if not estado_simulacion['listo'] and not estado_simulacion['bloqueado'] and not estado_simulacion['ejecutando']:
        estado_simulacion['simulacion_en_curso'] = False

    guardar_estado_simulacion(estado_simulacion)
    return redirect(url_for('index'))

def desbloquear_procesos(estado_simulacion):
    bloqueado = estado_simulacion['bloqueado']
    recursos_disponibles_dict = estado_simulacion['recursos_disponibles_dict']

    hilos_pre = [h for h in bloqueado if h['preeminencia']]
    hilos_no_pre = [h for h in bloqueado if not h['preeminencia']]

    for hilo in hilos_pre:
        if recursos_disponibles_para_hilo(hilo, recursos_disponibles_dict):
            asignar_recursos_hilo(hilo, recursos_disponibles_dict)
            hilo['recursos_obtenidos'] = list(hilo['recursos_hilo'])
            bloqueado.remove(hilo)
            hilo['estado'] = 'Listo'
            hilo['recursos_faltantes'] = []
            estado_simulacion['listo'].append(hilo)
        else:
            hilo['recursos_faltantes'] = obtener_recursos_faltantes_hilo(hilo, recursos_disponibles_dict)

    for hilo in hilos_no_pre:
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

    hilos_pre = [h for h in listo if h['preeminencia']]
    hilos_no_pre = [h for h in listo if not h['preeminencia']]

    def intentar_asignar_hilo(h):
        used_processor_ids = set(x['processor_id'] for x in ejecutando if x['processor_id'] is not None)
        available_processor_ids = [p for p in [1,2,3] if p not in used_processor_ids]

        if not available_processor_ids:
            return False

        # Caso 1: ya tiene recursos
        if set(h['recursos_hilo']).issubset(set(h['recursos_obtenidos'])):
            pass
        # Caso 2: puede asignar recursos ahora
        elif recursos_disponibles_para_hilo(h, recursos_disponibles_dict):
            asignar_recursos_hilo(h, recursos_disponibles_dict)
            h['recursos_obtenidos'] = list(h['recursos_hilo'])
        else:
            h['estado'] = 'Bloqueado'
            h['recursos_faltantes'] = obtener_recursos_faltantes_hilo(h, recursos_disponibles_dict)
            bloqueado.append(h)
            return True  # se movió a bloqueado

        h['estado'] = 'Ejecutando'
        h['processor_id'] = available_processor_ids[0]
        h['veces_ejecutando'] += 1
        ejecutando.append(h)
        return True

    # Asignar preeminentes primero
    for hilo in hilos_pre[:]:
        if intentar_asignar_hilo(hilo):
            listo.remove(hilo)

    # Luego no preeminentes
    for hilo in hilos_no_pre[:]:
        if intentar_asignar_hilo(hilo):
            listo.remove(hilo)

    estado_simulacion['listo'] = listo
    estado_simulacion['ejecutando'] = ejecutando
    estado_simulacion['bloqueado'] = bloqueado

def ejecutar_procesos(estado_simulacion):
    ejecutando = estado_simulacion['ejecutando']
    terminado = estado_simulacion['terminado']
    listo = estado_simulacion['listo']
    recursos_dict = estado_simulacion['recursos_disponibles_dict']

    hilos_a_listo = []
    hilos_terminados = []

    for hilo in ejecutando:
        tamaño_anterior = hilo['tamaño_hilo']
        hilo['tamaño_hilo'] -= 1
        hilo['unidades_ejecutadas'] += 1

        cantidad_reducida = tamaño_anterior - hilo['tamaño_hilo']  # normalmente 1
        if cantidad_reducida > 0:
            success, msg = memory_manager.reduce_hilo_size(hilo['id_hilo'], cantidad_reducida)
            if not success:
                print(f"Error al reducir tamaño de {hilo['id_hilo']} en memoria: {msg}")

        if hilo['tamaño_hilo'] <= 0:
            hilo['estado'] = 'Terminado'
            liberar_recursos_hilo(hilo, recursos_dict)
            hilo['recursos_obtenidos'] = []
            hilos_terminados.append(hilo)
        elif hilo['unidades_ejecutadas'] >= 5:
            # interrupción
            hilo['estado'] = 'Listo'
            hilos_a_listo.append(hilo)
        else:
            hilo['estado'] = 'Ejecutando'

    for h in hilos_terminados:
        ejecutando.remove(h)
        liberar_recursos_hilo(h, recursos_dict)
        h['processor_id'] = None
        terminado.append(h)

    for h in hilos_a_listo:
        ejecutando.remove(h)
        if not h['preeminencia']:
            # 20% de probabilidad de liberar recursos
            if random.random() < 0.2:
                liberar_recursos_hilo(h, recursos_dict)
                h['recursos_obtenidos'].clear()
        h['unidades_ejecutadas'] = 0
        h['processor_id'] = None
        listo.append(h)

    estado_simulacion['ejecutando'] = [x for x in ejecutando if x not in hilos_terminados and x not in hilos_a_listo]
    estado_simulacion['terminado'] = terminado
    estado_simulacion['listo'] = listo
    estado_simulacion['recursos_disponibles_dict'] = recursos_dict

    chequear_procesos_completos(estado_simulacion)

def chequear_procesos_completos(estado_simulacion):
    terminado = estado_simulacion['terminado']

    # Recolectar todos los process_id que aparecen en los hilos 'terminado'
    # y contar cuantos hilos tiene cada proceso en 'terminado'
    from collections import defaultdict
    hilos_terminados_por_proceso = defaultdict(int)
    for h in terminado:
        if h['tamaño_hilo'] <= 0:
            hilos_terminados_por_proceso[h['proceso_id']] += 1

    # Verificar cuántos hilos tiene cada proceso en total (en la simulación entera)
    # Si el número de hilos terminados = total de hilos que se generaron para ese proceso
    # entonces eliminamos todos los hilos del proceso en memory_manager
    # Para ello, necesitamos saber cuántos hilos había al inicio para cada proceso.
    # Si no guardaste ese dato, puedes inferirlo: mira todos los estados (incluyendo terminado)
    # y cuenta hilos por proceso:
    proceso_hilo_count = defaultdict(int)
    for st in ['nuevo','listo','bloqueado','ejecutando','terminado']:
        for h in estado_simulacion[st]:
            proceso_hilo_count[h['proceso_id']] += 1

    # Ahora chequeamos si un proceso ya no tiene hilos en otros estados:
    # - Si el número de hilos terminados = total de hilos del proceso
    #   significa que todos sus hilos llegaron a 0.
    #   Es el momento de eliminar del memory_manager.
    for proceso_id, term_count in hilos_terminados_por_proceso.items():
        total_hilos = proceso_hilo_count[proceso_id]
        if term_count == total_hilos:
            # Todos los hilos de este proceso han finalizado.
            # Ahora eliminamos del memory_manager:
            memory_manager.delete_process_hilos(proceso_id)

            print(f"Proceso {proceso_id} COMPLETAMENTE terminado. Hilos borrados de la memoria.")


def recursos_disponibles_para_hilo(hilo, recursos_disponibles_dict):
    for r in hilo['recursos_hilo']:
        if not recursos_disponibles_dict.get(r, True):
            return False
    return True

def obtener_recursos_faltantes_hilo(hilo, recursos_disponibles_dict):
    return [r for r in hilo['recursos_hilo'] if not recursos_disponibles_dict.get(r, True)]

def asignar_recursos_hilo(hilo, recursos_disponibles_dict):
    for r in hilo['recursos_hilo']:
        recursos_disponibles_dict[r] = False

def liberar_recursos_hilo(hilo, recursos_disponibles_dict):
    for r in hilo['recursos_hilo']:
        recursos_disponibles_dict[r] = True

@app.route('/generar_reporte')
def generar_reporte():
    estado_simulacion = get_estado_simulacion()
    reporte_datos = []
    for st in ESTADOS:
        for hilo in estado_simulacion[st.lower()]:
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
    # memory_manager.hilos ahora es la lista global
    return render_template('memoria.html',
                           ram=memory_manager.ram,
                           rom=memory_manager.rom,
                           hilos=memory_manager.hilos,
                           message=message)

@app.route('/reiniciar_simulacion')
def reiniciar_simulacion():
    session.pop('estado_simulacion', None)
    memory_manager.init_memory()
    return redirect(url_for('index'))

# Inicializar memoria
memory_manager.init_memory()

if __name__ == '__main__':
    app.run(debug=True)
