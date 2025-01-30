import random

# -- Ajusta según tu preferencia, mayor "variation" implica colores más distintos --
COLOR_VARIATION = 0.15  # 15% de variación por canal

# Constantes
RAM_ROWS, RAM_COLS = 5, 5
ROM_ROWS, ROM_COLS = 5, 10  # Tamaño de la ROM es 5x10
FRAME_SIZE = 2.5
MAX_PROCESS_SIZE = 65

# Lista predeterminada de colores (base para procesos)
PREDEFINED_COLORS = ['#5dade2', '#76d7c4', '#e74c3c', '#0e03f5', '#1df503', '#f4d03f', '#e90075', '#b400e9']
available_colors = PREDEFINED_COLORS.copy()

# Inicializa la matriz de RAM y ROM
ram = []
rom = []

# --- Diccionario de colores por proceso ---
# A cada process_id se le asigna un color base. Los hilos de ese proceso tendrán
# variaciones de ese color.
process_base_colors = {}

# Lista global para almacenar los hilos creados
hilos = []

def init_memory():
    """Reinicia por completo la memoria y las estructuras globales."""
    global ram, rom, hilos, available_colors, process_base_colors
    ram = []

    # Primera fila ocupada por el S.O.
    so_row = [{'process': 'S.O.', 'frame_id': 'S.O.-0'} for _ in range(RAM_COLS)]
    ram.append(so_row)

    # Resto de filas inicializadas como libres
    for _ in range(RAM_ROWS - 1):
        row = [{'process': None, 'frame_id': None} for _ in range(RAM_COLS)]
        ram.append(row)

    # Inicializa la matriz de ROM
    rom = [[{'process': None, 'frame_id': None} for _ in range(ROM_COLS)] for _ in range(ROM_ROWS)]

    # Vaciar la lista de hilos
    hilos.clear()

    # Restaurar la lista de colores disponibles y el mapeo base
    available_colors = PREDEFINED_COLORS.copy()
    process_base_colors.clear()

class HiloMemoria:
    """
    Representa un hilo en memoria. Ahora cada hilo se gestiona de forma independiente.
    - process_id: ID del proceso al que pertenece el hilo.
    - hilo_id: identificador único del hilo (por ejemplo "proc1-h1", etc.)
    - size: tamaño actual del hilo.
    - color: color visual asignado a este hilo (variación del color base de su proceso).
    - frames: marcos (RAM o ROM) que le pertenecen.
    """
    def __init__(self, process_id, hilo_id, size, color):
        self.process_id = process_id
        self.hilo_id = hilo_id
        self.size_initial = size
        self.size = size
        self.color = color
        self.frames = []

def generate_similar_color(base_color, variation=COLOR_VARIATION):
    """
    Genera un color en formato hex cercano a 'base_color' introduciendo
    ligeras variaciones en cada canal RGB.
    """
    base_color = base_color.lstrip('#')
    r = int(base_color[0:2], 16)
    g = int(base_color[2:4], 16)
    b = int(base_color[4:6], 16)

    # Pequeñas variaciones aleatorias por canal
    delta_r = random.randint(int(-variation * 255), int(variation * 255))
    delta_g = random.randint(int(-variation * 255), int(variation * 255))
    delta_b = random.randint(int(-variation * 255), int(variation * 255))

    r = max(0, min(255, r + delta_r))
    g = max(0, min(255, g + delta_g))
    b = max(0, min(255, b + delta_b))

    return f'#{r:02x}{g:02x}{b:02x}'

def create_hilo_memory(process_id, hilo_id, size):
    """
    Crea un hilo en memoria. Cada hilo recibe su propia asignación de marcos (RAM/ROM),
    pero comparte color base con otros hilos del mismo proceso.
    """
    # Evitar duplicados: si ya existe un hilo con ese hilo_id
    if any(h.hilo_id == hilo_id for h in hilos):
        return False, f'Ya existe un hilo con ID "{hilo_id}".'

    # Determina o crea el color base del proceso
    if process_id not in process_base_colors:
        if not available_colors:
            return False, 'No hay más colores base disponibles.'
        base_color = random.choice(available_colors)
        available_colors.remove(base_color)
        process_base_colors[process_id] = base_color

    # Generamos un color similar al base
    base_color = process_base_colors[process_id]
    hilo_color = generate_similar_color(base_color)

    # Creamos el objeto HiloMemoria
    hilo_obj = HiloMemoria(process_id, hilo_id, size, hilo_color)

    total_frames_needed = int(size // FRAME_SIZE)
    if size % FRAME_SIZE != 0:
        total_frames_needed += 1  # Necesitamos marco extra si hay residuo

    # Por defecto: asignar hasta 3 marcos en RAM
    ram_frames_needed = min(3, total_frames_needed)
    rom_frames_needed = total_frames_needed - ram_frames_needed

    ram_positions = get_free_frames(ram, ram_frames_needed, start_row=1)  # Evitar fila 0 (S.O.)
    rom_positions = get_free_frames(rom, rom_frames_needed)

    if len(ram_positions) < ram_frames_needed or len(rom_positions) < rom_frames_needed:
        return False, 'No hay suficiente espacio en memoria RAM o ROM para este hilo.'

    # Asignamos los marcos a RAM
    for idx, (i, j) in enumerate(ram_positions, start=1):
        frame_id = f"{hilo_id}-{idx}"
        ram[i][j]['process'] = hilo_obj
        ram[i][j]['frame_id'] = frame_id
        hilo_obj.frames.append({'type': 'RAM', 'i': i, 'j': j, 'frame_id': frame_id})

    # Asignamos los marcos a ROM (si hace falta)
    for idx, (i, j) in enumerate(rom_positions, start=ram_frames_needed + 1):
        frame_id = f"{hilo_id}-{idx}"
        rom[i][j]['process'] = hilo_obj
        rom[i][j]['frame_id'] = frame_id
        hilo_obj.frames.append({'type': 'ROM', 'i': i, 'j': j, 'frame_id': frame_id})

    hilos.append(hilo_obj)
    return True, 'Hilo creado exitosamente.'

def get_free_frames(memory_matrix, frames_needed, start_row=0):
    """Devuelve una lista de (i,j) libres en la matriz 'memory_matrix' para 'frames_needed' marcos."""
    if frames_needed == 0:
        return []
    free_positions = []
    rows = len(memory_matrix)
    cols = len(memory_matrix[0])

    # Generamos todas las posiciones posibles a partir de start_row
    positions = [(i, j) for i in range(start_row, rows) for j in range(cols)]
    random.shuffle(positions)

    for (i, j) in positions:
        if memory_matrix[i][j]['process'] is None:
            free_positions.append((i, j))
            if len(free_positions) == frames_needed:
                break
    return free_positions

def delete_process_hilos(process_id):
    global hilos, ram, rom, available_colors, process_base_colors

    # Filtramos hilos del proceso
    hilos_del_proceso = [h for h in hilos if h.process_id == process_id]

    if not hilos_del_proceso:
        return False  # No hay hilos de ese proceso

    # Liberar marcos de todos los hilos del proceso
    for hilo_obj in hilos_del_proceso:
        for frame in hilo_obj.frames:
            if frame['type'] == 'RAM':
                ram[frame['i']][frame['j']]['process'] = None
                ram[frame['i']][frame['j']]['frame_id'] = None
            else:
                rom[frame['i']][frame['j']]['process'] = None
                rom[frame['i']][frame['j']]['frame_id'] = None

    # Eliminar hilos de la lista global
    hilos = [h for h in hilos if h.process_id != process_id]

    # Liberar el color base del proceso
    if process_id in process_base_colors:
        base_color = process_base_colors[process_id]
        available_colors.append(base_color)
        del process_base_colors[process_id]

    return True

def delete_hilo_memory(hilo_id):
    """
    Elimina un hilo completo de la memoria (RAM y ROM).
    Libera sus marcos y si no quedan más hilos de ese proceso,
    libera también el color base.
    """
    global hilos
    hilo_to_delete = next((h for h in hilos if h.hilo_id == hilo_id), None)
    if not hilo_to_delete:
        return False

    # Liberamos los marcos en RAM/ROM
    for frame in hilo_to_delete.frames:
        mem_type = frame['type']
        i, j = frame['i'], frame['j']
        if mem_type == 'RAM':
            ram[i][j]['process'] = None
            ram[i][j]['frame_id'] = None
        else:
            rom[i][j]['process'] = None
            rom[i][j]['frame_id'] = None

    # Guardar el process_id antes de eliminar el hilo
    pid = hilo_to_delete.process_id

    # Eliminamos el hilo de la lista global
    hilos = [h for h in hilos if h.hilo_id != hilo_id]

    # Verificar si ya no quedan más hilos de ese proceso
    if not any(h.process_id == pid for h in hilos):
        # Devolver el color base de ese proceso a la lista de colores disponibles
        if pid in process_base_colors:
            base_color = process_base_colors[pid]
            available_colors.append(base_color)
            del process_base_colors[pid]

    return True

def extract_frame_number(cell_info):
    """
    Extrae el número entero del frame_id (asume "algo-<número>").
    Retorna -1 si no es válido.
    """
    if isinstance(cell_info, dict) and 'frame_id' in cell_info:
        try:
            return int(cell_info['frame_id'].split('-')[-1])
        except (IndexError, ValueError):
            return -1
    return -1

def reduce_hilo_size(hilo_id, amount):
    """
    Reduce 'amount' unidades de tamaño a un hilo específico. 
    Maneja la reasignación de marcos en RAM/ROM (similar a la lógica anterior).
    """
    global hilos
    hilo = next((h for h in hilos if h.hilo_id == hilo_id), None)
    if not hilo:
        return False, f'El hilo "{hilo_id}" no existe.'

    old_size = hilo.size
    new_size = max(0, old_size - amount)
    if new_size == old_size:
        return False, 'No se puede reducir más el tamaño del hilo.'

    hilo.size = new_size

    old_total_frames = int(old_size // FRAME_SIZE) + (1 if old_size % FRAME_SIZE != 0 else 0)
    new_total_frames = int(new_size // FRAME_SIZE) + (1 if new_size % FRAME_SIZE != 0 else 0)
    frames_to_remove = old_total_frames - new_total_frames

    # Si el tamaño se vuelve 0, eliminar hilo completamente
    if hilo.size == 0:
        #delete_hilo_memory(hilo_id)
        return True, f'El hilo "{hilo_id}" ha sido eliminado porque su tamaño es cero.'

    # Si el nuevo total de marcos es menor que 3, no hacemos cambios de RAM->ROM
    if new_total_frames < 3:
        return True, 'El tamaño del hilo se redujo, marcos se mantienen en RAM.'

    # Mover marcos de RAM a ROM
    ram_frames = [f for f in hilo.frames if f['type'] == 'RAM']
    frames_to_move = ram_frames[:frames_to_remove]

    rom_positions = get_free_frames(rom, len(frames_to_move))
    if len(rom_positions) < len(frames_to_move):
        return False, 'No hay suficiente espacio en ROM para alojar marcos liberados de RAM.'

    # Mover efectivamente
    for idx, frame in enumerate(frames_to_move):
        # Liberamos la celda en RAM
        r_i, r_j = frame['i'], frame['j']
        ram[r_i][r_j]['process'] = None
        ram[r_i][r_j]['frame_id'] = None

        # Asignamos en ROM
        rom_i, rom_j = rom_positions[idx]
        rom[rom_i][rom_j]['process'] = hilo
        rom[rom_i][rom_j]['frame_id'] = frame['frame_id']

        frame['type'] = 'ROM'
        frame['i'] = rom_i
        frame['j'] = rom_j

    # Subir un marco de ROM a RAM si frames_to_remove == 1
    if frames_to_remove == 1:
        frames_in_ram = [f for f in hilo.frames if f['type'] == 'RAM']
        frames_in_rom = [f for f in hilo.frames if f['type'] == 'ROM']

        if len(frames_in_ram) < 3 and frames_in_rom:
            # Ordenar por ID de frame para encontrar el “marco más reciente”
            frames_in_rom_sorted = sorted(frames_in_rom, key=lambda f: extract_frame_number(f))

            # IDs en RAM
            ram_frame_ids = [extract_frame_number(f) for f in frames_in_ram]
            max_ram_id = max(ram_frame_ids) if ram_frame_ids else -1

            # Filtramos los marcos de ROM con frame_id mayor a max_ram_id
            eligible_rom_frames = [f for f in frames_in_rom_sorted if extract_frame_number(f) > max_ram_id]
            if eligible_rom_frames:
                frame_to_move_up = eligible_rom_frames[0]
            else:
                # Si no hay marcos con ID mayor, tomamos simplemente el primero
                frame_to_move_up = frames_in_rom_sorted[0]

            free_ram_positions = get_free_frames(ram, 1, start_row=1)
            if not free_ram_positions:
                return False, 'No hay suficiente espacio en RAM para subir un marco desde ROM.'

            new_r_i, new_r_j = free_ram_positions[0]
            # Liberar la posición en ROM
            rom[frame_to_move_up['i']][frame_to_move_up['j']]['process'] = None
            rom[frame_to_move_up['i']][frame_to_move_up['j']]['frame_id'] = None

            # Asignar el marco en RAM
            ram[new_r_i][new_r_j]['process'] = hilo
            ram[new_r_i][new_r_j]['frame_id'] = frame_to_move_up['frame_id']

            # Actualizar la info del frame
            frame_to_move_up['type'] = 'RAM'
            frame_to_move_up['i'] = new_r_i
            frame_to_move_up['j'] = new_r_j

    return True, 'Tamaño del hilo reducido; marcos sobrantes movidos a ROM y uno ascendido a RAM si aplica.'
