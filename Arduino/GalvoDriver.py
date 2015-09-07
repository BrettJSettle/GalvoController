from PyQt4 import QtGui, QtCore
import numpy as np
from GalvoGraphics import *
import serial
import time

class GalvoScene(QtGui.QGraphicsScene):
	def __init__(self, **kargs):
		super(GalvoScene, self).__init__(**kargs)
		self.crosshair = CrossHair()
		self.crosshair.sigMoved.connect(self.crosshairMoved)
		self.addItem(self.crosshair)
		self.galvo = GalvoDriver()

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
				#self.galvo.write_points(shape)
				self.galvo.deactivateLasers()
		self.drawing = True
		self.duration = -1

	def setPoints(self, p):
		self.points = p

	def stop(self):
		self.drawing = False

class GalvoDriver():
	'''implementation of Galvo Driver that sends one coordinate at a time similar to a QGraphicsObject,
	handles maximum and minimum values accordingly'''
	boundRect = QtCore.QRectF(-10, -10, 20, 20)
	def __init__(self):
		self.ser = serial.Serial('COM3', 9600, timeout=2)
		self.ports = {'analog X': b'A0', 'analog Y': b'A1'}
		self.active = False
		self.lines = {0: False, 1: False}
		self.pos = QtCore.QPointF()
		self.update()

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

	def updateDigital(self):
		if self.active:
			for i in self.lines:
				self.ser.write(str(i).encode('utf-8'))
				self.ser.write(str(self.lines[i]).encode('utf-8'))

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

	def write_points(self, points):

		pts = []
		for p in points:
			pts.append([self.boundRect.x() + (p.x() * self.boundRect.width()), self.boundRect.y() + (p.y() * self.boundRect.height())])
		data = np.array([p[1] for p in pts] + [p[0] for p in pts], dtype=np.float64)
		samps = len(data)//2
		pass

	def update(self):
		self.ser.write(bytes(self.ports['analog X']))
		self.ser.write(str(self.pos.x()).encode('utf-8'))
		self.ser.write(bytes(self.ports['analog Y']))
		self.ser.write(str(self.pos.y()).encode('utf-8'))
