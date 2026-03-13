# RadioHub - Información técnica

Este manual explica los conceptos clave, los términos técnicos y las limitaciones de RadioHub. Le ayuda a comprender por qué ciertas funciones funcionan de la manera en que lo hacen.

---

## Modos de reproducción

### Modo HLS (predeterminado)

HLS significa "HTTP Live Streaming". RadioHub convierte el flujo de radio a través del backend en pequeños segmentos que el navegador puede reproducir. Esto permite:

- **Diferido:** Retroceder dentro del programa en curso
- **Pausa y reanudación:** El búfer continúa en segundo plano
- **Grabación del búfer:** Grabar contenido ya escuchado (HLS-REC)
- **Control de tasa de bits:** Adaptación automática a la conexión

El búfer HLS se gestiona en el backend. El tamaño se puede configurar en [Ajustes > General](#/setup/allgemein/einstellungen) (Búfer de diferido).

### Modo Direct

En modo Direct, el navegador se conecta directamente al flujo original de la emisora. Esto es más eficiente en recursos pero sin diferido, pausa ni grabación del búfer. Útil para servidores que no admiten la conversión HLS.

---

## Badges en la lista de emisoras

### ICY (verde / gris)

**ICY** significa "Icecast Metadata" - un protocolo que permite a las emisoras de radio enviar el título actual dentro del flujo. Cuando una emisora soporta ICY, RadioHub muestra el título actual y puede dividir automáticamente las grabaciones en canciones individuales.

- **ICY (verde, "good"):** La emisora proporciona marcas de tiempo precisas de cambio de título. Los cortes serán limpios.
- **ICY (verde, "poor"):** La emisora proporciona datos ICY, pero las marcas de tiempo son imprecisas (p. ej. informes retrasados). Los cortes pueden tener solapamientos o huecos.
- **ICY (gris):** ICY está presente pero la calidad aún no ha sido evaluada. Haga clic para alternar entre "good" y "poor".

**¿Por qué es importante?** Algunas emisoras informan del nuevo título solo segundos después del cambio real. RadioHub utiliza posiciones en bytes en el flujo de audio para el cálculo de cortes, pero si la emisora informa con retraso, el corte estará desplazado.

### Badges AD (detección de publicidad)

RadioHub puede verificar las emisoras en busca de publicidad. La verificación se puede iniciar en [Setup > Radio > Emisoras](#/setup/radio/sender) y analiza las URL de flujo y las respuestas del servidor:

- **0% AD (verde):** Sin sospecha de publicidad tras la verificación
- **XX% AD (amarillo):** Porcentaje de sospecha (p. ej. "35% AD") - umbral configurable
- **AD (rojo):** Marcado manualmente como publicidad (oculto)
- **OK (azul):** Aprobado manualmente a pesar de la sospecha

---

## Sistema de grabación

### Grabación segmentada

RadioHub graba en segmentos de 30 minutos. Si la conexión con la emisora se interrumpe, como máximo se pierde el segmento actual - no la grabación completa. Para una grabación de 8 horas, eso serían como máximo 30 minutos en lugar de todo. Los ajustes de grabación (formato, tasa de bits, carpeta) se encuentran en [Setup > Grabaciones](#/setup/aufnahmen).

### Detección de bloqueo

Durante una grabación, RadioHub supervisa el tamaño del archivo. Si el archivo no crece durante 30 segundos, el proceso de grabación se detecta como "bloqueado" y se reinicia. Esto evita grabaciones silenciosas donde FFmpeg está ejecutándose pero ya no recibe datos.

### División por título ICY

Si una emisora tiene metadatos ICY, los segmentos de 30 minutos se dividen automáticamente en canciones individuales basándose en los cambios de título detectados después de la grabación. Sin ICY, los bloques de 30 minutos permanecen como segmentos.

### Flujos HTTPS y reconexión

Muchas emisoras utilizan HTTPS. La función de reconexión integrada de FFmpeg solo funciona de manera fiable con flujos HTTP. Por eso, RadioHub gestiona la supervisión y el reinicio en caso de pérdida de conexión por sí mismo, independientemente del protocolo.

---

## Diferido y búfer

### ¿Cómo funciona el diferido?

El backend mantiene un búfer rotativo de segmentos de audio. Cada segmento dura unos segundos. El navegador solicita estos segmentos a través de la lista de reproducción HLS. Al retroceder, se cargan segmentos más antiguos del búfer.

### Grabación del búfer (HLS-REC)

La grabación del búfer utiliza el búfer HLS existente. Cuando inicia una grabación, RadioHub puede incluir los últimos X minutos del búfer. El periodo de retrospectiva es configurable en [Ajustes > General](#/setup/allgemein/einstellungen) (Grabación HLS). Esto permite grabar una canción que ya está sonando.

---

## Cutter (herramienta de edición)

### Forma de onda

La visualización de la forma de onda se calcula a partir de los datos de audio (valores de pico). Muestra el volumen a lo largo del tiempo y ayuda a colocar con precisión los puntos de corte.

### Marcadores

Los marcadores son puntos de corte en la forma de onda. Se pueden establecer manualmente o automáticamente a partir de los cambios de título ICY. Al cortar, la grabación se divide en estos puntos en segmentos.

### Análisis de transición

El análisis examina las zonas de audio alrededor de cada marcador. Evalúa si la transición es limpia (silencio entre títulos) o problemática (p. ej. fundido cruzado donde dos títulos se solapan). Colores: Verde = bueno, Amarillo = verificar, Rojo = problemático.

### Normalización (EBU R128)

La normalización ajusta el volumen al estándar EBU R128 - el estándar europeo de radiodifusión para una sonoridad consistente. De esta manera, todos los segmentos suenan igual de fuerte, independientemente del volumen original de la emisora.

---

## Sistema de podcasts

### Descarga automática

Los podcasts suscritos pueden descargar automáticamente nuevos episodios. El intervalo es configurable en [Setup > Podcast](#/setup/podcast). Las descargas se almacenan localmente y están disponibles sin conexión.

### Actualización de feeds

Los feeds de podcasts se consultan vía RSS/Atom. El [intervalo de actualización](#/setup/podcast) determina con qué frecuencia RadioHub busca nuevos episodios.

---

## Almacenamiento y datos

En [Setup > Almacenamiento](#/setup/speicher), se pueden configurar las rutas de almacenamiento para grabaciones, podcasts y caché. La pantalla muestra el espacio utilizado y libre por zona.

Las fuentes de datos externas (API Radio-Browser, Podcast Index) son visibles en [Setup > Servicios](#/setup/dienste) y se pueden redirigir a sus propias instancias si es necesario.

---

## Procesos automáticos en segundo plano

RadioHub ejecuta varios procesos en segundo plano que funcionan sin interacción del usuario:

### Actualización de feeds de podcasts

Al iniciar RadioHub, se lanza un proceso periódico en segundo plano que verifica automáticamente todos los feeds de podcasts suscritos en busca de nuevos episodios. El intervalo (predeterminado: 6 horas) es configurable en [Setup > Podcast](#/setup/podcast). Con la descarga automática activada, los nuevos episodios se descargan automáticamente.

### Gestión del búfer HLS

Tan pronto como se reproduce una emisora en modo HLS, el backend inicia un proceso FFmpeg que divide el flujo de audio en segmentos cortos (1 segundo cada uno). Estos forman un búfer rotativo de 10 minutos. En paralelo, un registrador de metadatos ICY detecta los cambios de título en el flujo. Ambos procesos finalizan automáticamente cuando se detiene la reproducción.

### Supervisión de grabaciones

Durante una grabación activa, se ejecutan dos procesos de supervisión:

- **Detección de bloqueo:** Cada 30 segundos se comprueba si el archivo de grabación está creciendo. Tres comprobaciones consecutivas sin crecimiento (90 segundos) desencadenan un reinicio del proceso de grabación.
- **Supervisión del almacenamiento:** El espacio libre en disco se comprueba regularmente. Si baja de 100 MB, la grabación se detiene automáticamente para evitar pérdida de datos.

### Grabación del búfer HLS (HLS-REC)

Durante una grabación del búfer HLS, un proceso recopilador copia nuevos segmentos del búfer HLS al directorio de grabación cada 0,5 segundos. Al inicio, los minutos de retrospectiva configurados se toman adicionalmente del búfer existente. Al detenerse, los segmentos se fusionan automáticamente y se dividen en títulos individuales si hay datos ICY disponibles.

### Caché de favicons

Al cargar la lista de emisoras, los iconos faltantes se descargan en segundo plano y se almacenan en caché localmente. Este proceso se ejecuta silenciosamente y no afecta a la interfaz.

### Detección de tasa de bits

Al reproducir una emisora por primera vez, RadioHub verifica la tasa de bits real y el códec mediante FFprobe. El resultado se guarda y se muestra en la lista de emisoras. En [Setup > Radio > Emisoras](#/setup/radio/sender), se puede iniciar una verificación masiva para todas las emisoras.

---

## Limitaciones conocidas

- **Diferido solo en modo HLS:** Los flujos directos se transmiten 1:1, sin almacenamiento en búfer.
- **La calidad ICY varía:** Algunas emisoras proporcionan metadatos imprecisos o retrasados. Esto afecta la precisión de los cortes.
- **Certificados SSL:** Algunas emisoras utilizan configuraciones SSL inusuales. RadioHub lo soluciona cuando es necesario, pero pueden aparecer advertencias.
- **Grabaciones largas:** Durante las pérdidas de conexión, como máximo se pierden 30 minutos (un segmento). Los segmentos más antiguos se conservan.
- **Limitaciones del navegador:** La API Web Audio en el navegador solo puede proporcionar datos de VU-metro cuando el contexto de audio está activo. Algunos navegadores requieren interacción del usuario para esto.

---

## Para saber más

Para los curiosos de la técnica - las tecnologías y estándares detrás de RadioHub:

### Protocolos de streaming

- [HTTP Live Streaming (HLS)](https://es.wikipedia.org/wiki/HTTP_Live_Streaming) - Protocolo de streaming adaptativo de Apple utilizado por RadioHub para el diferido
- [Icecast](https://es.wikipedia.org/wiki/Icecast) - Servidor de streaming de código abierto que popularizó el protocolo de metadatos ICY
- [SHOUTcast / Protocolo ICY](https://es.wikipedia.org/wiki/SHOUTcast) - Origen del estándar de metadatos ICY para información de título en flujos
- [Radio por Internet](https://es.wikipedia.org/wiki/Radio_por_internet) - Visión general del streaming de radio en Internet

### Formatos de audio y códecs

- [MP3 (MPEG-1 Audio Layer 3)](https://es.wikipedia.org/wiki/MP3) - El formato de audio más común para flujos de radio
- [AAC (Advanced Audio Coding)](https://es.wikipedia.org/wiki/Advanced_Audio_Coding) - Códec más moderno con mejor calidad a la misma tasa de bits
- [Ogg Vorbis](https://es.wikipedia.org/wiki/Vorbis) - Códec de audio libre y abierto
- [FLAC (Free Lossless Audio Codec)](https://es.wikipedia.org/wiki/FLAC) - Compresión sin pérdidas para la más alta calidad

### Procesamiento de audio

- [EBU R128](https://es.wikipedia.org/wiki/EBU_R_128) - Estándar europeo de normalización de sonoridad en radiodifusión
- [FFmpeg](https://es.wikipedia.org/wiki/FFmpeg) - El framework multimedia central utilizado por RadioHub para conversión, grabación y edición
- [Web Audio API](https://developer.mozilla.org/es/docs/Web/API/Web_Audio_API) - Interfaz del navegador para análisis de audio (VU-metro, forma de onda)

### Fuentes de datos

- [API Radio-Browser](https://www.radio-browser.info/) - Base de datos comunitaria abierta con más de 30.000 emisoras de radio en todo el mundo
- [Podcast Index](https://podcastindex.org/) - Catálogo de podcasts abierto como alternativa a directorios propietarios
- [RSS (Really Simple Syndication)](https://es.wikipedia.org/wiki/RSS) - El formato de feed a través del cual los podcasts proporcionan nuevos episodios

### Fundamentos técnicos

- [Tasa de bits](https://es.wikipedia.org/wiki/Tasa_de_bits) - Tasa de datos de un flujo de audio (p. ej. 128 kbps, 320 kbps)
- [Streaming](https://es.wikipedia.org/wiki/Streaming) - Fundamentos de la transmisión de datos en tiempo real
- [Compresión de audio](https://es.wikipedia.org/wiki/Compresi%C3%B3n_de_audio) - Cómo funciona la compresión con pérdidas
- [SSL/TLS](https://es.wikipedia.org/wiki/Seguridad_de_la_capa_de_transporte) - Cifrado utilizado en flujos HTTPS
