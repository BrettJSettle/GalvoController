from PyQt4 import QtCore, QtGui, uic
import numpy as np
import pickle
app = QtGui.QApplication([])
import time, sys
from GalvoDriver import *
from GalvoGraphics import *

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
	ui.keyPressEvent = lambda ev: QMainWindow.keyPressedEvent(ui, ev)
	scene.galvo.setBounds(scene.tempRect)
	ui.infoLabel.setText('Calibrated, drag crosshair to position laser. Right click to translate crosshair')

def import_settings(fname):
	with open(fname, 'rb') as f:
		d = pickle.load(f)
	scene.galvo.setBounds(QtCore.QRectF(d['galvo_x'], d['galvo_y'], d['galvo_width'], d['galvo_height']))

def export_settings(fname):
	values = {'galvo_x': scene.galvo.boundRect.x(), 'galvo_y': scene.galvo.boundRect.y(), \
			'galvo_width': scene.galvo.boundRect.width(), 'galvo_height': scene.galvo.boundRect.height()}
	with open(fname, 'wb') as f:
		pickle.dump(values, f)

def onOpen(ev):
	try:
		import_settings('settings.p')
	except Exception as e:
		print(e)

def onClose(ev):
	export_settings('settings.p')
	sys.exit(0)

def mousePressEvent(ev):
	global cur_shape, thread
	for i in scene.shapes():
		if i.selected:
			i.deselect()
	if thread != None:
		thread.drawing = False

	if ev.button() == QtCore.Qt.LeftButton:
		if not scene.crosshair.isVisible():
			scene.crosshair.show()
		GalvoScene.mousePressEvent(scene, ev)

	elif ev.button() == QtCore.Qt.RightButton:
		pos = ev.scenePos()
		for i in scene.shapes():
			if i.contains(pos):
				shapeSelected(i)
				return
		cur_shape = GalvoShape(pos)
		scene.addItem(cur_shape)

def mouseMoveEvent(ev):
	if cur_shape != None:
		cur_shape.addPoint(ev.scenePos())
	else:
		pass
	GalvoScene.mouseMoveEvent(scene, ev)

def mouseReleaseEvent(ev):
	global cur_shape
	if cur_shape != None:
		cur_shape.close()
		cur_shape = None
	GalvoScene.mouseReleaseEvent(scene, ev)

def shapeSelected(shape):
	global thread
	shape.select()
	scene.crosshair.setVisible(not shape.selected)
	thread = ShapeThread([scene.mapToGalvo(p) for p in shape.rasterPoints()], scene.galvo)
	thread.start()

thread = None
cur_shape = None
ui = uic.loadUi('galvo.ui')
ui.closeEvent = onClose
ui.showEvent = onOpen
ui.calibrateButton.pressed.connect(calibrate)
scene = GalvoScene()
scene.shapes = lambda : [i for i in scene.items() if isinstance(i, GalvoShape)]
ui.clearButton.pressed.connect(scene.clear)
ui.resetButton.pressed.connect(scene.reset)
ui.closeButton.pressed.connect(ui.close)
scene.mousePressEvent = mousePressEvent
scene.mouseMoveEvent = mouseMoveEvent
scene.mouseReleaseEvent = mouseReleaseEvent
mb = ui.menuBar()
galvoMenu = mb.addMenu('&Galvo')
galvoMenu.addAction(QtGui.QAction('&Calibrate', galvoMenu, triggered=calibrate))
galvoMenu.addAction(QtGui.QAction('&Reset Settings', galvoMenu, triggered=scene.reset))
fileMenu = mb.addMenu('&File')
fileMenu.addAction(QtGui.QAction('&Import Settings', fileMenu, triggered=lambda : import_settings(QtGui.QFileDialog.askOpenFilename(filter='Pickled files (*.p)'))))
fileMenu.addAction(QtGui.QAction('&Export Settings', fileMenu, triggered=lambda : export_settings(QtGui.QFileDialog.askSaveFilename(filter='Pickled files (*.p)'))))
ui.graphicsView.setScene(scene)
scene.setSceneRect(QtCore.QRectF(ui.graphicsView.rect()))
ui.opacitySlider.valueChanged.connect(lambda v: ui.setWindowOpacity(v/100.))
ui.show()
app.exec_()
