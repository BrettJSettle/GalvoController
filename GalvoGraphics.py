from PyQt4 import QtGui, QtCore
import numpy as np

class CrossHair(QtGui.QGraphicsObject):
	'''draggable crosshair object that acts as an aimer in a QGraphics Scene'''
	sigMoved = QtCore.pyqtSignal(object)
	def __init__(self, parent=None, size=7, color = QtCore.Qt.red, pos=QtCore.QPointF(0, 0)):
		QtGui.QGraphicsObject.__init__(self, parent)
		self.pen = QtGui.QPen(color)
		self.pen.setWidth(2)
		self.setZValue(10)
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

	def boundingRect(self):
		'''shape to draw in'''
		return QtCore.QRectF(-self.size - 1, -self.size - 1, 2 * self.size + 1, 2 * self.size + 1)

class GalvoShape(QtGui.QGraphicsPathItem):
	RASTER_GAP = 3
	def __init__(self, pos):
		self.path = QtGui.QPainterPath(pos)
		super(GalvoShape, self).__init__(self.path)

		self.path_pen = QtGui.QPen(QtGui.QColor(0, 0, 255))
		self.path_pen.setWidth(2)
		self.setPen(self.path_pen)
		self.setPath(self.path)
		self.mouseIsOver = False
		self.selected = False

	def paint(self, painter, option, *arg):
		painter.setRenderHint(QtGui.QPainter.Antialiasing)
		QtGui.QGraphicsPathItem.paint(self, painter, option, *arg)
		ps = self.rasterPoints()
		if len(ps) > 0:
			painter.drawPoints(*ps)

	def mouseOver(self, pos):
		self.mouseIsOver = self.path.contains(pos)

	def addPoint(self, p):
		self.path.lineTo(p)
		self.setPath(self.path)
		self.update()

	def setSelected(self, s):
		self.selected = s
		if self.selected:
			self.path_pen.setColor(QtGui.QColor(255, 0, 0))
		else:
			self.path_pen.setColor(QtGui.QColor(0, 0, 255))
		self.setPen(self.path_pen)
		self.update()

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
		while rect.boundingRect().y() < self.path.boundingRect().bottom():	# while the y-val is above the boundRect
			r = self.path.intersected(rect).boundingRect()
			raster.extend([QtCore.QPointF(x, r.top()) for x in np.arange(r.left(), r.right(), GalvoShape.RASTER_GAP)])
			rect.translate(0, GalvoShape.RASTER_GAP) #translate the raster down slightly
		return raster

	def rasterPath(self):
		ps = self.rasterPoints()
		if len(ps) == 0:
			return QtGui.QPainterPath()
		raster = QtGui.QPainterPath(ps[0])
		for p in ps[1:]:
			raster.lineTo(p)
		return raster
