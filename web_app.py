
from flask import Flask, jsonify, render_template_string
import threading
import time
import random
from collections import deque
from datetime import datetime

app = Flask(__name__)

# ============================================================
# CONFIGURACIÓN DEL PARQUEADERO
# ============================================================

CAPACIDAD = 3

semaforo = threading.Semaphore(CAPACIDAD)
lock_parqueadero = threading.Lock()
lock_eventos = threading.Lock()
lock_contador = threading.Lock()

lugares_ocupados = []
eventos = deque(maxlen=40)

contador_vehiculos = 0
vehiculos_activos = 0


# ============================================================
# REGISTRO DE EVENTOS
# ============================================================

def registrar_evento(mensaje):
    hora = datetime.now().strftime("%H:%M:%S")

    with lock_eventos:
        eventos.appendleft({
            "hora": hora,
            "mensaje": mensaje
        })


# ============================================================
# CONTROL DEL PARQUEADERO
# ============================================================

class ControlParqueadero:

    def __init__(self, capacidad):
        self.capacidad = capacidad
        self.semaforo = threading.Semaphore(capacidad)
        self.lock = threading.Lock()
        self.ocupados = []

    def entrar(self, id_vehiculo, timeout=10):
        disponible = self.semaforo.acquire(timeout=timeout)

        if not disponible:
            return False

        with self.lock:
            self.ocupados.append(id_vehiculo)

        registrar_evento(
            f"{id_vehiculo} ingresó al parqueadero."
        )
        return True

    def salir(self, id_vehiculo):
        with self.lock:
            if id_vehiculo not in self.ocupados:
                return

            self.ocupados.remove(id_vehiculo)

        self.semaforo.release()

        registrar_evento(
            f"{id_vehiculo} salió del parqueadero. Cupo liberado."
        )

    def obtener_estado(self):
        with self.lock:
            ocupados = list(self.ocupados)

        return {
            "ocupados": ocupados,
            "cantidad_ocupados": len(ocupados),
            "libres": self.capacidad - len(ocupados)
        }


control = ControlParqueadero(CAPACIDAD)


# ============================================================
# SIMULACIÓN DE VEHÍCULOS CON HILOS
# ============================================================

def vehiculo(id_vehiculo):
    global vehiculos_activos

    try:
        registrar_evento(
            f"{id_vehiculo} se dirige a la entrada."
        )

        # Simula el tiempo de llegada del vehículo
        time.sleep(random.uniform(0.5, 2))

        ingreso = control.entrar(id_vehiculo, timeout=10)

        if not ingreso:
            registrar_evento(
                f"{id_vehiculo} no encontró cupo disponible."
            )
            return

        registrar_evento(
            f"{id_vehiculo} está estacionado."
        )

        # Tiempo simulado de permanencia
        time.sleep(random.uniform(5, 10))

    except Exception as error:
        registrar_evento(
            f"Error en {id_vehiculo}: {error}"
        )

    finally:
        # Si ingresó, libera su espacio al terminar
        estado = control.obtener_estado()

        if id_vehiculo in estado["ocupados"]:
            control.salir(id_vehiculo)

        with lock_contador:
            vehiculos_activos -= 1



def agregar_vehiculo():
    global contador_vehiculos, vehiculos_activos

    with lock_contador:
        if vehiculos_activos >= 12:
            return False, (
                "Hay demasiados vehículos en proceso. "
                "Intenta nuevamente."
            )

        contador_vehiculos += 1
        id_vehiculo = f"Vehículo-{contador_vehiculos}"
        vehiculos_activos += 1

    hilo = threading.Thread(
        target=vehiculo,
        args=(id_vehiculo,),
        daemon=True
    )
    hilo.start()

    registrar_evento(
        f"{id_vehiculo} fue agregado a la simulación."
    )

    return True, f"{id_vehiculo} agregado correctamente."


# ============================================================
# INTERFAZ WEB
# ============================================================

PAGINA = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Simulador de Parqueadero Inteligente</title>

<style>
* {
    box-sizing: border-box;
}

:root {
    --verde: #38ef9d;
    --verde-oscuro: #0b9b68;
    --rojo: #ff626c;
    --amarillo: #ffd166;
    --blanco: #ffffff;
    --panel: rgba(12, 20, 31, 0.84);
    --borde: rgba(255, 255, 255, 0.18);
}

body {
    margin: 0;
    min-height: 100vh;
    height: 100vh;
    overflow: hidden;

    font-family: "Segoe UI", Arial, sans-serif;
    color: var(--blanco);

    background:
        linear-gradient(
            135deg,
            rgba(5, 12, 22, 0.75),
            rgba(4, 17, 25, 0.62)
        ),
        url("/static/fondo_parqueadero.jpg")
        center center / cover fixed;

    background-color: #101923;
}

.contenedor {
    width: min(1500px, 96%);
    margin: 0 auto;
    padding: 24px 0 35px;
}

.encabezado {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 18px;
    padding: 23px 28px;
    margin-bottom: 22px;

    background: rgba(8, 16, 26, 0.84);
    border: 1px solid var(--borde);
    border-radius: 20px;
    backdrop-filter: blur(12px);
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.25);
}

.marca {
    display: flex;
    align-items: center;
    gap: 16px;
}

.icono-principal {
    width: 64px;
    height: 64px;
    display: grid;
    place-items: center;
    border-radius: 17px;
    font-size: 34px;
    background: rgba(56, 239, 157, 0.15);
    border: 1px solid rgba(56, 239, 157, 0.45);
}

h1 {
    margin: 0;
    font-size: clamp(22px, 3vw, 34px);
    line-height: 1.2;
}

.subtitulo {
    margin: 8px 0 0;
    color: #d0dae4;
    font-size: 14px;
}

.estado-sistema {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 11px 16px;
    border: 1px solid rgba(56, 239, 157, 0.35);
    background: rgba(56, 239, 157, 0.09);
    border-radius: 30px;
    font-size: 13px;
    font-weight: 700;
}

.punto {
    width: 10px;
    height: 10px;
    background: var(--verde);
    border-radius: 50%;
    box-shadow: 0 0 12px var(--verde);
}

.resumen {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    margin-bottom: 22px;
}

.tarjeta {
    position: relative;
    overflow: hidden;
    padding: 22px;
    border-radius: 17px;
    background: var(--panel);
    border: 1px solid var(--borde);
    backdrop-filter: blur(10px);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.20);
}

.tarjeta::after {
    content: "";
    position: absolute;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    right: -30px;
    bottom: -50px;
    background: rgba(255, 255, 255, 0.035);
}

.tarjeta-cabecera {
    display: flex;
    align-items: center;
    gap: 12px;
    color: #d1dce7;
    font-size: 14px;
}

.tarjeta-icono {
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    border-radius: 12px;
    font-size: 22px;
    background: rgba(255, 255, 255, 0.09);
}

.numero {
    margin-top: 12px;
    font-size: clamp(30px, 4vw, 43px);
    font-weight: 800;
    line-height: 1.1;
}

.detalle {
    margin-top: 8px;
    color: #aebdca;
    font-size: 12px;
}

.panel {
    padding: 24px;
    margin-bottom: 22px;
    border-radius: 20px;
    background: var(--panel);
    border: 1px solid var(--borde);
    backdrop-filter: blur(12px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.22);
}

.titulo-seccion {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 20px;
}

.titulo-seccion h2 {
    margin: 0;
    font-size: 21px;
}

.etiqueta {
    padding: 7px 12px;
    border-radius: 20px;
    font-size: 12px;
    color: #dce7ef;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid var(--borde);
}

.parqueadero {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
}

.cupo {
    min-height: 210px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 20px 12px;
    border: 2px dashed rgba(255, 255, 255, 0.35);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.035);
    transition: 0.25s ease;
}

.cupo.libre {
    border-color: rgba(56, 239, 157, 0.60);
    background: rgba(56, 239, 157, 0.055);
}

.cupo.ocupado {
    border-style: solid;
    border-color: rgba(255, 98, 108, 0.75);
    background: rgba(255, 98, 108, 0.11);
}

.numero-cupo {
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 2px;
    color: #d6e1eb;
}

.auto {
    font-size: 64px;
    line-height: 1.1;
    filter: drop-shadow(0 5px 8px rgba(0, 0, 0, 0.3));
}

.estado-cupo {
    font-weight: 800;
    font-size: 14px;
}

.libre .estado-cupo {
    color: var(--verde);
}

.ocupado .estado-cupo {
    color: #ff8b91;
}

.id-vehiculo {
    min-height: 16px;
    color: #d3dce5;
    font-size: 12px;
    text-align: center;
}

.progreso-cabecera {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin: 22px 0 10px;
    font-size: 13px;
    color: #d6e0e8;
}

.barra-fondo {
    width: 100%;
    height: 14px;
    border-radius: 20px;
    overflow: hidden;
    background: rgba(255, 255, 255, 0.13);
}

.barra {
    width: 0%;
    height: 100%;
    border-radius: 20px;
    background: linear-gradient(90deg, #24d18b, #a3f56b);
    transition: width 0.4s ease, background 0.4s ease;
}

.controles {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 14px;
    margin-top: 23px;
}

.boton {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
    min-height: 49px;
    padding: 13px 23px;
    border: 0;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 800;
    cursor: pointer;
    transition: transform 0.2s, filter 0.2s;
}

.boton:hover {
    transform: translateY(-2px);
    filter: brightness(1.08);
}

.boton:disabled {
    cursor: not-allowed;
    opacity: 0.5;
    transform: none;
}

.boton-principal {
    color: #06251a;
    background: linear-gradient(135deg, #42f5a5, #24ce8c);
    box-shadow: 0 6px 20px rgba(36, 206, 140, 0.20);
}

.boton-secundario {
    color: white;
    background: rgba(255, 255, 255, 0.09);
    border: 1px solid var(--borde);
}

.mensaje {
    display: none;
    width: 100%;
    padding: 13px 16px;
    border-radius: 10px;
    font-size: 13px;
    line-height: 1.5;
}

.mensaje.visible {
    display: block;
}

.mensaje.ok {
    color: #a5ffd7;
    background: rgba(56, 239, 157, 0.10);
    border: 1px solid rgba(56, 239, 157, 0.25);
}

.mensaje.error {
    color: #ffb5ba;
    background: rgba(255, 98, 108, 0.10);
    border: 1px solid rgba(255, 98, 108, 0.30);
}

.eventos {
    padding: 0;
    margin: 0;
    list-style: none;
    max-height: 220px;
    overflow-y: auto;
    overflow-x: hidden;
}

.evento {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 14px 4px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.09);
}

.evento:last-child {
    border-bottom: 0;
}

.hora {
    flex-shrink: 0;
    min-width: 76px;
    padding: 6px 8px;
    text-align: center;
    color: #9fffd2;
    background: rgba(56, 239, 157, 0.09);
    border-radius: 7px;
    font-size: 12px;
    font-weight: 700;
}

.texto-evento {
    padding-top: 4px;
    color: #dbe4ec;
    font-size: 13px;
    line-height: 1.5;
    overflow-wrap: anywhere;
}

.vacio {
    color: #bac7d2;
    padding: 20px 0;
    text-align: center;
    font-size: 13px;
}

.pie {
    padding: 12px;
    text-align: center;
    color: #d0d9e2;
    font-size: 12px;
    text-shadow: 0 2px 5px #000;
}

@media (max-width: 760px) {
    .contenedor {
    width: 94%;
    padding-top: 12px;
    box-sizing: border-box;
    margin: 0 auto;
}
    .encabezado {
        padding: 18px;
    }

    .icono-principal {
        width: 52px;
        height: 52px;
        font-size: 27px;
    }

    .resumen {
        grid-template-columns: 1fr;
        gap: 12px;
    }

    .tarjeta {
        padding: 17px;
    }

    .numero {
        font-size: 32px;
    }

    .panel {
        padding: 17px;
    }

    .parqueadero {
        grid-template-columns: 1fr;
    }

    .cupo {
        min-height: 165px;
    }

    .estado-sistema {
        font-size: 11px;
    }

    .boton {
        width: 100%;
    }
}
</style>
</head>

<body>
<div class="contenedor">

    <header class="encabezado">
        <div class="marca">
            <div class="icono-principal">🅿️</div>
            <div>
                <h1>Parqueadero Inteligente</h1>
                <p class="subtitulo">
                    Simulador de concurrencia con hilos y semáforos
                </p>
            </div>
        </div>

        <div class="estado-sistema">
            <span class="punto"></span>
            SISTEMA ACTIVO
        </div>
    </header>

    <section class="resumen">
        <article class="tarjeta">
            <div class="tarjeta-cabecera">
                <div class="tarjeta-icono">🚘</div>
                <span>Cupos ocupados</span>
            </div>
            <div class="numero" id="ocupados">0</div>
            <div class="detalle">Vehículos estacionados actualmente</div>
        </article>

        <article class="tarjeta">
            <div class="tarjeta-cabecera">
                <div class="tarjeta-icono">🅿️</div>
                <span>Cupos disponibles</span>
            </div>
            <div class="numero" id="libres">3</div>
            <div class="detalle">Espacios libres para estacionar</div>
        </article>

        <article class="tarjeta">
            <div class="tarjeta-cabecera">
                <div class="tarjeta-icono">⚙️</div>
                <span>Vehículos en proceso</span>
            </div>
            <div class="numero" id="activos">0</div>
            <div class="detalle">Hilos de vehículos en ejecución</div>
        </article>
    </section>

    <section class="panel">
        <div class="titulo-seccion">
            <h2>🚗 Vista del parqueadero</h2>
            <span class="etiqueta">Capacidad máxima: 3 vehículos</span>
        </div>

        <div class="parqueadero" id="parqueadero">
            <div class="cupo libre">
                <div class="numero-cupo">CUPO 01</div>
                <div class="auto">🅿️</div>
                <div class="estado-cupo">DISPONIBLE</div>
            </div>
            <div class="cupo libre">
                <div class="numero-cupo">CUPO 02</div>
                <div class="auto">🅿️</div>
                <div class="estado-cupo">DISPONIBLE</div>
            </div>
            <div class="cupo libre">
                <div class="numero-cupo">CUPO 03</div>
                <div class="auto">🅿️</div>
                <div class="estado-cupo">DISPONIBLE</div>
            </div>
        </div>

        <div class="progreso-cabecera">
            <span>Nivel de ocupación</span>
            <strong id="porcentaje">0%</strong>
        </div>

        <div class="barra-fondo">
            <div class="barra" id="barra"></div>
        </div>

        <div class="controles">
            <button
                class="boton boton-principal"
                id="agregar"
                onclick="agregarVehiculo()"
            >
                <span>＋</span>
                Agregar vehículo
            </button>

            <button
                class="boton boton-secundario"
                onclick="actualizarEstado()"
            >
                ↻ Actualizar estado
            </button>

            <div class="mensaje" id="mensaje"></div>
        </div>
    </section>

    <section class="panel">
        <div class="titulo-seccion">
            <h2>📋 Registro de eventos</h2>
            <span class="etiqueta">Actividad en tiempo real</span>
        </div>

        <ul class="eventos" id="registro">
            <li class="vacio">Esperando eventos del simulador...</li>
        </ul>
    </section>

    <footer class="pie">
        Simulador de Parqueadero Inteligente · Python · Flask ·
        Threading · Semaphore · Lock
    </footer>

</div>

<script>
let enviando = false;

function mostrarMensaje(texto, tipo) {
    const elemento = document.getElementById("mensaje");
    elemento.textContent = texto;
    elemento.className = "mensaje visible " + tipo;
}

function renderizarCupos(ocupados) {
    const contenedor = document.getElementById("parqueadero");
    contenedor.innerHTML = "";

    for (let i = 0; i < 3; i++) {
        const id = ocupados[i];
        const estaOcupado = Boolean(id);

        const cupo = document.createElement("div");
        cupo.className = "cupo " +
            (estaOcupado ? "ocupado" : "libre");

        const numero = document.createElement("div");
        numero.className = "numero-cupo";
        numero.textContent = "CUPO 0" + (i + 1);

        const auto = document.createElement("div");
        auto.className = "auto";
        auto.textContent = estaOcupado ? "🚘" : "🅿️";

        const estado = document.createElement("div");
        estado.className = "estado-cupo";
        estado.textContent = estaOcupado ? "OCUPADO" : "DISPONIBLE";

        const vehiculo = document.createElement("div");
        vehiculo.className = "id-vehiculo";
        vehiculo.textContent = estaOcupado ? id : "Espacio libre";

        cupo.appendChild(numero);
        cupo.appendChild(auto);
        cupo.appendChild(estado);
        cupo.appendChild(vehiculo);

        contenedor.appendChild(cupo);
    }
}

function renderizarEventos(lista) {
    const registro = document.getElementById("registro");
    registro.innerHTML = "";

    if (!lista || lista.length === 0) {
        const vacio = document.createElement("li");
        vacio.className = "vacio";
        vacio.textContent = "Esperando eventos del simulador...";
        registro.appendChild(vacio);
        return;
    }

    lista.forEach(evento => {
        const elemento = document.createElement("li");
        elemento.className = "evento";

        const hora = document.createElement("span");
        hora.className = "hora";
        hora.textContent = evento.hora;

        const texto = document.createElement("span");
        texto.className = "texto-evento";
        texto.textContent = evento.mensaje;

        elemento.appendChild(hora);
        elemento.appendChild(texto);
        registro.appendChild(elemento);
    });
}

async function actualizarEstado() {
    try {
        const respuesta = await fetch("/estado", {
            cache: "no-store"
        });

        if (!respuesta.ok) {
            throw new Error("No se pudo consultar el estado.");
        }

        const datos = await respuesta.json();

        document.getElementById("ocupados").textContent =
            datos.ocupados;

        document.getElementById("libres").textContent =
            datos.libres;

        document.getElementById("activos").textContent =
            datos.activos;

        document.getElementById("porcentaje").textContent =
            datos.porcentaje + "%";

        const barra = document.getElementById("barra");
        barra.style.width = datos.porcentaje + "%";

        if (datos.porcentaje >= 100) {
            barra.style.background =
                "linear-gradient(90deg, #ff626c, #ff9a62)";
        } else if (datos.porcentaje >= 67) {
            barra.style.background =
                "linear-gradient(90deg, #ffd166, #ff9a62)";
        } else {
            barra.style.background =
                "linear-gradient(90deg, #24d18b, #a3f56b)";
        }

        renderizarCupos(datos.vehiculos_ocupados);
        renderizarEventos(datos.eventos);
            if (datos.ocupados >= 3) {
           mostrarMensaje(
        "⚠️ ¡PARQUEADERO LLENO! Los 3 cupos están ocupados.",
        "error"
        );
        }

        const boton = document.getElementById("agregar");
        boton.disabled = enviando || datos.activos >= 12;

    } catch (error) {
        console.error(error);
        mostrarMensaje(
            "No se pudo actualizar la información. Verifica que el servidor esté activo.",
            "error"
        );
    }
}

async function agregarVehiculo() {
    if (enviando) return;

    enviando = true;
    document.getElementById("agregar").disabled = true;

    
try {
    const respuesta = await fetch("/agregar", {
        method: "POST"
    });

    const datos = await respuesta.json();

    mostrarMensaje(
        datos.mensaje,
        datos.ok ? "ok" : "error"
    );

    if (!datos.ok) {
        alert(
            "⚠️ ¡PARQUEADERO LLENO!\n\n" +
            "Los 3 cupos están ocupados.\n" +
            "El vehículo permanecerá en espera hasta que se libere un espacio."
        );
    }
        await actualizarEstado();

    } catch (error) {
        mostrarMensaje(
            "No fue posible agregar el vehículo. Intenta nuevamente.",
            "error"
        );
    } finally {
        enviando = false;
        await actualizarEstado();
    }
}

actualizarEstado();
setInterval(actualizarEstado, 1000);
</script>

</body>
</html>
"""


# ============================================================
# RUTAS DE LA APLICACIÓN WEB
# ============================================================

@app.route("/")
def inicio():
    return render_template_string(PAGINA)



@app.route("/estado")
def estado():
    estado_parqueadero = control.obtener_estado()

    with lock_contador:
        activos = vehiculos_activos

    with lock_eventos:
        lista_eventos = list(eventos)

    ocupados = estado_parqueadero["cantidad_ocupados"]
    libres = estado_parqueadero["libres"]
    porcentaje = int((ocupados / CAPACIDAD) * 100)

    return jsonify({
        "ocupados": ocupados,
        "libres": libres,
        "activos": activos,
        "porcentaje": porcentaje,
        "parqueadero_lleno": ocupados >= CAPACIDAD,
        "vehiculos_ocupados": estado_parqueadero["ocupados"],
        "eventos": lista_eventos
    })


@app.route("/agregar", methods=["POST"])
def ruta_agregar():
    ok, mensaje = agregar_vehiculo()

    if not ok:
        registrar_evento(mensaje)

    return jsonify({
        "ok": ok,
        "mensaje": mensaje,
        "parqueadero_lleno": not ok
    })


# ============================================================
# INICIAR SERVIDOR
# ============================================================

if __name__ == "__main__":
    registrar_evento(
        "Sistema iniciado. Capacidad disponible: 3 cupos."
    )

    print("=" * 55)
    print(" SIMULADOR DE PARQUEADERO INTELIGENTE")
    print("=" * 55)
    print(" Capacidad: 3 vehículos")
    print(" Interfaz web: puerto 5000")
    print(" Para detener el servidor: Ctrl + C")
    print("=" * 55)

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True
    )
