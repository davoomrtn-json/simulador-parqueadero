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
    contador_vehiculos = 0
    lock_contador = threading.Lock() 

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

   global contador_vehiculos

  hilos_vehiculos = []

for i in range(num_vehiculos):

    with lock_contador:
        contador_vehiculos += 1
        id_vehiculo = f"Vehículo-{contador_vehiculos}"

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


# ==============================================================================
# VENTANA PRINCIPAL
# ==============================================================================
ventana = tk.Tk()

ventana.title(
    "Simulador de Parqueadero"
)

ventana.geometry(
    f"{ventana.winfo_screenwidth()}x{ventana.winfo_screenheight()}+0+0"
)

ventana.minsize(
    650,
    500
)
# ==============================================================================
# FONDO DEL PARQUEADERO
# ==============================================================================
from PIL import Image, ImageTk

imagen_fondo_original = Image.open("fondo_parqueadero.jpg")

etiqueta_fondo = tk.Label(ventana)
etiqueta_fondo.place(
    x=0,
    y=0,
    relwidth=1,
    relheight=1
)


# ==============================================================================

def actualizar_fondo(event=None):

    ancho = ventana.winfo_width()
    alto = ventana.winfo_height()

    if ancho <= 1 or alto <= 1:
        return

    imagen = imagen_fondo_original.copy()

    proporcion_ancho = ancho / imagen.width
    proporcion_alto = alto / imagen.height

    escala = max(
        proporcion_ancho,
        proporcion_alto
    )

    nuevo_ancho = int(imagen.width * escala)
    nuevo_alto = int(imagen.height * escala)

    imagen = imagen.resize(
        (nuevo_ancho, nuevo_alto),
        Image.Resampling.LANCZOS
    )

    izquierda = (nuevo_ancho - ancho) // 2
    arriba = (nuevo_alto - alto) // 2

    imagen = imagen.crop(
        (
            izquierda,
            arriba,
            izquierda + ancho,
            arriba + alto
        )
    )

    imagen_fondo = ImageTk.PhotoImage(imagen)

    etiqueta_fondo.config(
        image=imagen_fondo
    )

    etiqueta_fondo.image = imagen_fondo
ventana.bind("<Configure>", actualizar_fondo)
# ==============================================================================
# FUNCIÓN PARA AGREGAR VEHÍCULO
# ==============================================================================

def agregar_vehiculo():

    global vehiculos_activos

    # ----------------------------------------------------------
    # COMPROBAR SI YA EXISTEN 3 VEHÍCULOS ACTIVOS
    # ----------------------------------------------------------

    with lock_vehiculos_activos:

        if vehiculos_activos >= CAPACIDAD:

            return

        # Registrar inmediatamente el nuevo vehículo.
        vehiculos_activos += 1

        activos_actuales = vehiculos_activos


    # ----------------------------------------------------------
    # CAMBIAR EL BOTÓN INMEDIATAMENTE AL LLEGAR A 3
    # ----------------------------------------------------------

    if activos_actuales >= CAPACIDAD:

        boton_agregar.config(
            text="🚫 NO HAY ESPACIO DE PARQUEO",
            state=tk.DISABLED
        )


    # ----------------------------------------------------------
    # CREAR EL HILO DEL VEHÍCULO
    # ----------------------------------------------------------

    iniciar_simulacion(
        num_vehiculos=1,
        control=control,
        cola_eventos=cola_eventos
    )


# ==============================================================================
# FUNCIÓN PARA ACTUALIZAR LA INTERFAZ
# ==============================================================================

def actualizar_interfaz():


    # ------------------------------------------------------------------
    # LEER LOS EVENTOS
    # ------------------------------------------------------------------

    while True:

        try:

            mensaje = cola_eventos.get_nowait()

            registro.insert(
                tk.END,
                mensaje + "\n"
            )

            registro.see(
                tk.END
            )

        except queue.Empty:

            break


    # ------------------------------------------------------------------
    # ESTADO DEL PARQUEADERO
    # ------------------------------------------------------------------

    ocupados = control.lugares_ocupados

    disponibles = control.espacios_libres()


    # ------------------------------------------------------------------
    # VEHÍCULOS ACTIVOS
    # ------------------------------------------------------------------

    with lock_vehiculos_activos:

        activos = vehiculos_activos


    # ------------------------------------------------------------------
    # CONTROL DEL BOTÓN
    # ------------------------------------------------------------------

    if activos >= CAPACIDAD:

        boton_agregar.config(
            text="🚫 NO HAY ESPACIO DE PARQUEO",
            state=tk.DISABLED
        )

    else:

        boton_agregar.config(
            text="AGREGAR VEHÍCULO",
            state=tk.NORMAL
        )


    # ------------------------------------------------------------------
    # ACTUALIZAR OCUPADOS
    # ------------------------------------------------------------------

    etiqueta_ocupados.config(
        text=f"Ocupados: {ocupados}"
    )


    # ------------------------------------------------------------------
    # ACTUALIZAR DISPONIBLES
    # ------------------------------------------------------------------

    etiqueta_disponibles.config(
        text=f"Disponibles: {disponibles}"
    )


    # ------------------------------------------------------------------
    # ACTUALIZAR BARRA
    # ------------------------------------------------------------------

    barra_progreso["value"] = ocupados


    # ------------------------------------------------------------------
    # ACTUALIZAR PORCENTAJE
    # ------------------------------------------------------------------

    porcentaje = (
        ocupados / CAPACIDAD
    ) * 100

    etiqueta_porcentaje.config(
        text=f"{porcentaje:.0f}% de ocupación"
    )


    # ------------------------------------------------------------------
    # VOLVER A EJECUTAR
    # ------------------------------------------------------------------

    ventana.after(
        100,
        actualizar_interfaz
    )


# ==============================================================================
# FUNCIÓN PARA CERRAR
# ==============================================================================

def cerrar_aplicacion():

    ventana.destroy()


# ==============================================================================
# TÍTULO
# ==============================================================================

titulo = tk.Label(
    ventana,
    text="SIMULADOR DE PARQUEADERO",
    font=("Arial", 24, "bold"),
    fg="white",
    bg="#1f2937",
    padx=20,
    pady=8
)
titulo.pack(
    pady=20
)


subtitulo = tk.Label(
    ventana,
    text="Control y simulación de vehículos con concurrencia",
    font=("Arial", 11)
)

subtitulo.pack(
    pady=5
)


# ==============================================================================
# INFORMACIÓN DEL PARQUEADERO
# ==============================================================================

marco_informacion = tk.Frame(
    ventana
)

marco_informacion.pack(
    pady=20
)


etiqueta_capacidad = tk.Label(
    marco_informacion,
    text=f"Capacidad: {CAPACIDAD}",
    font=("Arial", 14)
)

etiqueta_capacidad.grid(
    row=0,
    column=0,
    padx=25
)


etiqueta_ocupados = tk.Label(
    marco_informacion,
    text="Ocupados: 0",
    font=("Arial", 14)
)

etiqueta_ocupados.grid(
    row=0,
    column=1,
    padx=25
)


etiqueta_disponibles = tk.Label(
    marco_informacion,
    text=f"Disponibles: {CAPACIDAD}",
    font=("Arial", 14)
)

etiqueta_disponibles.grid(
    row=0,
    column=2,
    padx=25
)


# ==============================================================================
# BARRA DE PROGRESO
# ==============================================================================

etiqueta_titulo_barra = tk.Label(
    ventana,
    text="Ocupación del parqueadero",
    font=("Arial", 12, "bold")
)

etiqueta_titulo_barra.pack(
    pady=(10, 5)
)


barra_progreso = ttk.Progressbar(
    ventana,
    orient="horizontal",
    length=500,
    mode="determinate",
    maximum=CAPACIDAD
)

barra_progreso.pack(
    pady=5
)


etiqueta_porcentaje = tk.Label(
    ventana,
    text="0% de ocupación",
    font=("Arial", 11)
)

etiqueta_porcentaje.pack(
    pady=5
)


# ==============================================================================
# BOTÓN AGREGAR VEHÍCULO
# ==============================================================================

boton_agregar = tk.Button(
    ventana,
    text="AGREGAR VEHÍCULO",
    command=agregar_vehiculo,
    font=("Arial", 12, "bold"),
    padx=20,
    pady=10
)

boton_agregar.pack(
    pady=20
)


# ==============================================================================
# REGISTRO DE EVENTOS
# ==============================================================================

etiqueta_eventos = tk.Label(
    ventana,
    text="REGISTRO DE EVENTOS",
    font=("Arial", 13, "bold")
)

etiqueta_eventos.pack(
    pady=(10, 5)
)


marco_registro = tk.Frame(
    ventana,
    height=180
)

marco_registro.pack(
    fill="x",
    padx=30,
    pady=10
)

marco_registro.pack_propagate(False)

barra_desplazamiento = tk.Scrollbar(
    marco_registro
)

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


# ==============================================================================
# BOTÓN CERRAR
# ==============================================================================

boton_cerrar = tk.Button(
    ventana,
    text="CERRAR",
    command=cerrar_aplicacion,
    font=("Arial", 10),
    padx=15,
    pady=5
)

boton_cerrar.pack(
    pady=10
)


# ==============================================================================
# INICIAR ACTUALIZACIÓN
# ==============================================================================

ventana.after(
    100,
    actualizar_interfaz
)


# ==============================================================================
# EJECUTAR APLICACIÓN
# ==============================================================================

ventana.mainloop()
