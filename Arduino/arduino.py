from serial_ports import *
import fileinput
from PyQt4 import QtCore, QtGui
app = QtGui.QApplication([])

port = 'COM3'

def getNewPort():
	ports = serial_ports()
	if len(ports) > 1:
		port, ok = QtGui.QInputDialog.getItem(None, 'Port Select', 'Select a port from the available ports', ports)
		if not ok:
			raise Exception('Selection cancelled')
	elif len(ports) == 1:
		port = ports[0]
	else:
		raise Exception("No available serial ports found. Is the device connected?")
	return port

if port == '':
	port = getNewPort()
	for line in fileinput.input('arduino.py', inplace=1):
		if line.startswith('port = \''):
			print("port = '%s'" % port)
		else:
			print(line, end='')

import time

ser = serial.Serial(port, 9600)
time.sleep(2)
#The following line is for serial over GPIO
i = 0

while (i < 4):
    # Serial write section

    setTempCar1 = 63
    setTempCar2 = 37
    ser.flush()
    setTemp1 = str(setTempCar1).encode('utf-8')
    setTemp2 = str(setTempCar2).encode('utf-8')
    print ("Sent: %s" % setTemp1)
    ser.write(setTemp1)
    time.sleep(1)

    # Serial read section
    msg = ser.read(ser.inWaiting())
    print ("Received: %s" % msg)
    i = i + 1
else:
    print("Exiting")

