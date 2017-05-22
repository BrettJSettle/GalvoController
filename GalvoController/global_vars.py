from qtpy import uic, QtWidgets, QtCore
import pickle, sys, os
ui = None
DEBUG = False
intervals = 10
pulse_time = 1000 # milliseconds
timer = None

def load_settings(fname='settings.p'):
	if os.path.exists(fname):
		with open(fname, 'rb') as f:
			d = pickle.load(f)
		ui.setGeometry(*d['window'])
		ui.scene.galvo.setBounds(QtCore.QRectF(d['galvo_x'], d['galvo_y'], d['galvo_width'], d['galvo_height']))
		ui.scene.galvo.lasers[0].rename(d['laser1'][0])
		ui.scene.galvo.lasers[0].changePin(d['laser1'][1])
		ui.scene.galvo.lasers[1].rename(d['laser2'][0])
		ui.scene.galvo.lasers[1].changePin(d['laser2'][1])
	ui.scene.center()

def save_settings(fname='settings.p'):
	geom = ui.geometry()
	x = geom.x()
	y = geom.y()
	w = geom.width()
	h = geom.height()
	values = {'galvo_x': ui.scene.galvo.boundRect.x(), 'galvo_y': ui.scene.galvo.boundRect.y(), \
			'galvo_width': ui.scene.galvo.boundRect.width(), 'galvo_height': ui.scene.galvo.boundRect.height(),\
			'laser1': (ui.scene.galvo.lasers[0].name, ui.scene.galvo.lasers[0].pin), 'laser2': (ui.scene.galvo.lasers[1].name, ui.scene.galvo.lasers[1].pin), 'window': list([x, y, w, h])}
	with open(fname, 'wb') as f:
		pickle.dump(values, f)
