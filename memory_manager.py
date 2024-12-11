# memory_manager.py

import random

# Constantes
RAM_ROWS, RAM_COLS = 5, 5
ROM_ROWS, ROM_COLS = 5, 10  # Tamaño de la ROM es 5x10
FRAME_SIZE = 2.5
MAX_PROCESS_SIZE = 65

# Lista predeterminada de colores
PREDEFINED_COLORS = ['#5dade2', '#76d7c4', '#e74c3c', '#0e03f5', '#1df503', '#f4d03f','#e90075','#b400e9']
available_colors = PREDEFINED_COLORS.copy()

# Inicializa la matriz de RAM y ROM
ram = []
rom = []

def init_memory():
    global ram, rom, processes, available_colors
    ram = []

    # Primera fila ocupada por el S.O.
    so_row = [{'process': 'S.O.', 'frame_id': 'S.O.-0'} for _ in range(RAM_COLS)]
    ram.append(so_row)

    # Resto de las filas inicializadas como libres
    for _ in range(RAM_ROWS - 1):
        row = [{'process': None, 'frame_id': None} for _ in range(RAM_COLS)]
        ram.append(row)

    # Inicializa la matriz de ROM
    rom = [[{'process': None, 'frame_id': None} for _ in range(ROM_COLS)] for _ in range(ROM_ROWS)]

    # Vaciar la lista de procesos
    processes.clear()

    # Restaurar la lista de colores disponibles
    available_colors = PREDEFINED_COLORS.copy()

# Lista para almacenar los procesos creados
processes = []

class ProcesoMemoria:
    def __init__(self, name, size, color):
        self.name = name
        self.size = size
        self.color = color
        self.frames = []  # Lista de marcos asignados (RAM y ROM)

def create_process_memory(name, size):
    # Verifica si el nombre del proceso ya existe
    if any(p.name == name for p in processes):
        return False, 'Ya existe un proceso con ese nombre en memoria.'

    # Selecciona un color aleatorio de los disponibles y lo remueve de la lista
    color = random.choice(available_colors)
    available_colors.remove(color)

    # Crea una instancia del proceso
    process = ProcesoMemoria(name, size, color)

    total_frames_needed = int(size // FRAME_SIZE)
    if size % FRAME_SIZE != 0:
        total_frames_needed += 1  # Si hay residuo, necesitamos un marco extra

    # Asignamos hasta 3 marcos en RAM
    ram_frames_needed = min(3, total_frames_needed)
    rom_frames_needed = total_frames_needed - ram_frames_needed

    ram_positions = get_free_frames(ram, ram_frames_needed, start_row=1)  # Empezamos desde la fila 1
    rom_positions = get_free_frames(rom, rom_frames_needed)

    if len(ram_positions) < ram_frames_needed or len(rom_positions) < rom_frames_needed:
        return False, 'No hay suficiente espacio en memoria.'

    # Asignamos los marcos a RAM
    for idx, (i, j) in enumerate(ram_positions, start=1):
        frame_id = f"{name}-{idx}"
        ram[i][j]['process'] = process
        ram[i][j]['frame_id'] = frame_id
        process.frames.append({'type': 'RAM', 'i': i, 'j': j, 'frame_id': frame_id})

    # Asignamos los marcos a ROM
    for idx, (i, j) in enumerate(rom_positions, start=ram_frames_needed + 1):
        frame_id = f"{name}-{idx}"
        rom[i][j]['process'] = process
        rom[i][j]['frame_id'] = frame_id
        process.frames.append({'type': 'ROM', 'i': i, 'j': j, 'frame_id': frame_id})

    processes.append(process)
    return True, 'Proceso creado exitosamente.'

def get_free_frames(memory, frames_needed, start_row=0):
    if frames_needed == 0:
        return []
    free_positions = []
    rows = len(memory)
    cols = len(memory[0])

    positions = [(i, j) for i in range(start_row, rows) for j in range(cols)]
    random.shuffle(positions)

    for (i, j) in positions:
        if memory[i][j]['process'] is None:
            free_positions.append((i, j))
            if len(free_positions) == frames_needed:
                break
    return free_positions

def delete_process_memory(name):
    global processes
    process_to_delete = None
    for process in processes:
        if process.name == name:
            process_to_delete = process
            break

    if process_to_delete:
        # Liberamos los marcos en RAM y ROM
        for frame in process_to_delete.frames:
            mem_type = frame['type']
            i = frame['i']
            j = frame['j']
            if mem_type == 'RAM':
                ram[i][j]['process'] = None
                ram[i][j]['frame_id'] = None
            else:
                rom[i][j]['process'] = None
                rom[i][j]['frame_id'] = None

        # Devuelve el color a la lista de colores disponibles
        available_colors.append(process_to_delete.color)

        # Eliminamos el proceso de la lista
        processes = [p for p in processes if p.name != name]
        return True
    else:
        return False

def extract_frame_number(frame):
    """
    Extrae el número del frame_id. Asume que frame_id sigue el formato "ProcesoX-Y",
    donde Y es un número entero.
    """
    if isinstance(frame, dict) and 'frame_id' in frame:
        try:
            return int(frame['frame_id'].split('-')[-1])
        except (IndexError, ValueError):
            return -1  # Valor predeterminado en caso de formato incorrecto
    else:
        return -1  # Valor predeterminado si frame no es dict o no tiene frame_id

def reduce_process_size(name, amount):
    global processes
    process = next((p for p in processes if p.name == name), None)
    if not process:
        return False, f'El proceso "{name}" no existe.'
    
    # Verificar que todos los marcos sean diccionarios
    for frame in process.frames:
        if not isinstance(frame, dict):
            return False, 'Error: Algunos marcos no están correctamente estructurados como diccionarios.'
    
    old_size = process.size
    new_size = max(0, old_size - amount)
    
    if new_size == old_size:
        return False, 'No se puede reducir más el tamaño del proceso.'
    
    # Cálculo de marcos antes y después de la reducción
    old_total_frames = int(old_size // FRAME_SIZE) + (1 if old_size % FRAME_SIZE != 0 else 0)
    new_total_frames = int(new_size // FRAME_SIZE) + (1 if new_size % FRAME_SIZE != 0 else 0)
    frames_to_remove = old_total_frames - new_total_frames
    
    # Actualizamos el tamaño del proceso
    process.size = new_size
    
    # Si el tamaño es cero, eliminamos el proceso por completo
    if process.size == 0:
        delete_process_memory(name)
        return True, f'El proceso "{name}" ha sido eliminado porque su tamaño es cero.'
    
    # Si no se debe remover ningún marco
    if frames_to_remove <= 0:
        return True, 'El tamaño del proceso ha sido reducido, no se liberaron marcos.'
    
    # Paso 1: Mover marcos de RAM a ROM
    ram_frames = [frame for frame in process.frames if frame['type'] == 'RAM']
    frames_to_move = ram_frames[:frames_to_remove]
    
    # Buscamos espacio libre en ROM para colocar estos marcos
    rom_positions = get_free_frames(rom, len(frames_to_move))
    if len(rom_positions) < len(frames_to_move):
        return False, 'No hay suficiente espacio en ROM para bajar las páginas.'
    
    # Movemos los marcos de RAM a ROM
    for idx, frame in enumerate(frames_to_move):
        # Limpiamos la celda en RAM
        ram_i, ram_j = frame['i'], frame['j']
        ram[ram_i][ram_j]['process'] = None
        ram[ram_i][ram_j]['frame_id'] = None
    
        # Asignamos el marco a la ROM
        rom_i, rom_j = rom_positions[idx]
        rom[rom_i][rom_j]['process'] = process
        rom[rom_i][rom_j]['frame_id'] = frame['frame_id']
    
        # Actualizamos la información del marco en el objeto del proceso
        frame['type'] = 'ROM'
        frame['i'] = rom_i
        frame['j'] = rom_j
    
    # Paso 2: Subir un marco desde ROM a RAM solo si frames_to_remove es 1 y new_total_frames > 2
    if frames_to_remove == 1 and new_total_frames > 2:
        # Recalcular las listas después de mover marcos a ROM
        frames_in_ram = [f for f in process.frames if f['type'] == 'RAM']
        frames_in_rom = [f for f in process.frames if f['type'] == 'ROM']
        
        if len(frames_in_ram) < 3 and frames_in_rom:
            # Ordenar los marcos en ROM por frame_id de menor a mayor
            frames_in_rom_sorted = sorted(
                frames_in_rom,
                key=lambda f: extract_frame_number(f)
            )
            
            # Obtener el frame_id máximo en RAM
            ram_frame_ids = [extract_frame_number(f) for f in frames_in_ram]
            max_ram_id = max(ram_frame_ids) if ram_frame_ids else -1
            
            # Filtrar marcos en ROM con frame_id mayor que max_ram_id
            eligible_rom_frames = [
                f for f in frames_in_rom_sorted
                if extract_frame_number(f) > max_ram_id
            ]
            
            # Si hay marcos elegibles, seleccionar el de menor frame_id entre ellos
            if eligible_rom_frames:
                frame_to_move_up = eligible_rom_frames[0]
            else:
                # Si no hay marcos con frame_id mayor, seleccionar el de menor frame_id en ROM
                frame_to_move_up = frames_in_rom_sorted[0]
            
            # Buscar una posición libre en RAM (empezando desde la fila 1 para reservar la primera fila al S.O.)
            free_ram_positions = get_free_frames(ram, 1, start_row=1)
            if len(free_ram_positions) < 1:
                return False, 'No hay suficiente espacio en RAM para subir una página desde ROM.'
            
            ram_i, ram_j = free_ram_positions[0]
            
            # Liberar la posición en ROM
            rom[frame_to_move_up['i']][frame_to_move_up['j']]['process'] = None
            rom[frame_to_move_up['i']][frame_to_move_up['j']]['frame_id'] = None
            
            # Asignar el marco en RAM
            ram[ram_i][ram_j]['process'] = process
            ram[ram_i][ram_j]['frame_id'] = frame_to_move_up['frame_id']
            
            # Actualizar la información del marco en el objeto proceso
            frame_to_move_up['type'] = 'RAM'
            frame_to_move_up['i'] = ram_i
            frame_to_move_up['j'] = ram_j
    
    return True, 'El tamaño del proceso ha sido reducido, las páginas sobrantes han sido bajadas a ROM y un marco ha sido subido a RAM.'
