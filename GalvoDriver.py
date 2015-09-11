from PyQt4 import QtGui, QtCore
import numpy as np
from GalvoGraphics import *
import sys
from PyDAQmx import *
from PyDAQmx.DAQmxCallBack import *
import time

class Laser(QtCore.QObject):
	sigRenamed = QtCore.pyqtSignal(str)
	sigToggled = QtCore.pyqtSignal()
	def __init__(self, name, pin):
		super(Laser, self).__init__()
		self.name = name
		self.pin = pin
		self.active = False
	def setActive(self, a):
		self.active = a
		self.sigToggled.emit()
	def rename(self, s):
		self.name = s
		self.sigRenamed.emit(s)
	def changePin(self, p):
		self.pin = p
		
class GalvoScene(QtGui.QGraphicsScene):
	sigSelectionChanged = QtCore.pyqtSignal()
	def __init__(self, **kargs):
		super(GalvoScene, self).__init__(**kargs)
		self.crosshair = CrossHair()
		self.crosshair.sigMoved.connect(self.crosshairMoved)
		self.addItem(self.crosshair)
		self.galvo = GalvoDriver()
		self.crosshair.dragging = False

	def crosshairMoved(self, pos):
		pos = self.mapToGalvo(pos)
		if not (0 <= pos.x() <= 1 and 0 <= pos.y() <= 1):
			pos.setX(min(1, max(0, pos.x())))
			pos.setY(min(1, max(0, pos.y())))
			self.crosshair.setPos(self.views()[0].mapToScene(self.views()[0].width() * pos.x(), self.views()[0].height() * pos.y()))
		self.galvo.moveTo(pos)
	
	def center(self):
		self.crosshair.setPos(self.views()[0].mapToScene(self.views()[0].width() * .5, self.views()[0].height() * .5))

	def getGalvoShapes(self):
		return [i for i in self.items()[::-1] if isinstance(i, GalvoShape)]

	def mousePressEvent(self, ev):
		if ev.button() == QtCore.Qt.RightButton:  # if right button, enable crosshair movement
			
			self.crosshair.setPos(ev.scenePos())
			self.crosshair.dragging = True
			if not self.crosshair.isVisible():
				self.crosshair.setVisible(True)
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
						sh.setSelected(True)
						toggled = True
					elif sh.selected:
						sh.setSelected(False)
						
			self.sigSelectionChanged.emit()
			if not toggled:					# if none are selected, create a new shape
				self.cur_shape = GalvoShape(ev.scenePos())
				self.addItem(self.cur_shape)

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
			if isinstance(i, GalvoShape):
				self.removeItem(i)

	def reset(self):
		self.galvo.setBounds(QtCore.QRect(-10, -10, 20, 20))
		self.center()

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

class GalvoBase(QtCore.QThread):
	'''implementation of Galvo Driver that sends one coordinate at a time similar to a QGraphicsObject,
	handles maximum and minimum values accordingly'''
	boundRect = QtCore.QRectF(-10, -10, 20, 20)
	def __init__(self):
		super(GalvoBase, self).__init__()
		self.active = False
		self.lasers = [Laser('Laser 1', 0), Laser('Laser 2', 1)]
		for l in self.lasers:
			l.sigToggled.connect(lambda : self.updateDigital() if self.active else None) # only toggle lasers if they are active
		self.shapes = []
		self.duration = -1

	def setShapes(self, shapes):
		self.shapes = shapes

	def setBounds(self, boundRect):
		self.boundRect = boundRect

	def penDown(self):
		self.active = True
		self.updateDigital()
	
	def penUp(self):
		self.active = False
		while self.isRunning():
			pass
		self.updateDigital()

class GalvoDriver(GalvoBase):
	'''implementation of Galvo Driver that sends one coordinate at a time similar to a QGraphicsObject,
	handles maximum and minimum values accordingly'''
	boundRect = QtCore.QRectF(-10, -10, 20, 20)
	def __init__(self):
		super(GalvoDriver, self).__init__()
		self.sample_rate=5000 # Maximum for the NI PCI-6001 is 5kHz.
		self.bufferSize=2
		self.read = int32()
		self.establishChannels()
		self.pos = QtCore.QPointF()

	def establishChannels(self):
		self.analog_output = Task()
		#self.analog_output.CreateAOVoltageChan(b'Dev3/ao0',b"",-10.0,10.0,DAQmx_Val_Volts,None)
		#self.analog_output.CreateAOVoltageChan(b"Dev3/ao1",b"",-10.0,10.0,DAQmx_Val_Volts,None)
		self.digital_output = Task()
		#self.digital_output.CreateDOChan(b'Dev3/port0/line0:7',b"",DAQmx_Val_ChanForAllLines)
		#self.analog_output.CfgSampClkTiming("", self.sample_rate, DAQmx_Val_Rising, DAQmx_Val_ConstSamps, self.bufferSize) # set to maximum speed

	def updateDigital(self):
		digital_data = np.uint8([0, 0, 0, 0, 0, 0, 0, 0])
		if self.active:
			for i in self.lasers:
				if i.active:
					digital_data[i.pin] = 1
		#self.digital_output.WriteDigitalLines(1,1,-1,DAQmx_Val_ChanForAllLines,digital_data,None,None)
		print("Toggling: %s" % [l.active and self.active for l in self.lasers])

	def run(self):
		start = time.clock()
		self.active = True
		while self.active:
			if len(self.shapes) > 1:	# draw multiple shapes, jumping between
				for shape in self.shapes:
					self.moveTo(shape[0], penUp=True)
					self.write_points(shape)
			elif len(self.shapes) == 1:	# draw one shape, top to bottom to top again
				self.write_points(self.shapes[0][:-1] + self.shapes[0][::-1])

	def moveTo(self, pos, penUp=False):
		self.pos = pos
		if penUp:
			self.penUp()
		data = np.array([pos.y(), pos.y(), -pos.x(), -pos.x()], dtype=np.float64)
		#self.analog_output.WriteAnalogF64(self.bufferSize,1,-1,DAQmx_Val_GroupByChannel,data,byref(self.read),None)
		#print("Moving: %s" % [l.active and self.active for l in self.lasers])
		if self.active and penUp:
			self.penDown()

	def write_points(self, points):
		self.analog_output.StopTask()
		pts = []
		for p in points:
			p = [self.boundRect.x() + (p.x() * self.boundRect.width()), self.boundRect.y() + (p.y() * self.boundRect.height())]
			p[0] = max(-10, min(p[0], 10))
			p[1] = max(-10, min(p[1], 10))
			pts.append(p)
		data = np.array([p[1] for p in pts] + [-p[0] for p in pts], dtype=np.float64) # sent as (y, -x)
		samps = len(data)//2
		#self.analog_output.WriteAnalogF64(samps,1,-1,DAQmx_Val_GroupByChannel,data,byref(self.read),None)
		print("Shape: %s" % [l.active and self.active for l in self.lasers])