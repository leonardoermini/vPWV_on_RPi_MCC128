    
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(24, GPIO.OUT)  # triggger gonfiaggio valvola

#Funzione che avvia il gonfiaggio della valvola per il delivery dell'impulso pressorio
#GONFIAGGIO ---> connettore VALVOLA 2 (più esterno)
GPIO.output(24, True)
time.sleep(0.05)  # tempo accensione
GPIO.output(24, False) #fine gonfiaggio
