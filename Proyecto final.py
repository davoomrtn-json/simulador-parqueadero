"""
================================================================================
 PROYECTO FINAL - SIMULADOR DE PARQUEADERO INTELIGENTE CON HILOS E INTERFAZ
 GRAFICA DE USUARIO EN PYTHON
 Universidad EAN - Facultad de Ingeniería
 Materia: Arquitectura de Computadores y Sistemas Operativos
 Profesora: Diana Carolina Beltrán Peña
 Año: 2026

 Autores:
   - Stefany Mora Rodríguez
   - Eliseo Jiménez Arias
   - Johan David Pinto Martín

 --------------------------------------------------------------------------
 Control de Parqueadero y Sincronización
 --------------------------------------------------------------------------
 Este archivo se encarga de que el parqueadero nunca se sobrecupe, aunque
 varios vehículos intenten entrar o salir exactamente al mismo tiempo.
 Para lograrlo usa dos herramientas típicas de un sistema operativo:

   - Un semáforo, que lleva la cuenta de cuántos cupos quedan libres.
   - Un lock (un candado), que protege el número de vehículos parqueados
     para que dos hilos no lo modifiquen a la vez y lo dejen mal.

 La idea es la misma que usa un sistema operativo para repartir recursos
 entre procesos: cada vehículo es como un proceso que necesita un recurso
 (el espacio de parqueo), y si no hay disponible, se queda esperando su
 turno en vez de entrar de todas formas.
================================================================================
"""

import threading
import time
import random
import queue

class ControlParqueadero:
    """
    Se encarga de todo el control de acceso al parqueadero: dejar entrar
    o no a un vehículo, llevar la cuenta de cuántos hay adentro y avisar
    cuando alguien sale.

    Tanto el hilo de cada vehículo como la interfaz gráfica deberían usar
    solo esta clase para interactuar con el parqueadero, en vez de crear
    sus propios semáforos o locks por su cuenta.
    """

    def __init__(self, capacidad: int, avisar=None):
        """
        capacidad: número de espacios que tiene el parqueadero.
        avisar: función para mandar mensajes hacia afuera (por ejemplo,
                a la cola que después lee la interfaz). Si no se pasa
                nada, se usa print, así que esta clase también se puede
                probar sola desde la consola.
        """
        if capacidad <= 0:
            raise ValueError("La capacidad debe ser un número mayor a 0.")

        self.capacidad = capacidad

        # El semáforo empieza con "capacidad" cupos disponibles. Cada
        # entrar() se lleva uno, cada salir() lo devuelve.
        self.semaforo = threading.Semaphore(capacidad)

        # Necesitamos el lock aparte del semáforo porque sumar o restar
        # un número no es una operación de un solo paso para Python:
        # primero se lee el valor, luego se cambia y luego se guarda.
        # Si dos vehículos hacen esto exactamente al mismo tiempo, el
        # conteo se puede desordenar. El lock evita eso.
        self.lock = threading.Lock()

        # Cuántos espacios están ocupados en este momento.
        self.lugares_ocupados = 0

        self.avisar = avisar if avisar else print

    # ------------------------------------------------------------------
    # Consultas: solo miran el estado, no lo cambian
    # ------------------------------------------------------------------
    def hay_espacio_libre(self) -> bool:
        """True si en este momento queda al menos un espacio libre."""
        with self.lock:
            return self.lugares_ocupados < self.capacidad

    def espacios_libres(self) -> int:
        """Cuántos espacios libres hay en este momento."""
        with self.lock:
            return self.capacidad - self.lugares_ocupados

    # ------------------------------------------------------------------
    # Estas dos funciones son la sección crítica: aquí se toca el número
    # compartido, así que siempre va dentro de un "with self.lock".
    # ------------------------------------------------------------------
    def _sumar_un_lugar_ocupado(self, vehiculo_id):
        with self.lock:
            self.lugares_ocupados += 1
            self.avisar(f"[{vehiculo_id}] entró. Lugares ocupados: {self.lugares_ocupados}/{self.capacidad}")

    def _restar_un_lugar_ocupado(self, vehiculo_id):
        with self.lock:
            self.lugares_ocupados -= 1
            self.avisar(f"[{vehiculo_id}] salió. Lugares ocupados: {self.lugares_ocupados}/{self.capacidad}")

    # ------------------------------------------------------------------
    # Entrar y salir del parqueadero: esto es lo que usa cada vehículo
    # ------------------------------------------------------------------
    def entrar(self, vehiculo_id, tiempo_maximo_espera=None) -> bool:
        """
        Intenta conseguir un cupo para vehiculo_id.

        Si hay cupo, lo toma y devuelve True. Si no hay, el vehículo se
        queda esperando ahí mismo (bloqueado) hasta que otro salga y
        libere un espacio, o hasta que se cumpla tiempo_maximo_espera
        (si se lo damos) y entonces se rinde.
        """
        self.avisar(f"[{vehiculo_id}] esperando espacio...")

        consiguio_cupo = self.semaforo.acquire(timeout=tiempo_maximo_espera)

        if consiguio_cupo:
            self._sumar_un_lugar_ocupado(vehiculo_id)
            return True
        else:
            self.avisar(f"[{vehiculo_id}] se rindió esperando (no hubo cupo a tiempo).")
            return False

    def salir(self, vehiculo_id):
        """
        Libera el espacio de vehiculo_id: resta uno al contador y le
        devuelve el cupo al semáforo para que otro vehículo pueda entrar.

        Ojo: esto solo se debe llamar una vez por cada entrar() exitoso,
        si no el conteo se descuadra.
        """
        self._restar_un_lugar_ocupado(vehiculo_id)
        self.semaforo.release()


# ==============================================================================
# Prueba por consola, sin necesidad de la interfaz gráfica.
# Si esto corre sin errores y el número de lugares ocupados nunca se pasa
# de la capacidad ni queda mal al final, es señal de que la sincronización
# está funcionando bien.
# ==============================================================================
def _vehiculo_de_prueba(control: ControlParqueadero, vehiculo_id: str):
    # Espera un rato antes de intentar entrar, para que no lleguen todos
    # exactamente al mismo tiempo.
    time.sleep(random.uniform(0.1, 1.5))

    if control.entrar(vehiculo_id, tiempo_maximo_espera=5):
        time.sleep(random.uniform(0.5, 2.0))  # tiempo parqueado
        control.salir(vehiculo_id)


#if __name__ == "__main__":
  #  random.seed(42)  # deja el mismo orden de vehículos cada vez que se corre

#    CAPACIDAD = 3
 #   NUM_VEHICULOS = 8

 #   control = ControlParqueadero(capacidad=CAPACIDAD)

  #  hilos = [
   #     threading.Thread(target=_vehiculo_de_prueba, args=(control, f"Vehiculo-{i+1}"))
    #    for i in range(NUM_VEHICULOS)
    #]

    #print(f"--- Prueba por consola: {NUM_VEHICULOS} vehículos, {CAPACIDAD} cupos ---")
    #for h in hilos:
     #   h.start()
    #for h in hilos:
     #   h.join()

    #print("--- Prueba terminada. Lugares ocupados al final:", control.lugares_ocupados, "---")
 # ==============================================================================
# Simulación de Vehículos y Eventos
# ==============================================================================
# Este bloque contiene la lógica individual de cada vehículo actuando como un 
# proceso independiente en el sistema, y la generación de sus respectivos hilos.
# ==============================================================================

# Crear la función vehiculo(id)[cite: 10].
def vehiculo(id_vehiculo: str, control, cola_eventos: queue.Queue):
    """
    Representa el ciclo de vida de un vehículo. Interactúa con el ControlParqueadero
    para solicitar acceso, parquear y salir.
    """
    # Generar tiempos aleatorios de llegada[cite: 10].
    tiempo_llegada = random.uniform(0.5, 3.0)
    time.sleep(tiempo_llegada)
    
    # Enviar eventos a la Queue[cite: 10].
    cola_eventos.put(f"[{id_vehiculo}] Llegó al parqueadero y solicita ingreso.")
    
    # Intentar ingreso al parqueadero[cite: 10].
    # El hilo se bloqueará aquí si el semáforo no tiene cupos disponibles.
    ingreso_exitoso = control.entrar(id_vehiculo, tiempo_maximo_espera=10)
    
    if ingreso_exitoso:
        # Simular tiempo de parqueo[cite: 10].
        tiempo_parqueo = random.uniform(2.0, 6.0)
        cola_eventos.put(f"[{id_vehiculo}] Ingresó. Tiempo de parqueo: {tiempo_parqueo:.1f}s.")
        time.sleep(tiempo_parqueo)
        
        # Gestionar la salida[cite: 10].
        control.salir(id_vehiculo)
        # Enviar eventos a la Queue[cite: 10].
        cola_eventos.put(f"[{id_vehiculo}] Liberó el espacio y salió del parqueadero.")
    else:
        cola_eventos.put(f"[{id_vehiculo}] Se cansó de esperar y se fue (timeout).")

def iniciar_simulacion(num_vehiculos: int, control, cola_eventos: queue.Queue):
    """
    Se encarga de inicializar la concurrencia creando y arrancando los hilos.
    """
    hilos_vehiculos = []
    
    # Crear hilos para cada vehículo[cite: 10].
    for i in range(num_vehiculos):
        id_vehiculo = f"Vehículo-{i+1}"
        hilo = threading.Thread(
            target=vehiculo, 
            args=(id_vehiculo, control, cola_eventos),
            daemon=True # Permite que el programa termine aunque queden hilos en espera
        )
        hilos_vehiculos.append(hilo)
        
    for hilo in hilos_vehiculos:
        hilo.start()
        
    return hilos_vehiculos
# ==============================================================================
# INTERFAZ GRÁFICA - GUI
# ==============================================================================

import tkinter as tk
from tkinter import ttk
import queue


# Cola que recibe los eventos de los vehículos
cola_eventos = queue.Queue()

# Capacidad del parqueadero
CAPACIDAD = 3

# Crear el controlador del parqueadero.
# Los mensajes del controlador también se envían a la cola.
control = ControlParqueadero(
    capacidad=CAPACIDAD,
    avisar=cola_eventos.put
)


# ------------------------------------------------------------------------------
# FUNCIONES DE LA INTERFAZ
# ------------------------------------------------------------------------------

def agregar_vehiculo():
    """
    Crea un nuevo vehículo y lo agrega a la simulación.
    """
    iniciar_simulacion(
        num_vehiculos=1,
        control=control,
        cola_eventos=cola_eventos
    )


def actualizar_interfaz():
    """
    Revisa la cola de eventos y actualiza la interfaz.
    Esta función se ejecuta cada 100 milisegundos.
    """

    # Leer todos los mensajes disponibles en la cola
    while True:
        try:
            mensaje = cola_eventos.get_nowait()

            # Mostrar el mensaje en el registro
            registro.insert(tk.END, mensaje + "\n")
            registro.see(tk.END)

        except queue.Empty:
            break

    # Actualizar contador de ocupados
    ocupados = control.lugares_ocupados

    # Actualizar contador de disponibles
    disponibles = control.espacios_libres()

    etiqueta_ocupados.config(text=f"Ocupados: {ocupados}")
    etiqueta_disponibles.config(text=f"Disponibles: {disponibles}")

    # Actualizar barra de progreso
    barra_progreso["value"] = ocupados

    # Actualizar porcentaje
    porcentaje = (ocupados / CAPACIDAD) * 100
    etiqueta_porcentaje.config(text=f"{porcentaje:.0f}% de ocupación")

    # Volver a revisar la cola dentro de 100 milisegundos
    ventana.after(100, actualizar_interfaz)


def cerrar_aplicacion():
    """
    Cierra la aplicación.
    """
    ventana.destroy()


# ------------------------------------------------------------------------------
# VENTANA PRINCIPAL
# ------------------------------------------------------------------------------

ventana = tk.Tk()

ventana.title("Simulador de Parqueadero")
ventana.geometry("750x600")
ventana.minsize(650, 500)


# ------------------------------------------------------------------------------
# TÍTULO
# ------------------------------------------------------------------------------

titulo = tk.Label(
    ventana,
    text="SIMULADOR DE PARQUEADERO",
    font=("Arial", 22, "bold")
)

titulo.pack(pady=20)


subtitulo = tk.Label(
    ventana,
    text="Control y simulación de vehículos con concurrencia",
    font=("Arial", 11)
)

subtitulo.pack(pady=5)


# ------------------------------------------------------------------------------
# INFORMACIÓN DEL PARQUEADERO
# ------------------------------------------------------------------------------

marco_informacion = tk.Frame(ventana)

marco_informacion.pack(pady=20)


etiqueta_capacidad = tk.Label(
    marco_informacion,
    text=f"Capacidad: {CAPACIDAD}",
    font=("Arial", 14)
)

etiqueta_capacidad.grid(row=0, column=0, padx=25)


etiqueta_ocupados = tk.Label(
    marco_informacion,
    text="Ocupados: 0",
    font=("Arial", 14)
)

etiqueta_ocupados.grid(row=0, column=1, padx=25)


etiqueta_disponibles = tk.Label(
    marco_informacion,
    text=f"Disponibles: {CAPACIDAD}",
    font=("Arial", 14)
)

etiqueta_disponibles.grid(row=0, column=2, padx=25)


# ------------------------------------------------------------------------------
# BARRA DE PROGRESO
# ------------------------------------------------------------------------------

etiqueta_titulo_barra = tk.Label(
    ventana,
    text="Ocupación del parqueadero",
    font=("Arial", 12, "bold")
)

etiqueta_titulo_barra.pack(pady=(10, 5))


barra_progreso = ttk.Progressbar(
    ventana,
    orient="horizontal",
    length=500,
    mode="determinate",
    maximum=CAPACIDAD
)

barra_progreso.pack(pady=5)


etiqueta_porcentaje = tk.Label(
    ventana,
    text="0% de ocupación",
    font=("Arial", 11)
)

etiqueta_porcentaje.pack(pady=5)


# ------------------------------------------------------------------------------
# BOTÓN AGREGAR VEHÍCULO
# ------------------------------------------------------------------------------

boton_agregar = tk.Button(
    ventana,
    text="AGREGAR VEHÍCULO",
    command=agregar_vehiculo,
    font=("Arial", 12, "bold"),
    padx=20,
    pady=10
)

boton_agregar.pack(pady=20)


# ------------------------------------------------------------------------------
# REGISTRO DE EVENTOS
# ------------------------------------------------------------------------------

etiqueta_eventos = tk.Label(
    ventana,
    text="REGISTRO DE EVENTOS",
    font=("Arial", 13, "bold")
)

etiqueta_eventos.pack(pady=(10, 5))


marco_registro = tk.Frame(ventana)

marco_registro.pack(
    fill="both",
    expand=True,
    padx=30,
    pady=5
)


barra_desplazamiento = tk.Scrollbar(marco_registro)

barra_desplazamiento.pack(
    side="right",
    fill="y"
)


registro = tk.Text(
    marco_registro,
    height=10,
    width=80,
    yscrollcommand=barra_desplazamiento.set
)

registro.pack(
    side="left",
    fill="both",
    expand=True
)


barra_desplazamiento.config(
    command=registro.yview
)


# ------------------------------------------------------------------------------
# BOTÓN CERRAR
# ------------------------------------------------------------------------------

boton_cerrar = tk.Button(
    ventana,
    text="CERRAR",
    command=cerrar_aplicacion,
    font=("Arial", 10),
    padx=15,
    pady=5
)

boton_cerrar.pack(pady=10)


# ------------------------------------------------------------------------------
# INICIAR ACTUALIZACIÓN DE LA INTERFAZ
# ------------------------------------------------------------------------------

ventana.after(100, actualizar_interfaz)


# ------------------------------------------------------------------------------
# INICIAR APLICACIÓN
# ------------------------------------------------------------------------------

ventana.mainloop()