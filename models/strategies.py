import threading
import queue
import time

# Función que produce datos y los coloca en la cola
def productor(q):
    for i in range(5):
        item = f"Elemento {i}"
        print(f"Produciendo: {item}")
        q.put(item)
        time.sleep(1)

# Función que consume datos de la cola
def consumidor(q):
    while True:
        item = q.get()
        if item is None:
            break
        print(f"Consumiendo: {item}")
        q.task_done()

# Crear una cola compartida entre los hilos
mi_cola = queue.Queue()

# Crear un hilo para el productor
hilo_productor = threading.Thread(target=productor, args=(mi_cola,))

# Crear un hilo para el consumidor
hilo_consumidor = threading.Thread(target=consumidor, args=(mi_cola,))

# Iniciar los hilos
hilo_productor.start()
hilo_consumidor.start()

# Esperar a que el productor termine
hilo_productor.join()

# Esperar a que el consumidor termine
mi_cola.put(None)  # Enviamos una señal de terminación al consumidor
hilo_consumidor.join()

print("Terminado")
