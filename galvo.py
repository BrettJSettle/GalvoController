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
	font = QtGui.QFont("Helvetica", 24, 3)
	ti = scene.addText('Position the laser in optimal top\n   left, then press any key', font = font)
	scene.keyPressEvent = lambda ev: setattr(scene, 'tempRect', QtCore.QRectF(scene.galvo.pos, QtCore.QSizeF()))
	while not hasattr(scene, 'tempRect'):
		QtGui.qApp.processEvents()
		time.sleep(.01)

	aimRect.moveTo(ui.graphicsView.mapToScene(ui.graphicsView.width() - 20, ui.graphicsView.height() - 20))
	aim.setRect(aimRect)
	scene.keyPressEvent = lambda ev: scene.tempRect.setSize(QtCore.QSizeF(scene.galvo.pos.x() - scene.tempRect.x(), scene.galvo.pos.y() - scene.tempRect.y()))
	ti.setText('Now position the laser in optimal bottom right, and press a key')
	while scene.tempRect.isEmpty():
		QtGui.qApp.processEvents()
		time.sleep(.01)
	scene.removeItem(aim)
	scene.keyPressEvent = GalvoScene.keyPressEvent
	scene.galvo.setBounds(scene.tempRect)
	del scene.tempRect
	scene.removeItem(ti)#('Calibrated, right click drag to position laser. Left click drag to draw ROIs')

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
	scene.galvo.setLaserActive(0, False)
	scene.galvo.setLaserActive(1, False)
	if ui.actionAutosave.isChecked():
		export_settings('settings.p')
	sys.exit(0)

def pulsePressed(num):
	scene.galvo.setLaserActive(num, True)
	val = ui.pulseSpin.value() if num == 0 else ui.pulse2Spin.value()
	Timer(val, lambda : scene.galvo.setLaserActive(num, False)).start()

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
	ps = [[scene.mapToGalvo(p) for p in shape.rasterPoints()] for shape in scene.getGalvoShapes() if shape.selected]
	scene.galvo.setShapes(ps)
	scene.crosshair.setVisible(not any([shape.selected for shape in scene.getGalvoShapes()]))

def changeRasterShift():
	result, ok = QtGui.QInputDialog.getInt(ui, "Raster Shift", "Enter the shift in pixels to translate the laser when rastering polygons:", GalvoShape.RASTER_GAP, min=0)
	if ok:
		GalvoShape.RASTER_GAP = result

def traceLine():
	l = [shape for shape in scene.getGalvoShapes() if shape.selected and not isinstance(shape, GalvoShape)]
	if len(l) > 1:
		print("Can only draw one line at a time")
		return
	scene.galvo.timedDraw(l[0].rasterPoints(), ui.traceSpin.value())

cur_shape = None
ui = uic.loadUi('galvo.ui')
ui.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
ui.closeEvent = onClose
ui.showEvent = onOpen
scene = GalvoScene()
scene.galvo.lasers[0].sigRenamed.connect(ui.laser1Button.setText)
scene.galvo.lasers[1].sigRenamed.connect(ui.laser2Button.setText)

scene.sigSelectionChanged.connect(selectionChanged)
scene.galvo.sigMoved.connect(lambda pos: ui.statusBar().showMessage("Mouse at (%.2f, %.2f)" % (pos.x(), pos.y())))

ui.graphicsView.setScene(scene)
scene.setSceneRect(QtCore.QRectF(ui.graphicsView.rect()))

ui.calibrateButton.pressed.connect(calibrate)
ui.clearButton.pressed.connect(scene.clear)
ui.resetButton.pressed.connect(scene.reset)
ui.closeButton.pressed.connect(ui.close)

ui.laser1Button.toggled.connect(lambda f: scene.galvo.setLaserActive(0, f))
ui.manualButton.pressed.connect(lambda : scene.galvo.setLaserActive(0, True))
ui.manualButton.released.connect(lambda : scene.galvo.setLaserActive(0, False))
ui.pulseButton.pressed.connect(lambda : pulsePressed(0))

ui.laser2Button.toggled.connect(lambda f: scene.galvo.setLaserActive(1, f))
ui.manual2Button.pressed.connect(lambda : scene.galvo.setLaserActive(1, True))
ui.manual2Button.released.connect(lambda : scene.galvo.setLaserActive(1, False))
ui.pulse2Button.pressed.connect(lambda : pulsePressed(1))
ui.roiButton.pressed.connect(lambda : scene.setDrawMethod('ROI'))
ui.lineButton.pressed.connect(lambda : scene.setDrawMethod('Line'))
ui.traceButton.pressed.connect(traceLine)

ui.opacitySlider.valueChanged.connect(lambda v: ui.setWindowOpacity(v/100.))
ui.opacitySlider.setValue(85)

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
