from qtpy import QtWidgets, QtGui, QtCore
import numpy as np
from . import global_vars as g

class CrossHair(QtWidgets.QGraphicsObject):
	'''draggable crosshair object that acts as an aimer in a QGraphics Scene'''
	sigMoved = QtCore.Signal(object)
	def __init__(self, parent=None, size=7, color = QtCore.Qt.red, pos=QtCore.QPointF(0, 0)):
		QtWidgets.QGraphicsObject.__init__(self, parent)
		self.pen = QtGui.QPen(color)
		self.pen.setWidth(2)
		self.setZValue(10)
		self.setPos(pos)
		self.size = size
		self.dragging = False
		self.newPos = [None, None]
		self.xChanged.connect(lambda : self.setCoord(x=self.pos().x))
		self.yChanged.connect(lambda: self.setCoord(y=self.pos().y))

	def setCoord(self, x=None, y=None):
		if x != None:
			self.newPos[0] = x
		elif y != None:
			self.newPos[1] = y

		if all(self.newPos):
			self.sigMoved.emit(self.pos())
			self.newPos = [None, None]

	def paint(self, painter, option, widget):
		'''paint the crosshair'''
		painter.setPen(self.pen)
		painter.drawEllipse(self.boundingRect())
		painter.drawLine(-self.size, 0, self.size, 0)
		painter.drawLine(0, -self.size, 0, self.size)

	def boundingRect(self):
		'''shape to draw in'''
		return QtCore.QRectF(-self.size - 1, -self.size - 1, 2 * self.size + 2, 2 * self.size + 2)



class GalvoLine(QtWidgets.QGraphicsPathItem):
	def __init__(self, pos):
		self.path = QtGui.QPainterPath(pos)
		super(GalvoLine, self).__init__(self.path)
		self.start = pos
		self.end = pos
		self.path_pen = QtGui.QPen(QtGui.QColor(0, 0, 255))
		self.path_pen.setWidth(2)
		self.setPen(self.path_pen)
		self.setPath(self.path)
		self.mouseIsOver = False

	def paint(self, painter, option, *arg):
		if self.visible:
			painter.setRenderHint(QtGui.QPainter.Antialiasing)
			QtWidgets.QGraphicsPathItem.paint(self, painter, option, *arg)
			painter.setPen(QtGui.QColor(0, 255, 0))
			painter.drawText(self.start.x(), self.start.y(), 'S')
			painter.setPen(QtGui.QColor(255, 0, 0))
			painter.drawText(self.end.x(), self.end.y(), 'E')

	def boundingRect(self):
		newRect = QtWidgets.QGraphicsPathItem.boundingRect(self)
		newRect.adjust(-5, -5, 5, 5)
		return newRect

	def mouseOver(self, pos):
		self.mouseIsOver = self.boundingRect().contains(pos)

	def addPoint(self, p):
		self.path.lineTo(p)
		self.setPath(self.path)
		self.end = p
		self.update()

	def setSelected(self, s):
		self.selected = s
		if self.selected:
			self.path_pen.setColor(QtGui.QColor(255, 0, 0))
		else:
			self.path_pen.setColor(QtGui.QColor(0, 0, 255))
		self.setPen(self.path_pen)
		self.update()

	def rasterPoints(self, count):
		return [self.path.pointAtPercent(i / float(count)) for i in range(count)]

class GalvoStraightLine(QtWidgets.QGraphicsPathItem):
	def __init__(self, posA, posB):
		self.path = QtGui.QPainterPath(posA)
		self.path.lineTo(posB)
		super(GalvoStraightLine, self).__init__(self.path)
		self.start = posA
		self.end = posB
		path_pen = QtGui.QPen(QtGui.QColor(0, 0, 255))
		path_pen.setWidth(2)
		self.setPen(path_pen)
		self.setPath(self.path)
		self.midDraw = False

	def paint(self, painter, option, *arg):
		painter.setRenderHint(QtGui.QPainter.Antialiasing)
		#QtGui.QGraphicsPathItem.paint(self, painter, option, *arg)
		pen = QtGui.QPen(QtGui.QColor(0, 0, 255))
		pen.setWidth(4)
		painter.setPen(pen)
		f = QtGui.QFont('Arial', 13, weight=1)
		f.setBold(True)
		painter.setFont(f)
		painter.drawPoints(*self.rasterPoints())
		painter.setPen(QtGui.QColor(0, 255, 0))
		painter.drawText(self.start.x(), self.start.y(), 'S')
		painter.setPen(QtGui.QColor(255, 0, 0))
		painter.drawText(self.end.x(), self.end.y(), 'E')

	def boundingRect(self):
		newRect = QtWidgets.QGraphicsPathItem.boundingRect(self)
		newRect.adjust(-10, -10, 10, 10)
		return newRect

	def setStart(self, p):
		self.start = p
		self.end = p
		self.path = QtGui.QPainterPath(self.start)
		self.path.lineTo(self.end)
		self.setPath(self.path)
		self.update()
		self.midDraw = True

	def setEnd(self, e, finish=False):
		self.end = e
		self.path = QtGui.QPainterPath(self.start)
		self.path.lineTo(self.end)
		self.setPath(self.path)
		self.update()
		if finish:
			self.midDraw = False

	def rasterPoints(self):
		return [self.path.pointAtPercent(i / (g.intervals - 1.)) for i in range(g.intervals)]

class GalvoShape(GalvoLine):
	def __init__(self, pos):
		super(GalvoShape, self).__init__(pos)

	def paint(self, painter, option, *arg):
		painter.setRenderHint(QtGui.QPainter.Antialiasing)
		QtWidgets.QGraphicsPathItem.paint(self, painter, option, *arg)
		ps = self.rasterPoints()
		if len(ps) > 0:
			painter.drawPolyline(*ps)
			#painter.drawLines(*ps)
			#painter.drawPoints(*ps)

	def mouseOver(self, pos):
		self.mouseIsOver = self.path.contains(pos)
		return self.mouseIsOver

	def close(self):
		self.path.closeSubpath()
		self.setPath(self.path)
		self.update()

	def rasterPoints(self):
		raster = []
		r = self.path.boundingRect()
		r.setHeight(1)
		rect = QtGui.QPainterPath()
		rect.addRect(r)	#create painterPath of the top of the boundRect
		i = 0
		step = g.ui.lineSepCounter.maximum() - g.intervals + 1
		step = g.intervals
		while rect.boundingRect().y() < self.path.boundingRect().bottom():	# while the y-val is above the boundRect
			r = self.path.intersected(rect).boundingRect()
			if i % 2 == 0:
				raster.extend([QtCore.QPointF(x, r.top()) for x in np.arange(r.left(), r.right(), step)])
			else:
				raster.extend([QtCore.QPointF(x, r.top()) for x in np.arange(r.right(), r.left(), -step)])

			rect.translate(0, step) #translate the raster down slightly
			i += 1
		return raster

	def rasterPath(self):
		ps = self.rasterPoints()
		if len(ps) == 0:
			return QtGui.QPainterPath()
		raster = QtGui.QPainterPath(ps[0])
		for p in ps[1:]:
			raster.lineTo(p)
		return raster
