import cv2
import face_recognition as fr
import os
import numpy as np
from datetime import datetime
import time as t
import imutils as im
import RPi.GPIO as GPIO
from rpi_lcd import LCD

# Modo de configuración de los pines del Raspberry Pi
GPIO.setmode(GPIO.BOARD)

# Deshabilitar las advertencias
GPIO.setwarnings(False)

# Configurar el modo de los pines (entradas o salidas)
GPIO.setup(16, GPIO.IN) 
GPIO.setup(18, GPIO.OUT) 

# Crear un objeto de tipo LCD
lcd = LCD()

# Crear base de datos
ruta = '/home/mecatronicaunt2022/Desktop/Registro_Personal/registro/media/Fotos'
mis_imagenes = []
nombres_personal = []
lista_personal = os.listdir(ruta)

for nombre in lista_personal:
    imagen_actual = cv2.imread(f'{ruta}/{nombre}')
    esc = 354/imagen_actual.shape[0]
    w = 354
    h = int(imagen_actual.shape[1]*esc)
    imagen_actual = im.resize(imagen_actual, width=w, height=h)
    mis_imagenes.append(imagen_actual)
    nombres_personal.append(os.path.splitext(nombre)[0])

print('Lista del personal autorizado: ', nombres_personal)

global escala
escala = 0.5

# Codificar imágenes
def codificar(imagenes):

    # Crear una lista nueva
    lista_codificada = []

    # Pasar todas la im|ágenes a rgb
    for imagen in imagenes:
        imagen = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)

        #Redimensionar imagen
        w = int(imagen.shape[0]*escala)
        h = int(imagen.shape[1]*escala)
        imagen = im.resize(imagen, width=w, height=h)

        # Girar imagen desde el eje vertical
        imagen= cv2.flip(imagen, 1)

        # Codificar
        codificado = fr.face_encodings(imagen)[0]

        # Agregar a la lista
        lista_codificada.append(codificado)

    # Devolver lista codificada
    return lista_codificada

# Registrar los ingresos
def registrar_ingresos(persona):
    f = open('/home/mecatronicaunt2022/Desktop/Proyecto 2.0/registro.csv', 'r+')
    lista_datos = f.readlines()
    #nombre_registro = []
    #for linea in lista_datos:
        #ingreso = linea.split(',')
        #nombre_registro.append(ingreso[0])

    #if persona not in nombre_registro:
    ahora = datetime.now()
    string_ahora = ahora.strftime('%H:%M:%S')
    f.writelines(f'\n{persona}, {string_ahora}')

# Mostrar texto en la pantalla LCD
def LCD_Text(text_1,text_2):
        lcd.text(text_1, 1)
        lcd.text(text_2, 2)
        
lista_personal_codificada = codificar(mis_imagenes)

# Tomar una imagen de la cámara
captura = cv2.VideoCapture(0,cv2.CAP_ANY)

# Inicializar variables
sensor_puerta = True
ingreso_personal = []
Aux = True
desc = False
wait = False
persona_detectada = False

while True:
    # Lectura del sensor interruptor de la puerta
    sensor_puerta = GPIO.input(16)
    if desc == False:
        if sensor_puerta == False:
            print('Puerta Cerrada')
            if Aux:
                try:
                    LCD_Text('  BIENVENIDO A', '   MULTIUSOS')
                except OSError:
                    break
                Aux = False 
        else:
            print('Puerta Abierta')
            try:
                LCD_Text('    PUERTA', '    ABIERTA')
            except OSError:
                break
            Aux = True 

    # Leer imagen de la cámara
    exito, imagen = captura.read()

    # Redimensionar imagen de la camara
    w = int(imagen.shape[0]*escala)
    h = int(imagen.shape[1]*escala)
    imagen = im.resize(imagen, width=w, height=h)

    # Girar imagen desde el eje vertical
    imagen = cv2.flip(imagen, 1)

    if not exito:
        print('No se ha podido tomar la captura')
        break
    else:
        # Reconocimiento Facial y Accionamiento del Servo
        if persona_detectada == False and sensor_puerta == False:
            t1 = t.time()
            # Reconocer cara en captura
            cara_captura = fr.face_locations(imagen)
            t2 = t.time()
            print('t_locations = ',t2-t1)
            
            if cara_captura == []:
                desc = False
            
            t1 = t.time()
            # Codificar cara captura
            cara_captura_codificada = fr.face_encodings(imagen, cara_captura)
            t2 = t.time()
            print('t_encodings',t2-t1)

            # Buscar coincidencias
            for caracodif, caraubic in zip(cara_captura_codificada, cara_captura):
                
                coincidencias = fr.compare_faces(lista_personal_codificada, caracodif)
                distancias = fr.face_distance(lista_personal_codificada, caracodif)
                print(distancias)

                indice_coincidencia = np.argmin(distancias)
                print(distancias[indice_coincidencia])
                
                # Dibujar recuadro de detección de rostro
                y1, x2, y2, x1 = caraubic
                cv2.rectangle(imagen, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Mostrar coincidencias si las halla
                if distancias[indice_coincidencia] < 0.55:
                    # Indicar que es desconocido
                    cv2.putText(imagen, 'Desconocido', (x1 + 6, y2 - 6), 2, 0.4, (0, 255, 0), 1)
                    print('Usted no es personal autorizado')
                    
                    try:
                        LCD_Text(' DESCONOCIDO,', 'ACCESO DENEGADO')
                    except OSError:
                        break
                    
                    desc = True
                    Aux = True 

                else:
                    desc = False
                    # Buscar el nombre del personal encontrado
                    nombre = nombres_personal[indice_coincidencia]

                    cv2.putText(imagen, nombre, (x1 + 6, y2 - 6), 2, 0.4, (0, 255, 0), 1)

                    #if nombre not in ingreso_personal:
                    if wait==False:
                        # Agrega una persona autorizada en la lista del personal
                        ingreso_personal.append(nombre)
                        print(ingreso_personal)

                        # Enviar un 1 al relé
                        GPIO.output(18, True)
                        print('Chapa activada')
                        
                        #registrar_ingresos(nombre)
                        print('Ingresó: ',nombre)
                        
                        try:
                            LCD_Text(' PUEDE INGRESAR', ' ' + nombre)
                            #registrar_ingresos(nombre)
                        except OSError:
                            break
                        
                        # Un segundo de activación de la cerradura eléctrica
                        t.sleep(0.55)
                        
                        try:
                            registrar_ingresos(nombre)
                            LCD_Text(' EMPUJE Y JALE', '   LA PUERTA')
                            
                        except OSError:
                            break

                        # Enviar un 0 al relé
                        GPIO.output(18, False)
                        t.sleep(4)
                        print('Chapa desactivada')
                        
                        persona_detectada = True
                        wait = True
                        Aux = True
                    else:
                        wait = False
                        print('Chapa desactivada')
                        print('\n')
                    #else:
                        # Remover a la persona que esta en la lista del personal que ingresó
                        #ingreso_personal.remove(nombre)
                        #print(ingreso_personal)
                        #print('Salió: ', nombre )

                        #try:
                            #LCD_Text(' ' + nombre, '     SALIO')
                        #except OSError:
                            #break

                        # Esperar 6 segundos
                        #t.sleep(6)
                        #Aux = True
                        
        elif sensor_puerta == True:
            persona_detectada = False
                    
        # Mostrar imagen obtenida
        cv2.imshow('Reconocimiento Facial', imagen)

        # Mantener ventana abierta
        key=cv2.waitKey(1)

        # Cerrar con el boton 'q'
        if key==ord('q') or key==ord('Q'):
            break
        
# Limpiar LCD
try:
    lcd.clear()
except OSError:
    pass

# Apagar la cámara
captura.release()

# Destruir todas las vetanas abiertas
cv2.destroyAllWindows()





















































