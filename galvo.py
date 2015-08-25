from PyQt4 import QtCore, QtGui, uic
from PyDAQmx import *
from PyDAQmx.DAQmxCallBack import *
import numpy as np
import pickle
app = QtGui.QApplication([])
import time, sys
from skimage.draw import polygon

class GalvoScene(QtGui.QGraphicsScene):
	sigRightClicked = QtCore.pyqtSignal(object)
	def __init__(self, **kargs):
		super(GalvoScene, self).__init__(**kargs)
		self.crosshair = CrossHair()
		self.crosshair.sigMoved.connect(self.updatePos)
		self.addItem(self.crosshair)
		self.galvo = GalvoDriver()

	def updatePos(self, pos):
		pos = mapToGalvo(pos)
		self.galvo.setPos(pos)

	def mousePressEvent(self, ev):
		global settings
		p = ev.scenePos()
		if ev.button() == QtCore.Qt.LeftButton:
			self.crosshair.setPos(ev.scenePos())
		else:
			self.sigRightClicked.emit(ev.scenePos())
		QtGui.QGraphicsScene.mousePressEvent(self, ev)

	def reset(self):
		self.galvo.boundRect = QtCore.QRect(-10, -10, 20, 20)

def mapFromGalvo(pt):
	'''maps an analog output value to a scene coordinate'''
	p = pt - scene.galvo.boundRect.topLeft()
	p.setX(p.x() / scene.galvo.boundRect.width() * ui.graphicsView.width())
	p.setY(p.y() / scene.galvo.boundRect.height() * ui.graphicsView.height())
	return p

def mapToGalvo(pt):
	'''maps a scene point to a percent to be used in the galvo driver'''
	p = QtCore.QPointF(ui.graphicsView.mapFromScene(pt))
	p.setX(p.x() / ui.graphicsView.width())
	p.setY(p.y() / ui.graphicsView.height())
	return p


class GalvoDriver():
	'''implementation of Galvo Driver that sends one coordinate at a time similar to a QGraphicsObject,
	handles maximum and minimum values accordingly'''
	boundRect = QtCore.QRectF(-10, -10, 20, 20)
	def __init__(self):
		self.sample_rate=5000 # Maximum for the NI PCI-6001 is 5kHz.
		self.bufferSize=2 #dummy variable
		self.read = int32()
		self.establishChannels()
		self.pos = QtCore.QPointF()
		self.update()

	def setBounds(self, boundRect):
		self.boundRect = boundRect

	def establishChannels(self):
		self.analog_output = Task()
		self.analog_output.CreateAOVoltageChan(b'Dev1/ao0',b"",-10.0,10.0,DAQmx_Val_Volts,None) #On the NI PCI-6001, AO is on the left side
		self.analog_output.CreateAOVoltageChan(b"Dev1/ao1",b"",-10.0,10.0,DAQmx_Val_Volts,None)

	def setPos(self, *args):
		'''accepts percentages using boundRect to assign a new position'''
		try:
			x, y = args
		except:
			x, y = args[0].x(), args[0].y()
		self.pos = QtCore.QPointF(self.boundRect.x() + (self.boundRect.width() * x), self.boundRect.y() + (self.boundRect.height() * y))
		self.pos.setX(min(10, max(self.pos.x(), -10)))
		self.pos.setY(min(10, max(self.pos.y(), -10)))
		self.update()

	def pos(self):
		p = pos - self.boundRect.topLeft()
		p.setX(p.x() / self.boundRect.width())
		p.setY(p.y() / self.boundRect.height())
		return p

	def write_pattern(self, points):
		self.analog_output.StopTask()
		#self.analog_output.CfgSampClkTiming("",self.sample_rate,DAQmx_Val_Rising,DAQmx_Val_ContSamps, 2)
		pts = []
		for x, y in points:
			pts.append([self.boundRect.x() + (x * self.boundRect.width()), self.boundRect.y() + (y * self.boundRect.height())])
		points = [p[0] for p in pts] + [p[1] for p in pts]
		data = np.array(points, dtype=np.float64)
		print(data)
		while(True):
			self.analog_output.WriteAnalogF64(2,1,-1,DAQmx_Val_GroupByChannel,data,byref(self.read),None)
			time.sleep(0.2)
			self.analog_output.StopTask()
	def update(self):
		self.analog_output.StopTask()
		data = np.array([self.pos.y(), self.pos.x()], dtype=np.float64)
		self.analog_output.WriteAnalogF64(self.bufferSize,1,-1,DAQmx_Val_GroupByChannel,data,byref(self.read),None)
		ui.statusBar().showMessage('Laser at (%.2f, %.2f)' % (self.pos.y(), self.pos.x()))

class CrossHair(QtGui.QGraphicsObject):
	'''draggable crosshair object that acts as an aimer in a QGraphics Scene'''
	sigMoved = QtCore.pyqtSignal(object)
	def __init__(self, parent=None, size=7, color = QtCore.Qt.red, pos=QtCore.QPointF(0, 0)):
		QtGui.QGraphicsObject.__init__(self, parent)
		self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)
		self.pen = QtGui.QPen(color)
		self.pen.setWidth(3)
		self.setPos(pos)
		self.size = size
		self.xChanged.connect(lambda : self.sigMoved.emit(self.pos()))
		self.yChanged.connect(lambda: self.sigMoved.emit(self.pos()))

	def paint(self, painter, option, widget):
		'''paint the crosshair'''
		painter.setPen(self.pen)
		painter.drawEllipse(self.boundingRect())
		painter.drawLine(-self.size, 0, self.size, 0)
		painter.drawLine(0, -self.size, 0, self.size)

	def mouseMoveEvent(self, ev):
		'''only draggable if mouse is in the frame'''
		pos = self.scene().views()[0].mapFromScene(ev.scenePos().toPoint())
		inside = self.scene().views()[0].frameRect().adjusted(self.size, self.size, -self.size, -self.size)
		if inside.contains(pos):
			QtGui.QGraphicsObject.mouseMoveEvent(self, ev)

	def boundingRect(self):
		'''shape to draw in'''
		return QtCore.QRectF(-self.size - 1, -self.size - 1, 2 * self.size + 1, 2 * self.size + 1)

def calibrate():
	global settings
	scene.reset()
	aim = CrossHair(size = 5, color=QtCore.Qt.blue, pos=ui.graphicsView.mapToScene(10, 10))
	scene.addItem(aim)
	ui.infoLabel.setText('Resize the window, drag the laser to the top left corner, then right click over it')
	scene.sigRightClicked.connect(lambda ev: setattr(scene, 'tempRect', QtCore.QRectF(scene.galvo.pos - QtCore.QPointF(.5, .5), QtCore.QSizeF())))
	while not hasattr(scene, 'tempRect'):
		QtGui.qApp.processEvents()
		time.sleep(.01)
	scene.sigRightClicked.disconnect()

	aim.setPos(ui.graphicsView.mapToScene(ui.graphicsView.width() - 10, ui.graphicsView.height() - 10))
	done = lambda : scene.tempRect.setSize(QtCore.QSizeF(scene.galvo.pos.x() - scene.tempRect.x() + .5, scene.galvo.pos.y() - scene.tempRect.y() + .5))
	ui.infoLabel.setText('Now drag the laser to the bottom right and right click it again')
	scene.sigRightClicked.connect(done)
	while scene.tempRect.isEmpty():
		QtGui.qApp.processEvents()
		time.sleep(.01)
	scene.removeItem(aim)
	scene.sigRightClicked.disconnect()
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

def raster_rect(rect):
	topLeft = mapToGalvo(rect.topLeft())
	bottomRight = mapToGalvo(rect.bottomRight())
	x_left = topLeft.x()
	x_right = bottomRight.x()
	pts = []
	for i, y in enumerate(np.arange(topLeft.y(), bottomRight.y(), .01)):
		if i % 2 == 0:
			pts.extend([[x_left, y], [x_right, y]])
		else:
			pts.extend([[x_right, y], [x_left, y]])

	pts.extend(pts[:-1:-1])
	scene.galvo.write_pattern(pts)

def make_rect(pos):
	global drawing, rects
	for i in rects:
		if pos in i.rect():
			raster_rect(i.rect())
			return
	drawing = QtCore.QRectF(pos.x(), pos.y(), 0, 0)
	rects.append(QtGui.QGraphicsRectItem(drawing))
	scene.addItem(rects[-1])

def mouseMoveEvent(ev):
	if drawing != None:
		drawing.setWidth(ev.scenePos().x() - drawing.x())
		drawing.setHeight(ev.scenePos().y() - drawing.y())
		rects[-1].setRect(drawing)
	else:
		print(ev.scenePos())
	QtGui.QGraphicsScene.mouseMoveEvent(scene, ev)

def mouseReleaseEvent(ev):
	global drawing, rects
	if drawing != None and drawing.isEmpty():
		scene.removeItem(rects[-1])
		rects = rects[:-1]
	drawing = None
	QtGui.QGraphicsScene.mouseReleaseEvent(scene, ev)

drawing = None
rects = []
ui = uic.loadUi('galvo.ui')
ui.closeEvent = onClose
ui.showEvent = onOpen
scene = GalvoScene()
scene.sigRightClicked.connect(make_rect)
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
