from PyQt4 import QtCore, QtGui, uic
import numpy as np
import pickle
app = QtGui.QApplication([])
import time, sys
from GalvoDriver import *
from GalvoGraphics import *
from threading import Timer

lasers = (Laser(name='450 Guide', pin=0), Laser('405 nm', pin=2))


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
	global lasers
	lasers = [Laser(*d['laser1']), Laser(*d['laser2'])]
	scene.galvo.setLasers(lasers)
	scene.center()
	
def export_settings(fname):
	geom = ui.geometry()
	x = geom.x()
	y = geom.y()
	w = geom.width()
	h = geom.height()
	values = {'galvo_x': scene.galvo.boundRect.x(), 'galvo_y': scene.galvo.boundRect.y(), \
			'galvo_width': scene.galvo.boundRect.width(), 'galvo_height': scene.galvo.boundRect.height(),\
			'laser1': (lasers[0].name, lasers[0].pin), 'laser2': (lasers[1].name, lasers[1].pin), 'window': list([x, y, w, h])}
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
	global lasers
	if ui.laser1Button.isChecked():
		lasers[0].activate()
	else:
		lasers[0].deactivate()
	if ui.laser2Button.isChecked():
		lasers[1].activate()
	else:
		lasers[1].deactivate()
	scene.galvo.setLasers(lasers)

def configure():
	old_lines = [l.name for l in lasers]	# get lines for lasers
	for i, laser in enumerate(lasers):
		result, ok = QtGui.QInputDialog.getItem(ui, "Pin Select", "Select the pin for %s. Currently at pin %d" % (laser.pin, old_lines[i]), ['Pin %d' % i for i in range(8)], editable=False)
		if ok:
			laser.changePin(int(result.split(' ')[0]))
	scene.galvo.setLasers(lasers)

def rename_lasers():
	global lasers
	result, ok = QtGui.QInputDialog.getText(ui, "Laser Name", "What is a name for laser 1?", text=lasers[0].name)
	if ok:
		lasers[0].rename(result)
		ui.laser1Button.setText(result)
	result, ok = QtGui.QInputDialog.getText(ui, "Laser Name", "What is a name for laser 2?", text=lasers[1].name)
	if ok:
		lasers[1].rename(result)
		ui.laser2Button.setText(result)
	
def selectionChanged():
	ps = [[scene.mapToGalvo(p) for p in shape.rasterPoints()] for shape in scene.getGalvoShapes() if shape.selected]
	scene.galvo.setShapes(ps)
	if len(ps) == 0:
		stopThread()

def crosshairMoved(pos):
	if not scene.galvo.active:
		scene.galvo.penDown()
	ui.continuousButton.setChecked(False)

def changeRasterShift():
	result, ok = QtGui.QInputDialog.getInt(ui, "Raster Shift", "Enter the shift in pixels to translate the laser when rastering polygons:", GalvoShape.RASTER_GAP, min=0)
	if ok:
		GalvoShape.RASTER_GAP = result

cur_shape = None
ui = uic.loadUi('galvo.ui')
ui.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
ui.closeEvent = onClose
ui.showEvent = onOpen
scene = GalvoScene(lasers)


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
ui.opacitySlider.setValue(85)
ui.laser1Button.toggled.connect(lambda f: updateLasers())
ui.laser1Button.setText(lasers[0].name)
ui.laser2Button.toggled.connect(lambda f: updateLasers())
ui.laser2Button.setText(lasers[1].name)

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
