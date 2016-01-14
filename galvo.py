from PyQt4 import QtCore, QtGui, uic
import numpy as np
import pickle
app = QtGui.QApplication([])
import time, sys, os
from GalvoDriver import *
from GalvoGraphics import *
from threading import Timer
import global_vars as g

def calibrate():
	global settings
	g.reset()
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
	ti.setPlainText('Now position the laser in optimal bottom \n      right, and press a key')
	while scene.tempRect.isEmpty():
		QtGui.qApp.processEvents()
		time.sleep(.01)
	scene.removeItem(aim)
	scene.keyPressEvent = GalvoScene.keyPressEvent
	scene.galvo.setBounds(scene.tempRect)
	del scene.tempRect
	scene.removeItem(ti)#('Calibrated, right click drag to position laser. Left click drag to draw ROIs')

def pulsePressed(num):
	pulse_time = ui.pulseSpin.value() / 1000.0
	if scene.drawMethod == 'Line':
		pts = [scene.mapToGalvo(p) for p in scene.line.rasterPoints(g.line_intervals)]
		def to_pt(i):
			if i >= len(pts):
				print(time.time() - t)
				scene.galvo.setLaserActive(num, False)
				return
			scene.galvo.moveTo(pts[i])
			Timer(pulse_time/g.line_intervals, lambda : to_pt(i + 1)).start()
		scene.galvo.setLaserActive(num, True)
		t = time.time()
		to_pt(0)
	else:
		scene.galvo.setLaserActive(num, True)
		Timer(pulse_time, lambda : scene.galvo.setLaserActive(num, False)).start()

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
	ps = [[scene.mapToGalvo(p) for p in shape.rasterPoints()] for shape in scene.getGalvoShapes() if shape.selected and type(shape) == GalvoShape]
	scene.galvo.setShapes(ps)
	scene.crosshair.setVisible(not any([shape.selected for shape in scene.getGalvoShapes()]))

def changeRasterShift():
	result, ok = QtGui.QInputDialog.getInt(ui, "Raster Shift", "Enter the shift in pixels to translate the laser when rastering polygons:", GalvoShape.RASTER_GAP, min=0)
	if ok:
		GalvoShape.RASTER_GAP = result

def closeCommandPrompt():
    from ctypes import windll
    GetConsoleWindow = windll.kernel32.GetConsoleWindow
    console_window_handle = GetConsoleWindow()
    ShowWindow = windll.user32.ShowWindow
    ShowWindow(console_window_handle, 0)

def pressed(num):
	button = ui.laser1Button if num == 0 else ui.laser2Button
	button.presstime = time.time()
	if not button.isChecked():
		scene.galvo.setLaserActive(num, True)

def released(num):
	button = ui.laser1Button if num == 0 else ui.laser2Button
	if time.time() - button.presstime > .2: # used as manual button
		button.setChecked(False)
		scene.galvo.setLaserActive(num, False)
	elif not button.isChecked():
		scene.galvo.setLaserActive(num, button.isChecked())

def connectUi():
	ui.clearButton.pressed.connect(scene.clear)
	ui.closeButton.pressed.connect(ui.close)

	ui.laser1Button.pressed.connect(lambda : pressed(0))
	ui.laser1Button.released.connect(lambda : released(0))
	ui.pulseButton.pressed.connect(lambda : pulsePressed(0))

	ui.laser2Button.pressed.connect(lambda : pressed(1))
	ui.laser2Button.released.connect(lambda : released(1))
	ui.pulse2Button.pressed.connect(lambda : pulsePressed(1))

	ui.roiButton.pressed.connect(lambda : scene.setDrawMethod('ROI'))
	ui.lineButton.pressed.connect(lambda : scene.setDrawMethod('Line'))
	ui.pointButton.pressed.connect(lambda : scene.setDrawMethod('Point'))
	ui.lineSepCounter.valueChanged.connect(lambda v: setattr(g, 'line_intervals', v))
	ui.opacitySlider.valueChanged.connect(lambda v: ui.setWindowOpacity(v/100.))
	ui.opacitySlider.setValue(85)

	ui.actionConfigure.triggered.connect(configure)
	ui.actionCalibrate.triggered.connect(calibrate)
	ui.actionReset.triggered.connect(g.reset)
	ui.actionRename.triggered.connect(rename_lasers)
	ui.actionEditRaster.triggered.connect(changeRasterShift)
	ui.actionDisconnect.triggered.connect(lambda : sys.exit(0))
	ui.actionImport.triggered.connect(lambda : g.import_settings(QtGui.QFileDialog.getOpenFileName(filter='Pickled files (*.p)')))
	ui.actionExport.triggered.connect(lambda : g.export_settings(QtGui.QFileDialog.getSaveFileName(filter='Pickled files (*.p)')))
	
	scene.galvo.lasers[0].sigRenamed.connect(ui.laser1Button.setText)
	scene.galvo.lasers[1].sigRenamed.connect(ui.laser2Button.setText)

if __name__ == '__main__':
    if os.name =='nt' and '-debug' not in sys.argv:
        closeCommandPrompt()
    else:
    	g.DEBUG = True
    ui, scene = g.initUiAndScene('galvoAlternate.ui')
    connectUi()
    ui.show()
    app.exec_() 