Utilidades para medir la respuesta de un altavoz en la sala.

## `logsweep2TF.py`

Obtiene la TF Transfer Function de un DUT (device under test) mediante
la deconvolución de una señal de excitación (logsweep) y
la respuesta capturada por el micrófono.

**`DUT   ---> LEFT  CHANNEL`**  (Señal del micrófono)

**`LOOP  ---> RIGHT CHANNEL`** (Bucle opcional para ayudar a validar la medida según la latencia HW vs la longitud N de la secuencia de pruebas)

IMPORTANTE:

Se recomienda una prueba previa de la tarjeta de sonido para verificar que:

- La tarjeta de sonido no pierde muestras (visible en la gráfica del logsweep capturado) y los niveles son correctos.

- La medida es viable (Time clearance) con los parámetros usados.

Ejemplo de captura con interrupciones que pueden ser no audibles:

![gaps](https://github.com/Rsantct/DRC/blob/master/logsweep2TF/gaps_in_recorded.jpg)

NOTA:

Actualmente no se contempla el enventado de la medida para obtener la respuesta libre de reflexiones.


## `roommeasure.py`

Obtiene la medida de la respuesta estacionaria de una sala, mediante el **promediado de medidas en varios puntos de escucha**.

Se obtiene:

**`room_avg.frd`**
Archivo de texto con la respuesta en frecuencia promedio de las medidas en varios puntos de escucha

**`room_avg_smoothed.frd`**
Archivo de texto promedio y suavizado 1/24 oct hasta la Freq Schroeder y progresivamente hacia 1/1 oct en Freq Nyq.

Usar **`-h`** para ver las opciones de uso de ambos scripts.

Se puede elegir la tarjeta de sonido a usar.

Se necesita tener **`https://github.com/AudioHumLab/audiotools`** instalado y actualizado.
