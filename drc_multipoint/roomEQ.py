#!/usr/bin/env python3
"""
    roomEQ.py

    Calcula un FIR para ecualizar la respuesta de una sala.

    Uso:

        roomEQ.py respuesta.frd  -fs=xxxxx  [ -e=XX -ref=XX  -scho=XX  -doFIR -plot ]

        -fs=    fs del FIR de salida, por defecto 48000 (Hz)

        -e=     Longitud del FIR en taps 2^XX. Por defecto 2^15, es decir,
                32 Ktaps con resolución de 16K bins sobre la fs.

        -ref=   Nivel de referencia en XX dB (autodetectado por defecto)

        -scho=  Frecuencia de Schroeder (por defecto 200 Hz)

        -doFIR  Genera FIRs después de estimar el target y la EQ de sala.

        -plot   Visualiza los impulsos FIR generados

        -dev    Gráficas auxiliares sobre la EQ


    NOTA: se necesita  github.com/AudioHumLab/audiotools

"""
#
# v0.1a
#   - Nombrado de archivos de salida para FIRtro
#   - Muestra la correspondencia del nivel de referencia estimado en el gráfico
# v0.1b
#   - Longitud del FIR y nivel de referencia en command line.
#   - Revisión del cómputo del FIR
# v0.1c python3

##########################################################################
# IMPORTA MODULOS
##########################################################################
# Para que este script pueda estar fuera de ~/audiotools
import os
import sys
HOME = os.path.expanduser("~")
sys.path.append(HOME + "/audiotools")
import tools
import pydsd
from smoothSpectrum import smoothSpectrum as smooth

# Módulos estandar
import numpy as np
from scipy import signal
from matplotlib import pyplot as plt
from matplotlib.ticker import EngFormatter


##########################################################################
# AJUSTES POR DEFECTO:
##########################################################################

# Solo calcula el target y la curva de EQ, no genera los FIR
noFIRs  = True

# Para developers, muestra gráficas relativas al cálculo del target
dev = False

# Salida:
m       = 2**15     # Longitud del FIR por defecto 2^15 = 32 Ktaps (resolución 16K bins)
fs      = 48000     # fs del FIR de salida
verFIRs = False

# Nivel de referencia:
autoRef = True
f1, f2  = 500, 2000 # Rango de frecs. para decidir el nivel de referencia

# TARGET sobre la curva .frd original
Noct    = 96        # Suavizado fino inicial 1/96 oct
fScho   = 200       # Frec de Schroeder
octScho = 2         # Octavas respecto a la freq. Schoeder para iniciar
                    # la transición de suavizado fino hacia 1/1 oct
Tspeed  = "medium"  # Velocidad de transición del suavizado audiotools/smoothSpectrum.py

##########################################################################
# 0 LEE ARGUMENTOS
##########################################################################

if len(sys.argv) == 1:
    print(__doc__)
    sys.exit()

for opc in sys.argv[1:]:

    if opc[0] != '-' and opc[-4:] in ('.frd','.txt'):
        FRDname = opc
        # Lee el contenido del archivo .frd
        FR, fs_FRD = tools.readFRD(FRDname)
        freq = FR[:, 0]     # >>>> vector de frecuencias <<<<
        mag  = FR[:, 1]     # >>>> vector de magnitudes  <<<<

    elif opc[:4] == '-fs=':
        if opc[4:] in ('44100', '48000', '96000'):
            fs = int(opc[4:])
        else:
            print( "fs debe ser 44100 | 48000 | 96000" )
            sys.exit()

    elif opc[:3] == '-e=':
        if opc[3:] in ('12', '13', '14', '15', '16'):
            m = 2**int(opc[3:])
        else:
            print( "m: 12...16 (4K...64K taps)" )
            sys.exit()

    elif opc[:5] == '-ref=':
        try:
            ref_level = opc[5:]
            ref_level = round( float(ref_level), 1)
            autoRef = False
        except:
            print( __doc__ )
            sys.exit()

    elif opc[:6] == '-scho=':
        try:
            fScho = float(opc[6:])
        except:
            print( __doc__ )
            sys.exit()

    elif '-v' in opc:
        verFIRs = True

    elif '-doFIR' in opc:
        noFIRs = False

    elif '-dev' in opc:
        dev = True

    else:
        print( __doc__ )
        sys.exit()

# Auxiliares para manejar los archivos de salida y para printados:
FRDbasename = FRDname.split("/")[-1]
FRDpathname = "/".join(FRDname.split("/")[:-1])

# Información fs
if fs == fs_FRD:
    print( "(i) fs=" + str(fs) + " coincide con la indicada en " + FRDbasename )
else:
    print( "(i) fs=" + str(fs) +  " distinta de " + str(fs_FRD) + " en " + FRDbasename )

# Información de la resolución
print( "(i) bins leidos:", len(freq), ", bins del EQ:", m/2 )
if (m/2) / len(freq) > 1:
    print( "(!) La longitud m=2^" + str(int(np.log2(m))) \
           + " EXCEDE la resolución original de " + FRDbasename)

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
    print( "(i) Nivel de referencia estimado: " +  str(ref_level) + " dB --> 0 dB" )
else:
    print( "(i) Nivel de referencia: " +  str(ref_level) + " dB --> 0 dB" )

# 1.2 Curva 'target': será una versión suavizada de la respuesta .frd de la sala:
# 'f0': freq a la que empezamos a suavizar más hasta llegar a 1/1 oct en Nyquist
f0 = 2**(-octScho) * fScho
# 'Noct': suavizado fino inicial en graves (por defecto 1/48 oct)
# 'Tspeed': velocidad de transición del suavizado audiotools/smoothSpectrum.py
print( "(i) Suavizando la respuesta para calcular el target" )
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
# Nótese que ahora 'eq' tiene unas transiciones abruptas en 0 dB debidas al recorte,
# limamos asperezas:

# Versión suavizada de 'eq' de la que nos interesa solo el suavizado superior
eqaux = smooth(freq, eq, Noct=12) # Noct=12 parece el valor más adecuado.

# Actualizamos 'eq' con los valores altos de 'eqaux', de manera que
# respetemos los valles profundos y suavizamos solo las transiciones de np.clip
np.copyto( eq, eqaux, where=(eqaux > -3.0) )

##########################################################################
# 3. Computamos el FIR de salida que usaremos en el convolver.
#    dom. de la freq ---( IFFT )---> dom. del tiempo
##########################################################################

##########################################################################
# 3.1 Interpolamos la curva 'eq' para adaptarnos a la longitud 'm'
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
print( "(i) Interpolando espectro para m = " + tools.Ktaps(m) + " @ " + str(fs) + " Hz" )
newFreq, newEq = pydsd.lininterp(freq, eq, m, fs)

# 3.2 Comprobamos que sea ODD
if len(newEq) % 2 == 0:
    raise ValueError("(!) Algo va mal debería ser un semiespectro ODD: " + str(len(newEq)))
    sys.exit()

# 3.3 Traducimos dBs --> linear
newEqlin = 10.0**(newEq/20.0)

# 3.4 Computamos el impulso calculando la IFFT de la curva 'newEq'.
#     OjO nuestra curva semiespectro 'newEq' es una abstracción reducida a magnitudes
#     de freqs positivas, pero la IFFT necesita un espectro causal (con phase minima)
#     y completo (freqs positivas y negativas)
wholespectrum = pydsd.minphsp( pydsd.wholespmp(newEqlin) ) # Ahora ya tiene phase
# dom.F --> dom.T y enventanado
imp = np.real( np.fft.ifft( wholespectrum ) )
imp = pydsd.semiblackmanharris(m) * imp[:m]

# Ahora 'imp' tiene una respuesta causal, natural, o sea de phase mínima.

# 3.5 Versión linear-phase (experimental)
impLP = tools.MP2LP(imp, windowed=True, kaiserBeta=1)

##########################################################################
# 4 PLOTEOS
##########################################################################

plt.rcParams.update({'font.size': 8})
fig, ax = plt.subplots( figsize=(9, 4.5) )    # in inches wide aspect

ax.set_xscale('log')

ax.grid(True, which='both', axis='x')
ax.grid(True, which='major', axis='y')

ax.set_xlim(20, 20000)

# Gráficas auxiliares de la EQ (solo si opc -dev)
if dev:

    ax.axvline(fScho, label='Schroeder', color='black', linestyle=':')

    ax.axvline (f0, label='f0 = -' + str(octScho) + ' oct vs Schroeder',
                    color='orange', linestyle=':', linewidth=1)

    ax.semilogx(freq, eqaux,
                 label='eqaux', linestyle=':', color='purple')

# Curva inicial sin suavizar:
ax.semilogx(freq, mag,
             label="raw response (" + str(len(mag)) + " bins)",
             color="silver", linestyle=":", linewidth=.5)

# Curva suavizada target:
ax.semilogx(freq, target,
             label="target (smoothed response)",
             color="blue", linestyle='-')

# Curva de EQ para generar el FIR:
ax.semilogx(newFreq, newEq,
             label="EQ applied (" + str(len(newEq)-1) + " bins)",
             color="red")

# Curva resultado estimada:
if dev:
    ax.semilogx(freq, (target + eq),
                 label='estimated result', color='green', linewidth=1.5)

# Cacho de curva usada para calcular el nivel de referencia:
if autoRef:
    ax.semilogx(freq[ f1_idx : f2_idx], rmag[ f1_idx : f2_idx ],
                 label="range to estimate ref level",
                 color="black", linestyle="--", linewidth=2)

title = FRDbasename + "\n(ref. level @ " + str(ref_level) + " dB --> 0 dB)"

# Nice engineering formatting "1 K"
ax.xaxis.set_major_formatter( EngFormatter() )
ax.xaxis.set_minor_formatter( EngFormatter() )

# Rotate_labels for both major and minor xticks
for label in ax.get_xticklabels(which='both'):
    label.set_rotation(70)
    label.set_horizontalalignment('center')

plt.title(title)

plt.show()

##########################################################################
# 5 Guardamos las gráficas en un PDF:
##########################################################################
#pdfName = FRDname.replace('.frd', '_eq.pdf').replace('.txt', '_eq.pdf')
#print( "\n(i) Guardando gráfica en el archivo " + pdfName )
# evitamos los warnings del pdf
# C:\Python27\lib\site-packages\matplotlib\figure.py:1742: UserWarning:
# This figure includes Axes that are not compatible with tight_layout, so
# its results might be incorrect.
#import warnings
#warnings.filterwarnings("ignore")
#fig.savefig(pdfName, bbox_inches='tight')

##########################################################################
# 6 Guardamos los impulsos en archivos .pcm
##########################################################################
if noFIRs:
    print( "(i) No se generan FIRs. Bye!" )
    sys.exit()

# Separamos los FIR de salida en un directorio indicativo de la fs y la longitud en taps:

if FRDpathname:
    dirSal = f'{FRDpathname}/{str(fs)}_{tools.Ktaps(m).replace(" ","")}'
else:
    dirSal = f'{str(fs)}_{tools.Ktaps(m).replace(" ","")}'
os.system("mkdir -p " + dirSal)

# Indicativo del canal para el nombre del .pcm de salida
ch = 'C'
if FRDbasename[0].upper() in ('L','R'):
    ch = FRDbasename[0].upper()
mpEQpcmname = f'{dirSal}/drc.{ch}_mp.pcm'
lpEQpcmname = f'{dirSal}/drc.{ch}_lp.pcm'

# Guardamos los FIR :
print( "(i) Guardando los FIR de ecualización:" )
print( "    " + str(fs) + "_" + tools.Ktaps(m).replace(' ','') + "/" + mpEQpcmname.split("/")[-1] )
print( "    " + str(fs) + "_" + tools.Ktaps(m).replace(' ','')+ "/" + lpEQpcmname.split("/")[-1] )

tools.savePCM32(imp,   mpEQpcmname)
tools.savePCM32(impLP, lpEQpcmname)


##########################################################################
# 7 Visualización de los FIRs de EQ:
##########################################################################
if verFIRs:
    print( "Veamos los FIR con audiotools/IRs_viewer.py ..." )
    os.system("IRs_viewer.py '" + lpEQpcmname + "' '" + mpEQpcmname
              + "' 20-20000 -eq -1 " + str(int(fs)))

# FIN
