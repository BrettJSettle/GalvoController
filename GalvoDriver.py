from PyQt4 import QtGui, QtCore
import numpy as np
from PyDAQmx import *
from PyDAQmx.DAQmxCallBack import *
from GalvoGraphics import *

class GalvoScene(QtGui.QGraphicsScene):
	def __init__(self, **kargs):
		super(GalvoScene, self).__init__(**kargs)
		self.crosshair = CrossHair()
		self.crosshair.sigMoved.connect(self.updatePos)
		self.addItem(self.crosshair)
		self.galvo = GalvoDriver()

	def updatePos(self, pos):
		pos = self.mapToGalvo(pos)
		out = False
		if not (0 <= pos.x() <= 1 and 0 <= pos.y() <= 1):
			pos.setX(min(1, max(0, pos.x())))
			pos.setY(min(1, max(0, pos.y())))
			self.crosshair.setPos(self.views()[0].mapToScene(self.views()[0].width() * pos.x(), self.views()[0].height() * pos.y()))
		self.galvo.setPos(pos)

	def mousePressEvent(self, ev):
		global settings
		p = ev.scenePos()
		if ev.button() == QtCore.Qt.LeftButton:
			self.crosshair.setPos(ev.scenePos())
		QtGui.QGraphicsScene.mousePressEvent(self, ev)

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
	def __init__(self, points, galvo):
		super(ShapeThread, self).__init__()
		self.points = points
		self.galvo = galvo
		self.drawing = True

	def run(self):
		while self.drawing:
			self.galvo.write_points(self.points)
		self.terminate()

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