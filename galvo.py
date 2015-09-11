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
	scene.galvo.lasers[0].rename(d['laser1'][0])
	scene.galvo.lasers[0].changePin(d['laser1'][1])
	scene.galvo.lasers[1].rename(d['laser2'][0])
	scene.galvo.lasers[1].changePin(d['laser2'][1])
	scene.center()
	
def export_settings(fname):
	geom = ui.geometry()
	x = geom.x()
	y = geom.y()
	w = geom.width()
	h = geom.height()
	values = {'galvo_x': scene.galvo.boundRect.x(), 'galvo_y': scene.galvo.boundRect.y(), \
			'galvo_width': scene.galvo.boundRect.width(), 'galvo_height': scene.galvo.boundRect.height(),\
			'laser1': (scene.galvo.lasers[0].name, scene.galvo.lasers[0].pin), 'laser2': (scene.galvo.lasers[1].name, scene.galvo.lasers[1].pin), 'window': list([x, y, w, h])}
	with open(fname, 'wb') as f:
		pickle.dump(values, f)

def onOpen(ev):
	try:
		import_settings('settings.p')
	except Exception as e:
		print(e)

def onClose(ev):
	scene.galvo.penUp()
	if ui.actionAutosave.isChecked():
		export_settings('settings.p')
	sys.exit(0)

def pulsePressed():
	if ui.continuousButton.isChecked():
		ui.continuousButton.setChecked(False)
	startThread()
	Timer(ui.doubleSpinBox.value(), stopThread).start()

def startThread():
	ps = [[scene.mapToGalvo(p) for p in shape.rasterPoints()] for shape in scene.getGalvoShapes() if shape.selected]
	scene.galvo.setShapes(ps)
	scene.galvo.penDown()
	if len(ps) > 0:	# run thread to draw shapes
		scene.galvo.start()
	
def stopThread():	# called on manual release, continuous unncheck
	scene.galvo.penUp()
	if ui.continuousButton.isChecked():
		ui.continuousButton.setChecked(False)

def configure():
	for laser in scene.galvo.lasers:
		result, ok = QtGui.QInputDialog.getItem(ui, "Pin Select", "Select the pin for %s. Currently at pin %d" % (laser.name, laser.pin), ['Pin %d' % i for i in range(8)], editable=False)
		if ok:
			laser.changePin(int(result.split(' ')[1]))

def rename_lasers():
	for i, laser in enumerate(scene.galvo.lasers):
		result, ok = QtGui.QInputDialog.getText(ui, "Laser Name", "What is a name for laser %d?" % i, text=laser.name)
		if ok:
			laser.rename(result)
	
def selectionChanged():
	if not any([shape.selected for shape in scene.getGalvoShapes()]):
		scene.galvo.active = False
		while scene.galvo.isRunning():
			pass
		if ui.continuousButton.isChecked():
			scene.galvo.setShapes([])
			scene.galvo.penDown()
		scene.crosshair.setVisible(True)
	else:
		if scene.galvo.active and not scene.galvo.isRunning():
			startThread()
		scene.crosshair.setVisible(False)

def changeRasterShift():
	result, ok = QtGui.QInputDialog.getInt(ui, "Raster Shift", "Enter the shift in pixels to translate the laser when rastering polygons:", GalvoShape.RASTER_GAP, min=0)
	if ok:
		GalvoShape.RASTER_GAP = result

cur_shape = None
ui = uic.loadUi('galvo.ui')
ui.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
ui.closeEvent = onClose
ui.showEvent = onOpen
scene = GalvoScene()
scene.galvo.lasers[0].sigRenamed.connect(ui.laser1Button.setText)
scene.galvo.lasers[1].sigRenamed.connect(ui.laser2Button.setText)

scene.sigSelectionChanged.connect(selectionChanged)

ui.graphicsView.setScene(scene)
scene.setSceneRect(QtCore.QRectF(ui.graphicsView.rect()))

ui.calibrateButton.pressed.connect(calibrate)
ui.clearButton.pressed.connect(scene.clear)
ui.resetButton.pressed.connect(scene.reset)
ui.closeButton.pressed.connect(ui.close)

ui.manualButton.pressed.connect(startThread)
ui.manualButton.released.connect(stopThread)
ui.pulseButton.pressed.connect(pulsePressed)
ui.continuousButton.toggled.connect(lambda f: startThread() if f else stopThread())

ui.opacitySlider.valueChanged.connect(lambda v: ui.setWindowOpacity(v/100.))
ui.opacitySlider.setValue(85)
ui.laser1Button.toggled.connect(lambda f: scene.galvo.lasers[0].setActive(ui.laser1Button.isChecked()))
ui.laser2Button.toggled.connect(lambda f: scene.galvo.lasers[1].setActive(ui.laser2Button.isChecked()))

ui.actionConfigure.triggered.connect(configure)
ui.actionCalibrate.triggered.connect(calibrate)
ui.actionReset.triggered.connect(scene.reset)
ui.actionRename.triggered.connect(rename_lasers)
ui.actionEditRaster.triggered.connect(changeRasterShift)
ui.actionDisconnect.triggered.connect(lambda : sys.exit(0))
ui.actionImport.triggered.connect(lambda : import_settings(QtGui.QFileDialog.askOpenFilename(filter='Pickled files (*.p)')))
ui.actionExport.triggered.connect(lambda : export_settings(QtGui.QFileDialog.askSaveFilename(filter='Pickled files (*.p)')))

ui.show()
app.exec_()
