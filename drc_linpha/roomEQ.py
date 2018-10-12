#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    roomEQ.py

    Calcula un FIR para ecualizar la respuesta de una sala.

    Uso:
        python roomEQ.py respuesta.frd  -fs=xxxxx  [ -ref=XX  -scho= XX e=XX -v ]

        -fs=    fs del FIR de salida, por defecto 48000 (Hz)
        -e=     Longitud del FIR en taps 2^XX (por defecto 2^14 = 16 Ktaps)
        -ref=   Nivel de referencia en XX dB (autodetectado por defecto)
        -scho=  Frecuencia de Schroeder (por defecto 200 Hz)
        -v      Visualiza los impulsos FIR generados

    Se necesita  github.com/AudioHumLab/audiotools

"""
#
# v0.1a
#   - Nombrado de archivos de salida para FIRtro
#   - Muestra la correspondencia del nivel de referencia estimado en el gráfico
# v0.1b
#   - Longitud del FIR y nivel de referencia en command line.
#   - Revisión del cómputo del FIR

##########################################################################
# AJUSTES POR DEFECTO:
##########################################################################

# Salida:
m       = 2**14     # Longitud del FIR por defecto 2^14 = 16 Ktaps
fs      = 48000     # fs del FIR de salida
verFIRs = False

# Nivel de referencia:
autoRef = True
f1, f2  = 400, 4000 # Rango de frecs. para decidir el nivel de referencia

# TARGET sobre la curva .frd original
Noct    = 96        # Suavizado fino inicial 1/96 oct
fScho   = 200       # Frec de Schroeder
octScho = 2         # Octavas respecto a la freq. Schoeder para iniciar
                    # la transición de suavizado fino hacia 1/1 oct
Tspeed  = "medium"  # Velocidad de transición del suavizado audiotools/smoothSpectrum.py

##########################################################################
# IMPORTA MODULOS
##########################################################################
# Para que este script pueda estar fuera de ~/audiotools
import os
import sys
HOME = os.path.expanduser("~")
sys.path.append(HOME + "/audiotools")
# modulos de audiotools:
try:
    import utils
    import pydsd
except:
    raise ValueError("rew2fir.py necesita https://githum.com/AudioHumLab/audiotools")
    sys.exit()

# Módulo de AudioHumLab/audiotools
from smoothSpectrum import smoothSpectrum as smooth

# Módulos estandar
import numpy as np
from scipy import signal
from matplotlib import pyplot as plt

##########################################################################
# 0 LEE ARGUMENTOS
##########################################################################

if len(sys.argv) == 1:
    print __doc__
    sys.exit()

for opc in sys.argv[1:]:

    if opc[0] <> '-' and opc[-4:] in ('.frd','.txt'):
        FRDname = opc
        # Lee el contenido del archivo .frd
        FR, fs_FRD = utils.readFRD(FRDname)
        freq = FR[:, 0]     # >>>> vector de frecuencias <<<<
        mag  = FR[:, 1]     # >>>> vector de magnitudes  <<<<

    elif opc[:4] == '-fs=':
        if opc[4:] in ('44100', '48000', '96000'):
            fs = int(opc[4:])
        else:
            print "fs debe ser 44100 | 48000 | 96000"
            sys.exit()

    elif opc[:3] == '-e=':
        if opc[3:] in ('12', '13', '14', '15', '16'):
            m = 2**int(opc[3:])
        else:
            print "m: 12...16 (4K...64K taps)"
            sys.exit()

    elif opc[:5] == '-ref=':
        try:
            ref_level = opc[5:]
            ref_level = round( float(ref_level), 1)
            autoRef = False
        except:
            print __doc__
            sys.exit()

    elif opc[:6] == '-scho=':
        try:
            fScho = float(opc[6:])
        except:
            print __doc__
            sys.exit()

    elif '-v' in opc:
        verFIRs = True

    else:
        print __doc__
        sys.exit()

# Auxiliares para manejar los archivos de salida y para printados:
FRDbasename = FRDname.split("/")[-1]
FRDpathname = "/".join(FRDname.split("/")[:-1])

# Información fs
if fs == fs_FRD:
    print "(i) fs=" + str(fs) + " coincide con la indicada en " + FRDbasename
else:
    print "(i) fs=" + str(fs) +  " distinta de " + str(fs_FRD) + " en " + FRDbasename

#######################################################################################
# 1 CALCULO DEL TARGET: ecualizaremos una versión suavizada de la respuesta de la sala
#######################################################################################

# 1.1 Nivel de referencia
# 'rmag' es una curva muy suavizada 1/1oct que usaremos para tomar el nivel de referencia
rmag = smooth(freq, mag, Noct=1)
if autoRef:
    f1_idx = (np.abs(freq - f1)).argmin()
    f2_idx = (np.abs(freq - f2)).argmin()
    # 'r2mag' es un minivector de las magnitudes del rango de referencia:
    r2mag = rmag[ f1_idx : f2_idx ]
    # Vector de pesos auxiliar para calcular el promedio, de longitud como r2mag
    weightslograte = .5
    weights = np.logspace( np.log(1), np.log(weightslograte), len(r2mag) )
    # Calculamos el nivel de referencia
    ref_level = round( np.average( r2mag, weights=weights ), 2)
    print "(i) Nivel de referencia estimado: " +  str(ref_level) + " dB --> 0 dB"
else:
    print "(i) Nivel de referencia: " +  str(ref_level) + " dB --> 0 dB"

# 1.2 Curva 'target': será una versión suavizada de la respuesta .frd de la sala:
# 'f0': freq a la que empezamos a suavizar más hasta llegar a 1/1 oct en Nyquist
f0 = 2**(-octScho) * fScho
# 'Noct': suavizado fino inicial en graves (por defecto 1/48 oct)
# 'Tspeed': velocidad de transición del suavizado audiotools/smoothSpectrum.py
print "(i) Suavizando la respuesta para calcular el target"
target = smooth(freq, mag, Noct, f0=f0, Tspeed=Tspeed)

# 1.3 Reubicamos las curvas en el nivel de referencia
mag    -= ref_level   # curva de magnitudes original
rmag   -= ref_level   # minicurva de magnitudes para buscar el ref_level
target -= ref_level   # curva target

##########################################################################
# 2 CÁLCULO DE LA EQ
##########################################################################

# 'eq' es la curva de ecualización por inversión del target:
eq  = -target

# Recortamos ganacias positivas:
np.clip(eq, a_min=None, a_max=0.0, out=eq)
# Nótese que ahora 'eq' tiene unas transiciones abruptas en 0 dB debidas al recorte.

# Limamos asperezas:

# Versión suavizada de 'eq' de la que nos interesa solo el suavizado cerca de 0 dB
eqaux = smooth(freq, eq, Noct=12) # Noct=12 parece el valor más adecuado.

# Actualizamos 'eq' con los valores altos de 'eqaux', de manera que 
# respetemos los valles profundos y suavizamos solo las transiciones de np.clip
np.copyto( eq, eqaux, where=(eqaux > -3.0) )

# DEBUG para ver lo que hemos hecho:
#plt.xlim(20,20000);plt.ylim(-15, 10)
#plt.semilogx(freq, target+eq,   label='target + eq')
#plt.semilogx(freq, eq,          label='eq', color='red')
#plt.semilogx(freq, eqaux,       label='eqaux', linestyle=':')
#plt.axvline(fScho,              label='Schroeder', color='black', linestyle=':')
#plt.axvline(f0,                 label='f0 = -' + str(octScho) + ' oct', color='grey', linestyle=':')
#plt.legend()
#plt.show()
#sys.exit()

##########################################################################
# 2.3 Interpolamos la curva 'eq' para adaptarnos a la longitud 'm'
#     y a la 'fs' deseadas para el impulso del FIR de salida.
#
#   Se observa que ARTA proporciona respuestas .frd
#   - de longitud power of 2
#   - el primer bin es 0 Hz
#   - si fs=48000, el último bin es fs/2 
#   - si fs=44100, el último bin es (fs/2)-1  ¿!? what the fuck 
#
#   NOTA: interpolando con pydsd.lininterp tenemos garantizado que:
#   - La longitud del nuevo semiespectro será ODD (power of 2) + 1,
#     conveniente para computar un wholespectrum EVEN que servirá para
#     sintetizar el IR con IFFT
#   - El primer bin es 0 Hz y el último es Nyquist
#
##########################################################################
print "(i) Interpolando"
newFreq, newEq = pydsd.lininterp(freq, eq, m, fs)

##########################################################################
# 3. Computamos el FIR de salida que usaremos en el convolver.
#    dom. de la freq ---( IFFT )---> dom. del tiempo
##########################################################################

# 3.1 Comprobamos que sea ODD
if len(newEq) % 2 == 0:
    raise ValueError("(!) Algo va mal debería ser un semiespectro ODD: " + str(len(newEq)))
    sys.exit()

# 3.2 Traducimos dBs --> linear
newEqlin = 10.0**(newEq/20.0)

# 3.3 Computamos el impulso calculando la IFFT de la curva 'newEq'.
#     OjO nuestra curva semiespectro 'newEq' es una abstracción reducida a magnitudes
#     de freqs positivas, pero la IFFT necesita un espectro causal (con phase minima)
#     y completo (freqs positivas y negativas)
wholespectrum = pydsd.minphsp( pydsd.wholespmp(newEqlin) ) # Ahora ya tiene phase
# dom.F --> dom.T
imp = np.real( np.fft.ifft( wholespectrum ) )
imp = pydsd.semiblackmanharris(m) * imp[:m]

# Ahora 'imp' tiene una respuesta causal, natural, o sea de phase mínima.

# 3.4 Versión linear-phase (experimental)
impLP = utils.MP2LP(imp, windowed=True, kaiserBeta=1)

##########################################################################
# 4 Guardamos los impulsos en archivos .pcm
##########################################################################

# Separamos los FIR de salida en un directorio de la fs solicitada
if FRDpathname:
    dirSal = FRDpathname + "/" + str(fs)
else:
    dirSal = str(fs)
os.system("mkdir -p " + dirSal)

# Indicativo del canal para el nombre del .pcm de salida
ch = 'C'
if FRDbasename[0].upper() in ('L','R'):
    ch = FRDbasename[0].upper()
    resto = FRDbasename[1:-4].strip().strip('_').strip('-')
mpEQpcmname = str(fs)+'/drc-X-'+ch+'_mp_'+resto+'.pcm'
lpEQpcmname = str(fs)+'/drc-X-'+ch+'_lp_'+resto+'.pcm'
if FRDpathname:
    mpEQpcmname = FRDpathname + "/" + mpEQpcmname
    lpEQpcmname = FRDpathname + "/" + lpEQpcmname

# Guardamos los FIR :
print "(i) Guardando los FIR de ecualización en '" + mpEQpcmname.split("/")[-1] \
       + "' '" + lpEQpcmname.split("/")[-1] + "'"

utils.savePCM32(imp,   mpEQpcmname)
utils.savePCM32(impLP, lpEQpcmname)

##########################################################################
# 5 PLOTEOS
##########################################################################

plt.axvline(fScho,              label='Schroeder', color='black', linestyle=':')

# Curva inicial sin suavizar:
plt.semilogx(freq, mag,
             label="raw response (" + str(len(mag)) + " bins)",
             color="silver", linestyle=":")

# Curva suavizada target:
plt.semilogx(freq, target,
             label="target (smoothed response)", color="blue")

# Cacho de curva usada para calcular el nivel de referencia:
if autoRef:
    plt.semilogx(freq[ f1_idx : f2_idx], rmag[ f1_idx : f2_idx ],
                 label="ref level range",
                 color="black", linestyle="--", linewidth=2)

# Curva de EQ para generar el FIR:
plt.semilogx(newFreq, newEq,
             label="EQ applied (" + str(len(newEq)) + " bins)",
             color="red")

title = FRDbasename + "\n(ref. level @ " + str(ref_level) + " dB --> 0 dB)"
plt.title(title)
plt.xlim(20, 20000)
plt.ylim(-30, 10)
plt.grid()
plt.legend()
plt.show()

##########################################################################
# 6 Guardamos las gráficas en un PDF:
##########################################################################
#pdfName = FRDname.replace('.frd', '_eq.pdf').replace('.txt', '_eq.pdf')
#print "\n(i) Guardando gráfica en el archivo " + pdfName
# evitamos los warnings del pdf
# C:\Python27\lib\site-packages\matplotlib\figure.py:1742: UserWarning:
# This figure includes Axes that are not compatible with tight_layout, so
# its results might be incorrect.
#import warnings
#warnings.filterwarnings("ignore")
#fig.savefig(pdfName, bbox_inches='tight')

##########################################################################
# 7 Visualización de los FIRs de EQ:
##########################################################################
if verFIRs:
    print "Veamos los FIR con audiotools/IRs_viewer.py ..."
    os.system("IRs_viewer.py '" + lpEQpcmname + "' '" + mpEQpcmname
              + "' 20-20000 -eq -1 " + str(int(fs)))

# FIN
