import difflib
import unicodedata
from pathlib import Path

import pypokedex
import pypokedex.pokemon as _pypokedex_pokemon
import streamlit as st
from pypokedex.pokemon import Sprites as _Sprites
from st_keyup import st_keyup

# ---------------------------------------------------------------------------
# ARREGLO PRINCIPAL: pypokedex se rompe con la respuesta actual de PokéAPI
# ---------------------------------------------------------------------------
# PokéAPI agregó la clave "versions" dentro de "sprites.other.official-artwork".
# pypokedex intenta separar TODAS las claves con split("_", 1) y revienta con
# "not enough values to unpack (expected 2, got 1)" en CADA consulta, así que
# ninguna búsqueda mostraba datos. Reemplazamos ese método interno por una
# versión que ignora las claves que no son "front_algo" / "back_algo".
def _extract_sprites_seguro(all_sprites):
    resultado = _Sprites(front={}, back={})
    for clave, url in all_sprites.items():
        if "_" not in clave:
            continue
        direccion, tipo = clave.split("_", 1)
        if direccion == "front":
            resultado.front[tipo] = url
        elif direccion == "back":
            resultado.back[tipo] = url
    return resultado


_pypokedex_pokemon.Pokemon._extract_sprites = staticmethod(_extract_sprites_seguro)

MAX_DEX = 1025
# Ruta relativa al propio archivo: funciona igual en local y en la nube,
# sin depender de desde qué carpeta se lance streamlit.
RUTA_NOMBRES = Path(__file__).with_name("pokemon_names.txt")

# Configuración estética de la página
st.set_page_config(
    page_title="Pokédex Completa Oficial",
    page_icon="https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/master-ball.png",
    layout="centered",
)

st.markdown(
    "<h1 style='display: flex; align-items: center; gap: 15px;'>"
    "<img src='https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/master-ball.png' width='45'> "
    "Pokédex Completa e Interactiva</h1>",
    unsafe_allow_html=True,
)
st.write("Consulta cualquier criatura de la base de datos oficial.")


# --- UTILIDADES DE BÚSQUEDA ---
def normalizar(texto):
    """Minúsculas, sin acentos y solo letras/números: 'Mr. Mime' -> 'mrmime'."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return "".join(c for c in texto if c.isalnum())


# --- CARGA DE LA LISTA COMPLETA DE NOMBRES ---
try:
    # encoding="utf-8" es obligatorio: el archivo tiene "flabébé" y "nidoran♀".
    with open(RUTA_NOMBRES, "r", encoding="utf-8") as f:
        TODOS_LOS_POKEMON_NOMBRES = [linea.strip().lower() for linea in f if linea.strip()]
except FileNotFoundError:
    st.error("⚠️ No se encontró el archivo 'pokemon_names.txt'. Asegúrate de que esté en la misma carpeta.")
    TODOS_LOS_POKEMON_NOMBRES = []

# El archivo está en orden de Pokédex Nacional, así que la posición = número.
DEX_POR_NOMBRE = {}
DEX_POR_CLAVE = {}
for _i, _nombre in enumerate(TODOS_LOS_POKEMON_NOMBRES[:MAX_DEX]):
    DEX_POR_NOMBRE[_nombre] = _i + 1
    DEX_POR_CLAVE.setdefault(normalizar(_nombre), _i + 1)
CLAVES_NORMALIZADAS = list(DEX_POR_CLAVE.keys())


def dex_de_texto(texto):
    """Convierte lo escrito por el usuario en un número de Pokédex (o None)."""
    texto = (texto or "").strip().lower()
    if not texto:
        return None
    if texto.isdigit():
        numero = int(texto)
        return numero if 1 <= numero <= MAX_DEX else None
    if texto in DEX_POR_NOMBRE:
        return DEX_POR_NOMBRE[texto]
    return DEX_POR_CLAVE.get(normalizar(texto))


def buscar_sugerencias(texto, limite=5):
    """Coincidencias por prefijo + ortografía flexible, sin repetir."""
    clave = normalizar(texto)
    if not clave:
        return []

    candidatos = []
    for nombre in TODOS_LOS_POKEMON_NOMBRES:
        if nombre.startswith(texto.strip().lower()) or normalizar(nombre).startswith(clave):
            candidatos.append(nombre)

    for coincidencia in difflib.get_close_matches(clave, CLAVES_NORMALIZADAS, n=3, cutoff=0.6):
        nombre = TODOS_LOS_POKEMON_NOMBRES[DEX_POR_CLAVE[coincidencia] - 1]
        candidatos.append(nombre)

    unicos = []
    for candidato in candidatos:
        if candidato not in unicos:
            unicos.append(candidato)
    return unicos[:limite]


def url_miniatura(dex):
    if not dex:
        return "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/poke-ball.png"
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{dex}.png"


# --- CARGA DE DATOS CON CACHÉ ---
# Cada tecla o clic provoca un rerun; sin caché se pediría el mismo Pokémon a
# PokéAPI decenas de veces. En la nube eso es lento y gasta el límite de la API.
@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def cargar_pokemon(dex):
    return pypokedex.get(dex=int(dex))


# --- INICIALIZAR LA MEMORIA (SESSION STATE) ---
if 'busqueda_activa' not in st.session_state:
    st.session_state.busqueda_activa = 25  # Pikachu por defecto
if 'ultimo_texto' not in st.session_state:
    st.session_state.ultimo_texto = ""

# Compatibilidad con sesiones antiguas que guardaban nombres en vez de números.
if isinstance(st.session_state.busqueda_activa, str):
    st.session_state.busqueda_activa = dex_de_texto(st.session_state.busqueda_activa) or 25


# --- EL BUSCADOR UNIVERSAL ---
st.markdown("---")

texto_busqueda = st_keyup(
    "🔍 Escribe un Nombre, Número de Pokédex o busca con ortografía flexible:",
    key="entrada_busqueda",
)

# ARREGLO: la búsqueda ya no se re-aplica en cada rerun. Antes, si dejabas
# "pikachu" escrito, cada clic en Anterior/Siguiente volvía a Pikachu.
if texto_busqueda and texto_busqueda.strip():
    consulta = texto_busqueda.strip().lower()

    if consulta != st.session_state.ultimo_texto:
        st.session_state.ultimo_texto = consulta
        st.session_state.sugerencias_ocultas = False
        dex_exacto = dex_de_texto(consulta)

        if dex_exacto is not None:
            st.session_state.busqueda_activa = dex_exacto
        elif consulta.isdigit():
            st.warning("⚠️ La Pokédex Nacional actual va del #1 al #1025.")

    # Las sugerencias se siguen mostrando aunque el texto ya esté procesado:
    # si se dejaran de dibujar, el clic sobre sus botones se perdería.
    mostrar_sugerencias = (
        not st.session_state.get("sugerencias_ocultas", False)
        and dex_de_texto(consulta) is None
        and not consulta.isdigit()
    )

    if mostrar_sugerencias:
        sugerencias = buscar_sugerencias(consulta)

        if sugerencias:
            st.info("💡 Sugerencias detectadas:")
            cols_sugerencias = st.columns(len(sugerencias))

            for i, sugerencia in enumerate(sugerencias):
                with cols_sugerencias[i]:
                    st.markdown(
                        f"<div style='display: flex; justify-content: center; height: 60px;'>"
                        f"<img src='{url_miniatura(DEX_POR_NOMBRE[sugerencia])}' "
                        f"style='object-fit: contain; width: 60px;'>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(f"{sugerencia.capitalize()}", key=f"btn_{sugerencia}", width="stretch"):
                        st.session_state.busqueda_activa = DEX_POR_NOMBRE[sugerencia]
                        st.session_state.sugerencias_ocultas = True
                        st.rerun()
        elif len(consulta) >= 3:
            st.error("No se encontraron coincidencias. Revisa la ortografía.")


# --- MENÚ DESPLEGABLE COMPLETO ---
def actualizar_desde_lista():
    seleccion = st.session_state.get("selector_lista", "(Elige uno)")
    if seleccion and seleccion != "(Elige uno)":
        numero_extraido = int(seleccion.split(" - ")[0].replace("#", ""))
        st.session_state.busqueda_activa = numero_extraido
        # Devolvemos el menú a su estado vacío para que las flechas puedan funcionar
        st.session_state.selector_lista = "(Elige uno)"


with st.expander("Ver lista desplegable completa"):
    LISTA_NUMERO_NOMBRE = [
        f"#{i + 1} - {nombre.capitalize()}"
        for i, nombre in enumerate(TODOS_LOS_POKEMON_NOMBRES[:MAX_DEX])
    ]

    st.selectbox(
        "Selecciona de la lista:",
        options=["(Elige uno)"] + LISTA_NUMERO_NOMBRE,
        key="selector_lista",
        on_change=actualizar_desde_lista,
    )


# --- RENDERIZADO DE LOS DATOS DEL POKÉMON ---
dex = st.session_state.busqueda_activa

if dex:
    try:
        with st.spinner("Conectando con la base de datos de pypokedex..."):
            pokemon = cargar_pokemon(dex)
    except Exception as e:
        st.error(f"No se pudo cargar el Pokémon #{dex}: {e}")
        st.stop()

    # --- BOTONES DE NAVEGACIÓN (ANTERIOR / SIGUIENTE) ---
    st.markdown("---")
    col_prev, col_center, col_next = st.columns([1, 2, 1])

    with col_prev:
        if pokemon.dex > 1:
            if st.button("⬅️ Anterior", width="stretch"):
                st.session_state.busqueda_activa = pokemon.dex - 1
                st.rerun()

    with col_center:
        st.markdown(
            f"<h2 style='text-align: center; margin: 0;'>{pokemon.name.replace('-', ' ').capitalize()}</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<h4 style='text-align: center; color: gray; margin: 0;'>N.° Nacional: #{pokemon.dex}</h4>",
            unsafe_allow_html=True,
        )

    with col_next:
        if pokemon.dex < MAX_DEX:
            if st.button("Siguiente ➡️", width="stretch"):
                st.session_state.busqueda_activa = pokemon.dex + 1
                st.rerun()

    # --- ESTRUCTURA VISUAL EN DOS COLUMNAS ---
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        # Sprite normal y, si no existe (algunas formas), el artwork oficial.
        url_imagen = (pokemon.sprites.front or {}).get("default")
        if not url_imagen:
            for grupo in pokemon.other_sprites.values():
                url_imagen = (grupo.front or {}).get("default")
                if url_imagen:
                    break

        if url_imagen:
            st.markdown(
                f"<div style='display: flex; justify-content: center;'>"
                f"<img src='{url_imagen}' width='200'></div>",
                unsafe_allow_html=True,
            )
        else:
            st.warning("No se encontró imagen para esta forma.")

        st.markdown("### 📐 Características")
        st.write(f"**Altura:** {pokemon.height / 10:.1f} m")
        st.write(f"**Peso:** {pokemon.weight / 10:.1f} kg")
        experiencia = f"{pokemon.base_experience} XP" if pokemon.base_experience else "—"
        st.write(f"**Experiencia Base:** {experiencia}")

        st.markdown("### 🏷️ Tipos")
        for tipo in pokemon.types:
            st.info(tipo.upper())

    with col2:
        st.markdown("### 📊 Estadísticas Base")
        stats = pokemon.base_stats

        st.write(f"**Vida (HP):** {stats.hp}")
        st.progress(min(stats.hp / 255, 1.0))

        st.write(f"**Ataque:** {stats.attack}")
        st.progress(min(stats.attack / 255, 1.0))

        st.write(f"**Defensa:** {stats.defense}")
        st.progress(min(stats.defense / 255, 1.0))

        st.write(f"**Ataque Especial:** {stats.sp_atk}")
        st.progress(min(stats.sp_atk / 255, 1.0))

        st.write(f"**Defensa Especial:** {stats.sp_def}")
        st.progress(min(stats.sp_def / 255, 1.0))

        st.write(f"**Velocidad:** {stats.speed}")
        st.progress(min(stats.speed / 255, 1.0))

        st.markdown("### 🌀 Habilidades")
        for habilidad in pokemon.abilities:
            oculta = " *(Oculta)*" if habilidad.is_hidden else ""
            st.write(f"• {habilidad.name.replace('-', ' ').capitalize()}{oculta}")
