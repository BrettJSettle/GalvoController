from PyQt4 import uic, QtCore
import GalvoDriver
import pickle, sys
ui = None
scene = None
DEBUG = False
rois = []
line = None
line_intervals = 10
pulse_time = 1000 # milliseconds
timer = None

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
	scene.galvo.setLaserActive((0, 1), False)

def onClose(ev):
	scene.galvo.setLaserActive((0, 1), False)
	if ui.actionAutosave.isChecked():
		export_settings('settings.p')
	sys.exit(0)

def reset():
	ui.pointButton.click()
	scene.center()
	scene.resetBounds()

def initUiAndScene(filename):
	global ui, scene
	ui = uic.loadUi(filename)
	scene = GalvoDriver.GalvoScene()
	ui.graphicsView.setScene(scene)
	ui.showEvent = onOpen
	ui.closeEvent = onClose
	scene.setSceneRect(QtCore.QRectF(ui.graphicsView.rect()))

	return ui, scene