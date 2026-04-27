# Visor 3D Costa Rica - Premium

Este repositorio contiene las herramientas de procesamiento y el visor web interactivo diseñado para visualizar un modelo 3D de alta fidelidad del relieve topográfico de Costa Rica. Utilizando un Modelo de Elevación Digital (DEM) y capas vectoriales optimizadas mediante teselas (tiling), se logra una renderización fluida y profesional en el navegador mediante **Three.js**.

## Características Principales

*   **Visualización de Terreno 3D:** Carga dinámica de teselas *Terrain-RGB* que permiten reconstruir el relieve con precisión métrica y una exageración vertical optimizada (1.875x) para apreciar mejor la orografía.
*   **Capa Satelital Híbrida:** Opción de alternar entre el modelo de elevación coloreado y una capa de **Google Satélite** de alta resolución.
*   **Simbología Hipsométrica Detallada:** Representación cromática de la elevación basada en una leyenda de 16 niveles, desde el nivel del mar hasta cumbres superiores a los 3000m, incluyendo zonas de depresión y océanos.
*   **Herramientas de Medición:** Funcionalidad integrada para medir **distancias horizontales** y calcular **áreas** en hectáreas directamente sobre el terreno 3D.
*   **Perfil Topográfico en Tiempo Real:** Herramienta interactiva para trazar trayectorias y generar un gráfico de perfil de elevación con estadísticas de altitud máxima, mínima y distancia total.
*   **Alineación Topográfica (Vector Draping):** Las capas de poblados, carreteras y ríos se ajustan automáticamente a la altura del terreno cargado, garantizando una superposición espacial perfecta.
*   **Interactividad y Consultas:** Uso de *Raycasting* para identificar nombres de poblaciones y consultar altitudes exactas mediante tooltips dinámicos.

## Estructura de Datos

El visor utiliza una estructura de archivos optimizada para la web:

*   **`/tiles/`:** Pirámide de imágenes PNG codificadas en formato *Terrain-RGB* (Zoom nivel 10).
*   **`/tiles_vector/`:** Datos vectoriales en formato GeoJSON segmentados por teselas, incluyendo:
    *   **Poblados:** Representados por marcadores circulares sutiles con información de atributos.
    *   **Carreteras:** Red vial nacional proyectada sobre el relieve.
    *   **Ríos:** Red hídrica principal con alineación tridimensional.

## Arquitectura del Sistema

### 1. Preparación de Datos (Backend/Scripts)
*   **`tile_dem.py`:** Convierte el DEM original a teselas RGB siguiendo la fórmula: `Elevación = -10000 + (R*65536 + G*256 + B)*0.1`.
*   **`tile_vectors.py`:** Procesa geopaquetes (GPKG) o shapefiles para generar la estructura de tiles vectoriales en GeoJSON.

### 2. Visor Web (`index.html`)
Impulsado por WebGL y un conjunto de librerías modernas:
*   **Three.js:** Motor principal de renderizado 3D y manejo de luces/sombras.
*   **OrbitControls:** Permite una navegación fluida (rotación, zoom y desplazamiento) por el modelo.
*   **Proj4js:** Gestión de proyecciones cartográficas para asegurar la precisión espacial (Web Mercator / EPSG:3857).

## Requisitos y Configuración

*   Navegador moderno compatible con **WebGL**.
*   Para desarrollo local, se requiere un servidor HTTP (debido a políticas de CORS para archivos locales).

### Ejecución Local

1.  Asegúrate de que las carpetas `/tiles/` y `/tiles_vector/` existan y contengan los datos procesados.
2.  Lanza un servidor web ligero (ejemplo con Python):
    ```bash
    python -m http.server 8000
    ```
3.  Accede a [`http://localhost:8000/index.html`](http://localhost:8000/index.html) en tu navegador.

## Notas Técnicas

*   **Proyección:** El visor opera internamente en Web Mercator para compatibilidad con servicios de mapas globales.
*   **Rendimiento:** Las teselas se cargan de forma asíncrona para minimizar el tiempo de espera inicial. Se recomienda el uso de una GPU dedicada para una experiencia óptima en modelos de gran escala.
