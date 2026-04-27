# Visor 3D - Costa Rica Alta Fidelidad
Visor geografico en siguiente link:  https://asoto59g.github.io/CR3d/ 
_______________________________________________________________________
Este repositorio contiene las herramientas de procesamiento y el visor web necesarios para generar un modelo 3D del relieve topográfico de Costa Rica en alta fidelidad. Al integrar un Modelo de Elevación Digital (DEM) y diversas capas vectoriales estructuradas mediante un enfoque de teselas (tiling), se optimiza sustancialmente la renderización en navegador utilizando Three.js.

## Características Principales

*   **Generación de Teselas (Tiles) de Terreno:** Transformación de un modelo DEM masivo a formato *Terrain-RGB* para una carga dinámica y asíncrona.
*   **Vector Draping (Alineación Topográfica 3D):** Los datos vectoriales (como ríos y caminos) son adaptados dinámicamente a la topografía en el navegador mediante un muestreo directo de las alturas del DEM cargado.
*   **Capas Dinámicas Bajo Demanda:** Renderización a solicitud de las capas de infraestructura y poblaciones. Por defecto, la capa de poblados está desactivada para optimizar la carga inicial.
*   **Escala Hipsométrica Continua:** Somatización de la elevación mediante colores dinámicos (desde verde oscuro, amarillo hasta café) calculados en tiempo real.
*   **Herramientas Interactivas:** Integración de *Raycasting* para consultar nombres de poblados y altitudes exactas. Los iconos de poblados han sido optimizados como círculos negros sutiles.

## Fuentes de Datos

*   **DEM (`CRdemrecort.tif`):** Archivo raster TIFF de altísima resolución (aprox. 30 metros de pixel), que sirve como base principal del relieve.
*   **Vectorial (`packaged_data.gpkg`):** Geopaquete con estructura SQL/espacial que incluye capas de Poblados, Caminos (red vial) y Ríos del país.
*   **Proyección Origial:** CRTM05 (EPSG:5367).

## Arquitectura y Componentes

El proyecto se divide en módulos o scripts de preparación de código abierto y un frontend de visualización web:

### 1. `tile_dem.py`
Procesa y fracciona el DEM original (`CRdemrecort.tif`) generando una pirámide de tiles.
*   Convierte las alturas del modelo a valores RGB estándar (`-10000 + (R*65536 + G*256 + B)*0.1`) lo que consolida los datos como imágenes PNG muy livianas.
*   Transforma internamente las coordenadas esféricas (*WGS84*) al marco de referencia de Costa Rica (*CRTM05*) usando Numpy antes de muestrear para extremar precisión temporal en la vectorización inicial.

### 2. `tile_vectors.py`
Realiza consultas espaciales en la base de datos GPKG, segmenta la data vectorial en áreas pequeñas (cuadrícula de tiles a partir de z=10 hasta z=15) y genera ficheros GeoJSON optimizados con elevaciones tridimensionales.
*   Segmenta la data vectorial en áreas pequeñas (cuadrícula de tiles zoom 10).
*   Genera ficheros GeoJSON optimizados que el visor proyecta sobre el relieve en tiempo real.

### 3. `index.html`
Es el cliente interactivo impulsado por la aceleración WebGL y **Three.js**.
*   **Topografía en Tiempo Real:** Carga los tiles Terrain-RGB de manera inteligente convirtiendo el color del píxel de regreso a valores métricos y ajustando los relieves correspondientes.  
*   **Superposición de Vectores:** Una interfaz amigable provee opciones de activación/inactivación. El visor realiza el *draping* (ajuste de altura) automáticamente al vuelo usando la información de las teselas del terreno.
*   **Información de Herramientas (Tooltips):** Usa lógica y proyecciones espaciales en navegador *Proj4js* junto a un *Three.Raycaster* para identificar los nombres de poblados (propiedad `NOMBRE`) y su altitud.

## Requisitos 

*   Python 3.x
*   Librerías Python: `Pillow (PIL)`, `numpy`
*   Navegador Moderno compatible con WebGL para desplegar `visor_3d.html`.
*   *(Opcional)* Servidor HTTP Local (ejemplo, `python -m http.server`) para cargar librerías javascript por directrices de CORS durante el desarrollo en local.

## Instrucciones de Uso y Procedimiento de Carga

1. Instalar dependencias Python si fuese necesario:
   ```bash
   pip install numpy Pillow
   ```
2. Ejecutar generador de terreno:
   ```bash
   python tile_dem.py
   ```
   *(Esto creará la carpeta /tiles/ poblada de archivos png codificados de terrenos.)*
3. Ejecutar extractor de vectores tridimensionales:
   ```bash
   python tile_vectors.py
   ```
   *(Creará la carpeta /tiles_vector/ conteniendo las geometrías dividas por niveles y coordenadas integradas.)*
4. Lanzar un entorno en red ligero local para abrir la interfaz:
   ```bash
   python -m http.server 8000
   ```
5. Acceder a [`http://localhost:8000/index.html`](http://localhost:8000/index.html) o rutas similiares en tu navegador para interactuar con la topografía de Costa Rica.
