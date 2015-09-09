from PyQt4 import QtCore, QtGui, uic
import numpy as np
import pickle
app = QtGui.QApplication([])
import time, sys
from GalvoDriver import *
from GalvoGraphics import *
from threading import Timer
import fileinput
import serial.tools.list_ports

lasers = ('405 nm', '450 Guide')
available_ports = list(serial.tools.list_ports.comports())
arduino_port = 'COM4'

if 'daq' not in sys.argv and (arduino_port == '' or not any([arduino_port == p[0] for p in available_ports])):
	for p in available_ports:
		if 'Arduino' in p[1]:
			arduino_port = p[0]
			break
	for line in fileinput.input('galvo.py', inplace=1):
		if line.startswith('arduino_port = \''):
			print("arduino_port = '%s'" % arduino_port)
		else:
			print(line, end='')

def calibrate():
	global settings
	scene.reset()
	aimRect = QtCore.QRectF(ui.graphicsView.mapToScene(0, 0), ui.graphicsView.mapToScene(20, 20))
	aim = QtGui.QGraphicsRectItem(aimRect)
	aim.setBrush(QtGui.QColor(255, 0, 0))
	scene.addItem(aim)
	ui.infoLabel.setText('Resize the window, drag the laser to the top left corner, then press any key')
	scene.keyPressEvent = lambda ev: setattr(scene, 'tempRect', QtCore.QRectF(scene.galvo.pos, QtCore.QSizeF()))
	while not hasattr(scene, 'tempRect'):
		QtGui.qApp.processEvents()
		time.sleep(.01)

	aimRect.moveTo(ui.graphicsView.mapToScene(ui.graphicsView.width() - 20, ui.graphicsView.height() - 20))
	aim.setRect(aimRect)
	scene.keyPressEvent = lambda ev: scene.tempRect.setSize(QtCore.QSizeF(scene.galvo.pos.x() - scene.tempRect.x(), scene.galvo.pos.y() - scene.tempRect.y()))
	ui.infoLabel.setText('Now drag the laser to the bottom right and press any key')
	while scene.tempRect.isEmpty():
		QtGui.qApp.processEvents()
		time.sleep(.01)
	scene.removeItem(aim)
	scene.keyPressEvent = GalvoScene.keyPressEvent
	scene.galvo.setBounds(scene.tempRect)
	ui.infoLabel.setText('Calibrated, right click drag to position laser. Left click drag to draw ROIs')

def import_settings(fname):
	with open(fname, 'rb') as f:
		d = pickle.load(f)
	ui.setGeometry(*d['window'])
	scene.galvo.setBounds(QtCore.QRectF(d['galvo_x'], d['galvo_y'], d['galvo_width'], d['galvo_height']))
	scene.galvo.setLines({k: False for k in d['lasers']})
	scene.center()
	
def export_settings(fname):
	geom = ui.geometry()
	x = geom.x()
	y = geom.y()
	w = geom.width()
	h = geom.height()
	values = {'galvo_x': scene.galvo.boundRect.x(), 'galvo_y': scene.galvo.boundRect.y(), \
			'galvo_width': scene.galvo.boundRect.width(), 'galvo_height': scene.galvo.boundRect.height(),\
			'lasers': list(scene.galvo.lines.keys()), 'window': list([x, y, w, h])}
	with open(fname, 'wb') as f:
		pickle.dump(values, f)

def onOpen(ev):
	try:
		import_settings('settings.p')
	except Exception as e:
		print(e)

def onClose(ev):
	scene.galvo.stop()
	scene.galvo.penUp()
	if ui.actionAutosave.isChecked():
		export_settings('settings.p')
	sys.exit(0)

def startThread(duration = -1):	# called from manual, pulse, and continuous
	scene.crosshair.setVisible(False)
	if duration > 0:
		ui.continuousButton.setChecked(False)
	if any([shape.selected for shape in scene.getGalvoShapes()]):
		scene.galvo.draw_shapes([[scene.mapToGalvo(p) for p in shape.rasterPoints()] for shape in scene.getGalvoShapes() if shape.selected], duration)
	else:
		stopThread()

def stopThread():	# called on manual release, continuous unncheck
	scene.galvo.stop()
	if ui.continuousButton.isChecked():
		ui.continuousButton.setChecked(False)

def updateLasers():
	mi, ma = sorted(scene.galvo.lines)
	li = {mi: ui.laser1Button.isChecked(), ma: ui.laser2Button.isChecked()}
	scene.galvo.setLines(li)

def configure():
	old_lines = sorted(scene.galvo.lines.keys())	# get lines for lasers
	lines = {}
	for i, name in enumerate(lasers):
		result, ok = QtGui.QInputDialog.getItem(ui, "Port Select", "Select the port for %s. Currently at Line %d" % (name, old_lines[i]), ['Line %d' % i for i in range(16)], editable=False)
		if not ok:
			lines[old_lines[i]] = False
		else:
			lines[int(result[-1])] = False
	scene.galvo.setLines(lines)

def selectionChanged():
	ps = [[scene.mapToGalvo(p) for p in shape.rasterPoints()] for shape in scene.getGalvoShapes() if shape.selected]
	scene.galvo.setShapes(ps)
	if len(ps) == 0:
		stopThread()

def crosshairMoved(pos):
	if not scene.galvo.active:
		scene.galvo.penDown()
	ui.continuousButton.setChecked(False)

def lineRead(line):
	print(line)
	if ', ' in line:
		x, y = [float(i) for i in (line.split(', '))]
		p1 = scene.mapFromGalvo(QtCore.QPointF(x+.02, y))
		p2 = scene.mapFromGalvo(QtCore.QPointF(x-.02, y))
		cross1.setPos(p1)
		cross2.setPos(p2)
	else:
		if line[0] == '7':
			cross1.setVisible(line[-1] == '1')
		elif line[0] == '11':
			cross2.setVisible(line[-1] == '1')

cur_shape = None
ui = uic.loadUi('galvo.ui')
ui.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
ui.closeEvent = onClose
ui.showEvent = onOpen
if 'daq' in sys.argv:
	scene = GalvoScene()
else:
	scene = GalvoScene(port=arduino_port)
	##testing
	scene.galvo.lineRead.connect(lineRead)
	cross1 = CrossHair()
	cross2 = CrossHair()
	scene.addItem(cross1)
	#cross1.setVisible(False)
	scene.addItem(cross2)
	#cross2.setVisible(False)


scene.sigSelectionChanged.connect(selectionChanged)
scene.crosshair.sigMoved.connect(crosshairMoved)

ui.graphicsView.setScene(scene)
scene.setSceneRect(QtCore.QRectF(ui.graphicsView.rect()))

ui.calibrateButton.pressed.connect(calibrate)
ui.clearButton.pressed.connect(scene.clear)
ui.resetButton.pressed.connect(scene.reset)
ui.closeButton.pressed.connect(ui.close)

ui.manualButton.pressed.connect(startThread)
ui.manualButton.released.connect(stopThread)
ui.pulseButton.pressed.connect(lambda : startThread(ui.doubleSpinBox.value()))
ui.continuousButton.toggled.connect(lambda f: startThread() if f else stopThread())

ui.opacitySlider.valueChanged.connect(lambda v: ui.setWindowOpacity(v/100.))
ui.opacitySlider.setValue(50)
ui.laser1Button.toggled.connect(lambda f: updateLasers())
ui.laser1Button.setText(lasers[0])
ui.laser2Button.toggled.connect(lambda f: updateLasers())
ui.laser2Button.setText(lasers[1])

ui.actionConfigure.triggered.connect(configure)
ui.actionCalibrate.triggered.connect(calibrate)
ui.actionReset.triggered.connect(scene.reset)
ui.actionDisconnect.triggered.connect(lambda : sys.exit(0))
ui.actionImport.triggered.connect(lambda : import_settings(QtGui.QFileDialog.askOpenFilename(filter='Pickled files (*.p)')))
ui.actionExport.triggered.connect(lambda : export_settings(QtGui.QFileDialog.askSaveFilename(filter='Pickled files (*.p)')))

ui.show()
app.exec_()
