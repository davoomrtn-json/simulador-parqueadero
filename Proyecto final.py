
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
Este archivo se encarga de que el parqueadero nunca se sobrecupe, aunque varios 
vehículos intenten entrar o salir exactamente al mismo tiempo. Para lograrlo usa 
dos herramientas típicas de un sistema operativo: - Un semáforo, que lleva la 
cuenta de cuántos cupos quedan libres. - Un lock (un candado), que protege el 
número de vehículos parqueados para que dos hilos no lo modifiquen a la vez y lo 
dejen mal. La idea es la misma que usa un sistema operativo para repartir recursos 
entre procesos: cada vehículo es como un proceso que necesita un recurso
 (el espacio de parqueo), y si no hay disponible, se queda esperando su turno en vez
 de entrar de todas formas.
================================================================================
"""
import threading
import time
import random
import queue
import tkinter as tk
from tkinter import ttk


# ==============================================================================
# CONTROL DEL PARQUEADERO
# ==============================================================================

class ControlParqueadero:
    """
    Se encarga de todo el control de acceso al parqueadero: dejar entrar
    o no a un vehículo, llevar la cuenta de cuántos hay adentro y avisar
    cuando alguien sale.
    """

    def __init__(self, capacidad: int, avisar=None):

        if capacidad <= 0:
            raise ValueError(
                "La capacidad debe ser un número mayor a 0."
            )

        self.capacidad = capacidad

        # Semáforo que controla los cupos disponibles.
        self.semaforo = threading.Semaphore(capacidad)

        # Lock para proteger el número de vehículos parqueados.
        self.lock = threading.Lock()

        # Número de espacios ocupados actualmente.
        self.lugares_ocupados = 0

        self.avisar = avisar if avisar else print

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def hay_espacio_libre(self) -> bool:

        with self.lock:

            return self.lugares_ocupados < self.capacidad

    def espacios_libres(self) -> int:

        with self.lock:

            return self.capacidad - self.lugares_ocupados

    # ------------------------------------------------------------------
    # Sección crítica
    # ------------------------------------------------------------------

    def _sumar_un_lugar_ocupado(self, vehiculo_id):

        with self.lock:

            self.lugares_ocupados += 1

            self.avisar(
                f"[{vehiculo_id}] entró. Lugares ocupados: "
                f"{self.lugares_ocupados}/{self.capacidad}"
            )

    def _restar_un_lugar_ocupado(self, vehiculo_id):

        with self.lock:

            self.lugares_ocupados -= 1

            self.avisar(
                f"[{vehiculo_id}] salió. Lugares ocupados: "
                f"{self.lugares_ocupados}/{self.capacidad}"
            )

    # ------------------------------------------------------------------
    # Entrar y salir
    # ------------------------------------------------------------------

    def entrar(
        self,
        vehiculo_id,
        tiempo_maximo_espera=None
    ) -> bool:

        self.avisar(
            f"[{vehiculo_id}] esperando espacio..."
        )

        consiguio_cupo = self.semaforo.acquire(
            timeout=tiempo_maximo_espera
        )

        if consiguio_cupo:

            self._sumar_un_lugar_ocupado(
                vehiculo_id
            )

            return True

        else:

            self.avisar(
                f"[{vehiculo_id}] se rindió esperando "
                f"(no hubo cupo a tiempo)."
            )

            return False

    def salir(self, vehiculo_id):

        self._restar_un_lugar_ocupado(
            vehiculo_id
        )

        self.semaforo.release()


# ==============================================================================
# PRUEBA POR CONSOLA
# ==============================================================================

def _vehiculo_de_prueba(
    control: ControlParqueadero,
    vehiculo_id: str
):

    time.sleep(
        random.uniform(0.1, 1.5)
    )

    if control.entrar(
        vehiculo_id,
        tiempo_maximo_espera=5
    ):

        time.sleep(
            random.uniform(0.5, 2.0)
        )

        control.salir(
            vehiculo_id
        )


# ==============================================================================
# VARIABLES DE LA SIMULACIÓN
# ==============================================================================

cola_eventos = queue.Queue()

CAPACIDAD = 3

control = ControlParqueadero(
    capacidad=CAPACIDAD,
    avisar=cola_eventos.put
)


# ==============================================================================
# CONTROL DE VEHÍCULOS ACTIVOS
# ==============================================================================

# Esta variable cuenta los vehículos que ya fueron agregados
# aunque todavía estén esperando para llegar al parqueadero.

vehiculos_activos = 0

# Lock para proteger la variable anterior.

lock_vehiculos_activos = threading.Lock()


# ==============================================================================
# SIMULACIÓN DE VEHÍCULOS
# ==============================================================================

def vehiculo(
    id_vehiculo: str,
    control,
    cola_eventos: queue.Queue
):

    global vehiculos_activos

    try:

        # Tiempo aleatorio antes de llegar.
        tiempo_llegada = random.uniform(
            0.5,
            3.0
        )

        time.sleep(
            tiempo_llegada
        )

        # Avisar que llegó.
        cola_eventos.put(
            f"[{id_vehiculo}] Llegó al parqueadero y solicita ingreso."
        )

        # Intentar ingresar.
        ingreso_exitoso = control.entrar(
            id_vehiculo,
            tiempo_maximo_espera=10
        )

        if ingreso_exitoso:

            # Tiempo que permanece estacionado.
            tiempo_parqueo = random.uniform(
                2.0,
                6.0
            )

            cola_eventos.put(
                f"[{id_vehiculo}] Ingresó. "
                f"Tiempo de parqueo: {tiempo_parqueo:.1f}s."
            )

            time.sleep(
                tiempo_parqueo
            )

            # Liberar el espacio.
            control.salir(
                id_vehiculo
            )

            cola_eventos.put(
                f"[{id_vehiculo}] Liberó el espacio "
                f"y salió del parqueadero."
            )

        else:

            cola_eventos.put(
                f"[{id_vehiculo}] Se cansó de esperar "
                f"y se fue (timeout)."
            )

    finally:

        # Cuando el vehículo termina completamente su ciclo,
        # deja de contarse como vehículo activo.

        with lock_vehiculos_activos:

            vehiculos_activos -= 1


# ==============================================================================
# INICIAR SIMULACIÓN
# ==============================================================================

def iniciar_simulacion(
    num_vehiculos: int,
    control,
    cola_eventos: queue.Queue
):

    hilos_vehiculos = []

    for i in range(num_vehiculos):

        id_vehiculo = f"Vehículo-{i+1}"

        hilo = threading.Thread(
            target=vehiculo,
            args=(
                id_vehiculo,
                control,
                cola_eventos
            ),
            daemon=True
        )

        hilos_vehiculos.append(
            hilo
        )

    for hilo in hilos_vehiculos:

        hilo.start()

    return hilos_vehiculos
