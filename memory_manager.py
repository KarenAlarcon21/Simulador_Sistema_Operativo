# memory_manager.py

import random

# Constantes
RAM_ROWS, RAM_COLS = 5, 5
ROM_ROWS, ROM_COLS = 5, 10  # Tamaño de la ROM es 5x10
FRAME_SIZE = 2.5
MAX_PROCESS_SIZE = 65

# Lista predeterminada de colores
PREDEFINED_COLORS = ['#5dade2', '#76d7c4', '#e74c3c', '#0e03f5', '#1df503', '#f4d03f']
available_colors = PREDEFINED_COLORS.copy()

# Inicializa la matriz de RAM y ROM
ram = []
rom = []

def init_memory():
    global ram, rom, processes, available_colors
    ram = []

    # Primera fila ocupada por el S.O.
    so_row = [{'process': 'S.O.'} for _ in range(RAM_COLS)]
    ram.append(so_row)

    # Resto de las filas inicializadas como libres
    for _ in range(RAM_ROWS - 1):
        row = [{'process': None} for _ in range(RAM_COLS)]
        ram.append(row)

    # Inicializa la matriz de ROM
    rom = [[{'process': None} for _ in range(ROM_COLS)] for _ in range(ROM_ROWS)]

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

    # Asignamos los marcos al proceso y registramos las posiciones con identificador de marco
    frame_number = 1  # Iniciamos la numeración de marcos desde 1

    for (i, j) in ram_positions:
        frame_id = f"{name}-{frame_number}"  # Creamos el identificador de marco
        ram[i][j]['process'] = process
        ram[i][j]['frame_id'] = frame_id  # Asignamos el identificador de marco a la celda
        process.frames.append({'type': 'RAM', 'i': i, 'j': j, 'frame_id': frame_id})
        frame_number += 1

    for (i, j) in rom_positions:
        frame_id = f"{name}-{frame_number}"  # Creamos el identificador de marco
        rom[i][j]['process'] = process
        rom[i][j]['frame_id'] = frame_id  # Asignamos el identificador de marco a la celda
        process.frames.append({'type': 'ROM', 'i': i, 'j': j, 'frame_id': frame_id})
        frame_number += 1

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

def reduce_process_size(name, amount):
    global processes
    process = next((p for p in processes if p.name == name), None)
    if not process:
        return False, f'El proceso {name} no existe.'

    # Reducimos el tamaño del proceso
    new_size = max(0, process.size - amount)
    if new_size == process.size:
        return False, 'No se puede reducir más el tamaño del proceso.'

    old_total_frames = int(process.size // FRAME_SIZE)
    if process.size % FRAME_SIZE != 0:
        old_total_frames += 1

    process.size = new_size

    if process.size == 0:
        # Si el tamaño es cero, eliminamos el proceso
        delete_process_memory(name)
        return True, f'El proceso {name} ha sido eliminado porque su tamaño es cero.'

    new_total_frames = int(process.size // FRAME_SIZE)
    if process.size % FRAME_SIZE != 0 and process.size % FRAME_SIZE != 0.0:
        new_total_frames += 1

    frames_to_remove = int(old_total_frames - new_total_frames)

    if frames_to_remove <= 0:
        return True, 'El tamaño del proceso ha sido reducido, no se liberaron marcos.'

    # Liberamos marcos en RAM primero
    ram_frames = [frame for frame in process.frames if frame['type'] == 'RAM']
    rom_frames = [frame for frame in process.frames if frame['type'] == 'ROM']

    frames_removed = 0
    frames_to_delete = []

    # Liberamos marcos en RAM
    for frame in ram_frames:
        if frames_removed < frames_to_remove:
            i, j = frame['i'], frame['j']
            ram[i][j]['process'] = None
            ram[i][j]['frame_id'] = None
            frames_to_delete.append(frame)
            frames_removed += 1
        else:
            break

    # Si aún necesitamos liberar más marcos, liberamos en ROM
    if frames_removed < frames_to_remove:
        for frame in rom_frames:
            if frames_removed < frames_to_remove:
                i, j = frame['i'], frame['j']
                rom[i][j]['process'] = None
                rom[i][j]['frame_id'] = None
                frames_to_delete.append(frame)
                frames_removed += 1
            else:
                break

    # Eliminamos los marcos liberados de la lista de marcos del proceso
    process.frames = [frame for frame in process.frames if frame not in frames_to_delete]

    # Contamos cuántos marcos en RAM tiene el proceso actualmente
    current_ram_frames = len([frame for frame in process.frames if frame['type'] == 'RAM'])

    # Si el proceso tiene menos de 3 marcos en RAM, intentamos mover marcos de ROM a RAM
    max_ram_frames = 3
    frames_needed_in_ram = max_ram_frames - current_ram_frames

    if frames_needed_in_ram > 0:
        # Obtenemos posiciones libres en RAM
        free_ram_positions = get_free_frames(ram, frames_needed_in_ram, start_row=1)
        # Obtenemos marcos en ROM que podemos mover
        rom_frames_to_move = [frame for frame in process.frames if frame['type'] == 'ROM'][:len(free_ram_positions)]

        for idx, frame in enumerate(rom_frames_to_move):
            # Obtenemos una posición libre en RAM
            ram_i, ram_j = free_ram_positions[idx]
            # Posición actual en ROM
            rom_i, rom_j = frame['i'], frame['j']

            # Movemos el marco de ROM a RAM
            ram[ram_i][ram_j]['process'] = process
            ram[ram_i][ram_j]['frame_id'] = frame['frame_id']
            rom[rom_i][rom_j]['process'] = None
            rom[rom_i][rom_j]['frame_id'] = None

            # Actualizamos las posiciones en la lista de marcos del proceso
            frame['type'] = 'RAM'
            frame['i'] = ram_i
            frame['j'] = ram_j

    return True, 'El tamaño del proceso ha sido reducido y los marcos han sido actualizados.'
