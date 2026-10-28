# Pokédex Completa e Interactiva

Pokédex hecha en Streamlit que consulta la [PokéAPI](https://pokeapi.co) mediante
[pypokedex](https://pypi.org/project/pypokedex/): busca por nombre (con ortografía
flexible y sin acentos), por número de Pokédex Nacional o desde la lista
desplegable de los 1025 Pokémon, y muestra sprite, tipos, altura, peso,
estadísticas base y habilidades.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `app.py` | La aplicación (entrypoint de Streamlit). |
| `pokemon_names.txt` | Los 1025 nombres en orden de Pokédex Nacional. La posición en la lista es el número de Pokédex. |
| `requirements.txt` | Dependencias que instala la nube. |
| `.streamlit/config.toml` | Tema visual. |

## Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abre en `http://localhost:8501`.

## Publicar en internet (gratis)

GitHub por sí solo **no ejecuta** la app (Pages solo sirve HTML/CSS/JS estático y
Streamlit necesita un proceso Python con WebSockets). Lo que sí funciona es
conectar el repositorio a **Streamlit Community Cloud**:

1. Crea un repositorio **público** en GitHub y sube estos 4 archivos (respetando
   la estructura: `app.py` y `pokemon_names.txt` en la raíz).
2. Entra en <https://share.streamlit.io> con tu cuenta de GitHub.
3. *Create app* → elige el repositorio, la rama `main` y `app.py` como
   *Main file path* → *Deploy*.
4. En 1–3 minutos tendrás una URL pública del tipo
   `https://tu-usuario-pokedex.streamlit.app`.

También sirven **Hugging Face Spaces** (SDK Streamlit), **Render** o
**Google Cloud Run**; cualquiera necesita el mismo `requirements.txt`.

### Notas de la nube

- La app "duerme" tras un rato sin visitas; la primera carga puede tardar
  ~30 s en despertar.
- Las consultas a PokéAPI están cacheadas 24 h (`st.cache_data`), así que
  navegar entre Pokémon ya visitados es instantáneo.
- No hay secretos ni claves API: todo son datos públicos.

## Sobre el parche a pypokedex

PokéAPI agregó la clave `versions` dentro de `sprites.other.official-artwork` y
`pypokedex` intenta separar todas las claves de sprites con `split("_", 1)`, lo
que lanzaba `ValueError: not enough values to unpack` en cada consulta. `app.py`
reemplaza ese método interno (`_extract_sprites_seguro`) para ignorar las claves
que no son `front_*`/`back_*`. Si `pypokedex` corrige esto en el futuro, el
parche puede eliminarse sin tocar el resto.

## Aviso

Proyecto de fans, sin fines de lucro. Pokémon y todos los nombres relacionados son
marcas registradas de Nintendo, Creatures Inc. y GAME FREAK Inc. Los datos e
imágenes provienen de PokéAPI / PokeAPI sprites.
