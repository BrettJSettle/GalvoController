from PyQt4 import QtCore, QtGui, uic
import numpy as np
import pickle
app = QtGui.QApplication([])
import time, sys
from GalvoDriver import *
from GalvoGraphics import *
from threading import Timer

def calibrate():
	global settings
	scene.reset()
	aimRect = QtCore.QRectF(ui.graphicsView.mapToScene(0, 0), ui.graphicsView.mapToScene(20, 20))
	aim = QtGui.QGraphicsRectItem(aimRect)
	aim.setBrush(QtGui.QColor(255, 0, 0))
	scene.addItem(aim)
	ui.infoLabel.setText('Resize the window, drag the laser to the top left corner, then press any key')
	ui.keyPressEvent = lambda ev: setattr(scene, 'tempRect', QtCore.QRectF(scene.galvo.pos, QtCore.QSizeF()))
	while not hasattr(scene, 'tempRect'):
		QtGui.qApp.processEvents()
		time.sleep(.01)

	aimRect.moveTo(ui.graphicsView.mapToScene(ui.graphicsView.width() - 20, ui.graphicsView.height() - 20))
	aim.setRect(aimRect)
	ui.keyPressEvent = lambda ev: scene.tempRect.setSize(QtCore.QSizeF(scene.galvo.pos.x() - scene.tempRect.x(), scene.galvo.pos.y() - scene.tempRect.y()))
	ui.infoLabel.setText('Now drag the laser to the bottom right and press any key')
	while scene.tempRect.isEmpty():
		QtGui.qApp.processEvents()
		time.sleep(.01)
	scene.removeItem(aim)
	ui.keyPressEvent = keyPressEvent
	scene.galvo.setBounds(scene.tempRect)
	ui.infoLabel.setText('Calibrated, drag crosshair to position laser. Right click to translate crosshair')

def import_settings(fname):
	with open(fname, 'rb') as f:
		d = pickle.load(f)
	scene.galvo.setBounds(QtCore.QRectF(d['galvo_x'], d['galvo_y'], d['galvo_width'], d['galvo_height']))
	scene.galvo.setLines({k: False for k in d['lasers']})

def export_settings(fname):
	values = {'galvo_x': scene.galvo.boundRect.x(), 'galvo_y': scene.galvo.boundRect.y(), \
			'galvo_width': scene.galvo.boundRect.width(), 'galvo_height': scene.galvo.boundRect.height(),\
			'lasers': list(scene.galvo.lines.keys())}
	with open(fname, 'wb') as f:
		pickle.dump(values, f)

def onOpen(ev):
	try:
		import_settings('settings.p')
	except Exception as e:
		print(e)

def onClose(ev):
	scene.galvo.deactivateLasers()
	if ui.actionAutosave.isChecked():
		export_settings('settings.p')
	sys.exit(0)

def mousePressEvent(ev):
	global cur_shape, thread

	if thread.isRunning():	#stop drawing the shape
		stopThread()

	if ev.button() == QtCore.Qt.LeftButton:
		if not scene.crosshair.isVisible():
			scene.crosshair.show()
		GalvoScene.mousePressEvent(scene, ev)

	elif ev.button() == QtCore.Qt.RightButton:
		pos = ev.scenePos()
		toggled = False
		for sh in scene.shapes():
			if sh.mouseIsOver:
				sh.toggle()
				toggled = True
			elif int(ev.modifiers()) != QtCore.Qt.ControlModifier and sh.selected:
				sh.toggle()
				toggled = True
		if not toggled:
			cur_shape = GalvoShape(pos)
			scene.addItem(cur_shape)

def keyPressEvent(ev):
	if ev.key() == 16777223:
		for sh in scene.shapes()[::-1]:
			if sh.selected:
				scene.removeItem(sh)

def mouseMoveEvent(ev):
	if cur_shape != None:
		cur_shape.addPoint(ev.scenePos())
	else:
		for sh in scene.shapes():
			sh.mouseOver(ev.scenePos())
	GalvoScene.mouseMoveEvent(scene, ev)

def mouseReleaseEvent(ev):
	global cur_shape
	if cur_shape != None:
		cur_shape.close()
		cur_shape = None
	GalvoScene.mouseReleaseEvent(scene, ev)

def startThread(duration = -1):
	scene.crosshair.setVisible(False)
	thread.setDuration(duration)
	thread.drawing = True
	thread.setPoints([[scene.mapToGalvo(p) for p in shape.rasterPoints()] for shape in scene.shapes() if shape.selected])
	thread.start()

def stopThread():
	global thread
	thread.stop()
	scene.crosshair.setVisible(True)
	if ui.continuousButton.isChecked():
		ui.continuousButton.setChecked(False)

def updateLasers():
	mi, ma = sorted(scene.galvo.lines)
	li = {mi: ui.laser1Button.isChecked(), ma: ui.laser2Button.isChecked()}
	scene.galvo.setLines(li)

def configure():
	old_lines = sorted(scene.galvo.lines.keys())	# get lines for lasers
	lines = {}
	for i in range(2):
		result, ok = QtGui.QInputDialog.getItem(ui, "Port Select", "Select the port for Laser 1", ['Line %d' % i for i in range(8)], editable=False)
		if not ok:
			lines[old_lines[i]] = False
		else:
			lines[int(result[-1])] = False
	scene.galvo.setLines(lines)

cur_shape = None
ui = uic.loadUi('galvo.ui')
ui.closeEvent = onClose
ui.showEvent = onOpen
scene = GalvoScene()
thread = ShapeThread(scene.galvo)
scene.mousePressEvent = mousePressEvent
scene.mouseMoveEvent = mouseMoveEvent
scene.mouseReleaseEvent = mouseReleaseEvent
scene.shapes = lambda : [i for i in scene.items() if isinstance(i, GalvoShape)]
ui.keyPressEvent = keyPressEvent

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
ui.laser1Button.toggled.connect(lambda f: updateLasers())
ui.laser2Button.toggled.connect(lambda f: updateLasers())

ui.configureAction.triggered.connect(configure)
ui.actionCalibrate.triggered.connect(calibrate)
ui.actionReset.triggered.connect(scene.reset)
ui.actionDisconnect.triggered.connect(lambda : sys.exit(0))
ui.actionImport.triggered.connect(lambda : import_settings(QtGui.QFileDialog.askOpenFilename(filter='Pickled files (*.p)')))
ui.actionExport.triggered.connect(lambda : export_settings(QtGui.QFileDialog.askSaveFilename(filter='Pickled files (*.p)')))

ui.show()
app.exec_()
