from PyQt4 import QtGui, QtCore
import numpy as np
import serial
from GalvoGraphics import *
import sys
if 'daq' in sys.argv:
	from PyDAQmx import *
	from PyDAQmx.DAQmxCallBack import *
import time

class GalvoScene(QtGui.QGraphicsScene):
	sigSelectionChanged = QtCore.pyqtSignal()
	def __init__(self, port='', **kargs):
		super(GalvoScene, self).__init__(**kargs)
		self.crosshair = CrossHair()
		self.crosshair.sigMoved.connect(self.crosshairMoved)
		self.addItem(self.crosshair)
		if port != '':
			self.galvo = ArduinoGalvoDriver(port=port)
		else:
			self.galvo = GalvoDriver()
		self.crosshair.dragging = False

	def crosshairMoved(self, pos):
		pos = self.mapToGalvo(pos)
		out = False
		if not (0 <= pos.x() <= 1 and 0 <= pos.y() <= 1):
			pos.setX(min(1, max(0, pos.x())))
			pos.setY(min(1, max(0, pos.y())))
			self.crosshair.setPos(self.views()[0].mapToScene(self.views()[0].width() * pos.x(), self.views()[0].height() * pos.y()))
		self.galvo.setPos(pos)

	def getGalvoShapes(self):
		return [i for i in self.items()[::-1] if isinstance(i, GalvoShape)]

	def mousePressEvent(self, ev):
		if ev.button() == QtCore.Qt.RightButton:  # if right button, enable crosshair movement
			self.crosshair.setPos(ev.scenePos())
			self.crosshair.dragging = True
			if not self.crosshair.isVisible():
				self.crosshair.show()
			for sh in self.getGalvoShapes():
				sh.setSelected(False)
				self.sigSelectionChanged.emit()
			QtGui.QGraphicsScene.mousePressEvent(self, ev)

		elif ev.button() == QtCore.Qt.LeftButton:	# draw shapes
			toggled = False	
			if int(ev.modifiers()) == QtCore.Qt.ControlModifier:	# if control held, just toggle all shapes under mouse
				for sh in self.getGalvoShapes():
					if sh.mouseIsOver:
						sh.setSelected(not sh.selected)
						toggled = True
			else:
				for sh in self.getGalvoShapes():
					if sh.mouseIsOver:
						self.crosshair.setVisible(False)
						sh.setSelected(True)
						toggled = True
					elif sh.selected:
						sh.setSelected(False)

			if not toggled:					# if none are selected, create a new shape
				for sh in self.getGalvoShapes():
					sh.setSelected(False)
				self.cur_shape = GalvoShape(ev.scenePos())
				self.addItem(self.cur_shape)
			else:
				self.sigSelectionChanged.emit()

	def mouseMoveEvent(self, ev):
		if self.crosshair.dragging:	#ignore shapes if dragging crosshair
			self.crosshair.setPos(ev.scenePos())
		elif hasattr(self, 'cur_shape'):
			self.cur_shape.addPoint(ev.scenePos())
		else:
			for sh in self.getGalvoShapes():
				sh.mouseOver(ev.scenePos())
		QtGui.QGraphicsScene.mouseMoveEvent(self, ev)

	def mouseReleaseEvent(self, ev):
		if self.crosshair.dragging:
			self.crosshair.dragging = False
		elif hasattr(self, 'cur_shape'):
			self.cur_shape.close()
			del self.cur_shape
		QtGui.QGraphicsScene.mouseReleaseEvent(self, ev)

	def keyPressEvent(self, ev):
		if ev.key() == 16777223:
			for sh in self.getGalvoShapes()[::-1]:
				if sh.selected:
					self.removeItem(sh)
					self.sigSelectionChanged.emit()

	def clear(self):
		for i in self.items()[::-1]:
			self.removeItem(i)
		self.addItem(self.crosshair)

	def reset(self):
		self.galvo.setBounds(QtCore.QRect(-10, -10, 20, 20))
		self.galvo.setPos(0, 0)

	def mapFromGalvo(self, pt):
		'''maps an analog output value to a scene coordinate'''
		p = pt - self.galvo.boundRect.topLeft()
		p.setX(p.x() / scene.galvo.boundRect.width() * self.views()[0].width())
		p.setY(p.y() / scene.galvo.boundRect.height() * self.views()[0].height())
		return p

	def mapToGalvo(self, pt):
		'''maps a scene point to a percent to be used in the galvo driver'''
		p = QtCore.QPointF(self.views()[0].mapFromScene(pt))
		p.setX(p.x() / self.views()[0].width())
		p.setY(p.y() / self.views()[0].height())
		return p

class ShapeThread(QtCore.QThread):
	def __init__(self, galvo, duration=-1):
		super(ShapeThread, self).__init__()
		self.points = []
		self.galvo = galvo
		self.drawing = True
		self.duration = duration

	def setDuration(self, t=-1):
		self.duration = t

	def empty(self):
		return len(self.points) == 0

	def run(self):
		start = time.clock()
		while (self.duration == -1 or time.clock() - start < self.duration) and self.drawing:
			for shape in self.points:
				self.galvo.setPos(shape[0])
				self.galvo.activateLasers()
				self.galvo.write_points(shape)
				self.galvo.deactivateLasers()
		self.drawing = True
		self.duration = -1

	def setPoints(self, p):
		self.points = p

	def stop(self):
		self.drawing = False

class GalvoBase():
	'''implementation of Galvo Driver that sends one coordinate at a time similar to a QGraphicsObject,
	handles maximum and minimum values accordingly'''
	boundRect = QtCore.QRectF(-10, -10, 20, 20)
	def __init__(self):
		self.active = False
		self.lines = {0: False, 1: False}
		self.pos = QtCore.QPointF()

	def setBounds(self, boundRect):
		self.boundRect = boundRect

	def activateLasers(self, lines=[]):
		self.active = True
		self.updateDigital()
	
	def deactivateLasers(self, lines=[]):
		self.active = False
		self.updateDigital()

	def setLines(self, lines):
		self.lines = lines
		self.updateDigital()

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

class GalvoDriver(GalvoBase):
	'''implementation of Galvo Driver that sends one coordinate at a time similar to a QGraphicsObject,
	handles maximum and minimum values accordingly'''
	boundRect = QtCore.QRectF(-10, -10, 20, 20)
	def __init__(self):
		super(GalvoDriver, self).__init__()
		self.sample_rate=5000 # Maximum for the NI PCI-6001 is 5kHz.
		self.bufferSize=2 #dummy variable
		self.read = int32()
		self.establishChannels()
		self.update()

	def establishChannels(self):
		self.analog_output = Task()
		self.analog_output.CreateAOVoltageChan(b'Dev1/ao0',b"",-10.0,10.0,DAQmx_Val_Volts,None)
		self.analog_output.CreateAOVoltageChan(b"Dev1/ao1",b"",-10.0,10.0,DAQmx_Val_Volts,None)
		self.digital_output = Task()
		self.digital_output.CreateDOChan(b'Dev1/port0/line0:7',b"",DAQmx_Val_ChanForAllLines)

	def updateDigital(self):
		digital_data = np.uint8([0, 0, 0, 0, 0, 0, 0, 0])
		if self.active:
			for i in self.lines:
				if self.lines[i]:
					digital_data[i] = 1
		self.digital_output.WriteDigitalLines(1,1,-1,DAQmx_Val_ChanForAllLines,digital_data,None,None)

	def write_points(self, points):
		self.analog_output.StopTask()
		pts = []
		for p in points:
			pts.append([self.boundRect.x() + (p.x() * self.boundRect.width()), self.boundRect.y() + (p.y() * self.boundRect.height())])
		data = np.array([p[1] for p in pts] + [p[0] for p in pts], dtype=np.float64)
		samps = len(data)//2
		self.analog_output.WriteAnalogF64(samps,1,-1,DAQmx_Val_GroupByChannel,data,byref(self.read),None)

	def write_path(self, painterPath, steps = 1000):
		self.analog_output.StopTask()
		pts = []
		for i in np.linspace(0, 1, steps):
			p = painterPath.pointAtPercent(i)
			pts.append(QtCore.QPointF(self.boundRect.x() + (p.x() * self.boundRect.width()), self.boundRect.y() + (p.y() * self.boundRect.height())))
		self.write_points(pts)

	def update(self):
		self.analog_output.StopTask()
		data = np.array([self.pos.y(), self.pos.y(), self.pos.x(), self.pos.x()], dtype=np.float64)
		self.analog_output.WriteAnalogF64(self.bufferSize,1,-1,DAQmx_Val_GroupByChannel,data,byref(self.read),None)

class ArduinoGalvoDriver(GalvoBase):
	'''implementation of Galvo Driver that sends one coordinate at a time similar to a QGraphicsObject,
	handles maximum and minimum values accordingly'''
	boundRect = QtCore.QRectF(-10, -10, 20, 20)
	def __init__(self, port):
		super(ArduinoGalvoDriver, self).__init__()
		self.ser = serial.Serial(port, 9600, timeout=2)
		self.ports = {'analog X': b'A0', 'analog Y': b'A1'}
		self.update()

	def updateDigital(self):
		if self.active:
			s = 'D'
			for i in self.lines:
				s += ' %d %d' % (i, self.lines[i])
			s += '\n'
			self.ser.write(s.encode('utf-8'))

	def write_points(self, points):
		return
		pts = []
		for p in points:
			pts.append([self.boundRect.x() + (p.x() * self.boundRect.width()), self.boundRect.y() + (p.y() * self.boundRect.height())])
		data = np.array([p[1] for p in pts] + [p[0] for p in pts], dtype=np.float64)
		samps = len(data)//2
		

	def update(self):
		print('writing (%d, %d)' % (self.pos.x(), self.pos.y()))
		return
		self.ser.write(bytes(self.ports['analog X']))
		self.ser.write(str(self.pos.x()).encode('utf-8'))
		self.ser.write(bytes(self.ports['analog Y']))
		self.ser.write(str(self.pos.y()).encode('utf-8'))
		
