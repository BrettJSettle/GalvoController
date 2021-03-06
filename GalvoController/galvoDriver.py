from qtpy import QtGui, QtCore, QtWidgets
import numpy as np
from .galvoGraphics import *
import sys
from . import global_vars as g

def byref_str(s):
	''' Duplicate function used for debug mode
	'''
	return "ref(%s)" % s

if not g.DEBUG:  # try to import PyDAQmx and connect to machine. On fail, enter DEBUG MODE
	try:
		from PyDAQmx import *
		from PyDAQmx.DAQmxCallBack import *
	except:
		print("Could not import PyDAQmx. Running in Debug mode")
		g.DEBUG = True

if g.DEBUG:	# set values if PyDAQmx failed
	DAQmx_Val_Volts = 'DAQmx_Val_Volts'
	DAQmx_Val_ChanForAllLines = 'DAQmx_Val_ChanForAllLines'
	DAQmx_Val_GroupByChannel = "DAQmx_Val_GroupByChannel"
	byref = byref_str

import time

class Laser(QtCore.QObject):
	''' Represents a laser connected to the USB-6001. Stores laser name, pin number, and state
	'''
	sigRenamed = QtCore.Signal(str)
	def __init__(self, name, pin):
		super(Laser, self).__init__()
		self.name = name
		self.pin = pin
		self.active = False
	def setActive(self, a):
		self.active = a
	def rename(self, s):
		self.name = s
		self.sigRenamed.emit(s)
	def changePin(self, p):
		self.pin = p
	
class GalvoScene(QtWidgets.QGraphicsScene):
	''' Interactive area on GUI for crosshair and ROI control
	'''
	def __init__(self, **kargs):
		super(GalvoScene, self).__init__(**kargs)
		self.galvo = GalvoDriver()
		self.crosshair = CrossHair()
		self.crosshair.sigMoved.connect(self.crosshairMoved)
		self.addItem(self.crosshair)
		self.line = GalvoStraightLine(QtCore.QPointF(-100, 0), QtCore.QPointF(0, 0))
		self.line.setVisible(False)
		self.addItem(self.line)
		self.drawMethod = 'Point'
		self.rois = []
		self.currentROI = None

	def crosshairMoved(self, pos):
		pos = self.mapToGalvo(pos)
		if not (0 <= pos.x() <= 1 and 0 <= pos.y() <= 1):
			pos.setX(min(1, max(0, pos.x())))
			pos.setY(min(1, max(0, pos.y())))
			self.crosshair.setPos(self.views()[0].mapToScene(self.views()[0].width() * pos.x(), self.views()[0].height() * pos.y()))
		self.galvo.moveTo(pos)

	def setDrawMethod(self, method):
		self.drawMethod = method
		self.crosshair.setVisible(method == 'Point')
		for roi in self.rois:
			roi.setVisible(method == 'ROI')
		self.line.setVisible(method == 'Line' and self.line.start.x() != -100)

		g.ui.laser1Button.setEnabled(method == 'Point')
		g.ui.laser2Button.setEnabled(method == 'Point')


		g.ui.intervalTypeLabel.setText("Line Intervals:" if method == 'Line' else 'Mesh Size:')

	def mousePressEvent(self, ev):
		if self.drawMethod =='Point':
			self.crosshair.setPos(ev.scenePos())
			self.crosshair.dragging = ev.button() == QtCore.Qt.RightButton
		else:
			if ev.button() == QtCore.Qt.RightButton:  # if right button, enable crosshair movement
				if self.drawMethod =='ROI':
					for i in range(len(self.rois) - 1, -1, -1):
						if self.rois[i].mouseOver(ev.scenePos()):
							self.removeItem(self.rois[i])
							self.rois.pop(i)
			elif ev.button() == QtCore.Qt.LeftButton:
				if self.drawMethod == "ROI":
					self.currentROI = GalvoShape(ev.scenePos())
					self.addItem(self.currentROI)
				elif self.drawMethod == "Line":
					self.line.setVisible(True)
					if not self.line.midDraw:
						self.line.setStart(ev.scenePos())
					else:
						self.line.setEnd(ev.scenePos(), finish=True)
		QtWidgets.QGraphicsScene.mousePressEvent(self, ev)

	def mouseMoveEvent(self, ev):
		if self.drawMethod == 'Point' and self.crosshair.dragging:
			self.crosshair.setPos(ev.scenePos())
		elif isinstance(self.currentROI, GalvoShape):
			self.currentROI.addPoint(ev.scenePos())
		elif self.line.midDraw:
			self.line.setEnd(ev.scenePos())

		QtWidgets.QGraphicsScene.mouseMoveEvent(self, ev)

	def mouseReleaseEvent(self, ev):
		self.crosshair.dragging = False
		if ev.button() == QtCore.Qt.RightButton:
			pass
		elif ev.button() == QtCore.Qt.LeftButton:
			if isinstance(self.currentROI, GalvoShape):
				self.currentROI.close()
				if self.currentROI.path.length() > 50:
					self.rois.append(self.currentROI)
				else:
					self.removeItem(self.currentROI)
			if self.line.midDraw:
				if (ev.scenePos() - self.line.start).manhattanLength() > 5:
					self.line.setEnd(ev.scenePos(), finish=True)

		self.currentROI = None
		QtWidgets.QGraphicsScene.mouseReleaseEvent(self, ev)

	def center(self):
		self.setDrawMethod("Point")
		self.crosshair.setPos(self.views()[0].mapToScene(self.views()[0].width() * .5, self.views()[0].height() * .5))

	def clear(self):
		for i in self.rois:
			if isinstance(i, GalvoLine):
				self.removeItem(i)
		self.rois = []

	def resetBounds(self):
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
		self.lasers = (Laser('Laser 1', 0), Laser('Laser 2', 1))
		self.shapes = []
		self.duration = -1

	def setShapes(self, shapes):
		self.shapes = shapes
		if len(shapes) > 0 and not self.isRunning():
			self.start()

	def setBounds(self, boundRect):
		self.boundRect = boundRect
		
class DebugDriver():
	def __getattr__(self, attr):
		print(attr)
		return print

class GalvoDriver(GalvoBase):
	'''implementation of Galvo Driver that sends one coordinate at a time similar to a QGraphicsObject,
	handles maximum and minimum values accordingly'''
	boundRect = QtCore.QRectF(-10, -10, 20, 20)
	def __init__(self):
		super(GalvoDriver, self).__init__()
		self.sample_rate=5000 # Maximum for the NI PCI-6001 is 5kHz.
		self.bufferSize=2
		if not g.DEBUG:
			self.read = int32()
			self.establishChannels()
		else:
			self.read = 'int32'
			self.analog_output = DebugDriver()
			self.digital_output = DebugDriver()

	def establishChannels(self):
		self.analog_output = Task()
		self.analog_output.CreateAOVoltageChan(b'Dev1/ao0',b"",-10.0,10.0,DAQmx_Val_Volts,None)
		self.analog_output.CreateAOVoltageChan(b"Dev1/ao1",b"",-10.0,10.0,DAQmx_Val_Volts,None)
		self.digital_output = Task()
		self.digital_output.CreateDOChan(b'Dev1/port0/line0:7',b"",DAQmx_Val_ChanForAllLines)
		#self.analog_output.CfgSampClkTiming("", 50, DAQmx_Val_Rising, DAQmx_Val_ContSamps, self.bufferSize) 

	def setLaserActive(self, num, active):
		if type(num) in (list, tuple):
			for n in num:
				self.lasers[n].setActive(active)
		else:
			self.lasers[num].setActive(active)
		self.updateDigital()

	def updateDigital(self, active=True):
		digital_data = np.uint8([0, 0, 0, 0, 0, 0, 0, 0])
		if active:
			for i in self.lasers:
				if i.active:
					digital_data[i.pin] = 1
		self.digital_output.WriteDigitalLines(1,1,-1,DAQmx_Val_ChanForAllLines,digital_data,None,None)
		if any(digital_data) and len(self.shapes) > 0 and not self.isRunning():
			self.start()

	def timedDraw(self, path, totalTime):
		pointCount = path.length() / 5
		points = [path.pointAtPercent(i) for i in np.linspace(0., 1., pointCount)]
		pts = []
		for p in points:
			pts.append(self.mapFromPercent(p))
		data = np.array([p.y() for p in pts] + [-p.x() for p in pts], dtype=np.float64) # sent as (y, -x)
		samps = len(data)//2
		self.analog_output.WriteAnalogF64(samps,1,-1,DAQmx_Val_GroupByChannel,data,byref(self.read),None)

	def run(self):
		while len(self.shapes) > 0 and (self.lasers[0].active or self.lasers[1].active):
			if len(self.shapes) > 1:	# draw multiple shapes, jumping between
				for shape in self.shapes:
					self.moveTo(shape[0], penUp=True)
					self.write_points(shape)
			elif len(self.shapes) == 1:	# draw one shape, top to bottom to top again
				self.write_points(self.shapes[0][:-1] + self.shapes[0][::-1])
				
	def mapFromPercent(self, p): 
		p = [self.boundRect.x() + (p.x() * self.boundRect.width()), self.boundRect.y() + (p.y() * self.boundRect.height())]
		return QtCore.QPointF(max(-10, min(p[0], 10)),  max(-10, min(p[1], 10)))

	def moveTo(self, pos, penUp=False):
		''' Send the new position to the galvonmeter
		Parameters:
			pos: new XY coordinate of the crosshair, within range
		'''
		pos = self.mapFromPercent(pos)
		self.pos = pos
		if penUp:
			self.updateDigital(active=False)
		data = np.array([pos.y(), pos.y(), -pos.x(), -pos.x()], dtype=np.float64)
		self.analog_output.WriteAnalogF64(self.bufferSize,1,-1,DAQmx_Val_GroupByChannel,data,byref(self.read),None)
		if penUp:
			self.updateDigital()
		#g.ui.statusBar().showMessage("Crosshair at position (%.3f, %.3f)" % (self.pos.x(), self.pos.y()))

	def write_points(self, points):
		self.analog_output.StopTask()
		pts = []
		for p in points:
			pts.append(self.mapFromPercent(p))
		data = np.array([p.y() for p in pts] + [-p.x() for p in pts], dtype=np.float64) # sent as (y, -x)
		samps = len(data)//2
		self.analog_output.WriteAnalogF64(samps,1,-1,DAQmx_Val_GroupByChannel,data,byref(self.read),None)
