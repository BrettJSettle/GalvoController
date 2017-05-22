from qtpy import QtWidgets, QtCore, QtGui, uic
import sys, time, os
from threading import Timer

from . import global_vars as g
from .config import LaserConfigureWindow
from .galvoDriver import GalvoScene

app = None

class GalvoController(QtWidgets.QMainWindow):
	def __init__(self):
		QtWidgets.QMainWindow.__init__(self)
		uic.loadUi(os.path.join(os.path.dirname(__file__), 'galvoController.ui'), self)
		self.scene = GalvoScene()
		g.ui = self
		self.configWindow = LaserConfigureWindow()
		self.configWindow.sigAccepted.connect(self.settingsChanged)
		self.graphicsView.setScene(self.scene)
		self.scene.setSceneRect(QtCore.QRectF(self.graphicsView.rect()))
		self._connect_signals()

	def showEvent(self, ev):
		try:
			g.load_settings()
		except Exception as e:
			print(e)
		self.scene.galvo.setLaserActive((0, 1), False)

	def closeEvent(self, ev):
		self.scene.galvo.setLaserActive((0, 1), False)
		if self.actionAutosave.isChecked():
			g.save_settings()
		sys.exit(0)

	def showHelp(self):
		self.helpText = QtWidgets.QTextBrowser()
		self.helpText.setOpenExternalLinks(True)
		self.helpText.setHtml("""
<h1 style="width:100%; height:20%; text-align:center;">Galvonmeter Controller</h1>
<div style="width:90%; height: 70%; margin:5%; background: #CCCCCC">
	<p style="padding:10px"> The Galvonmeter control software communicates with a 2 dimensional laser control system via the National Instruments USB 6001</p>
	<p>The pin information for the device can be found in the Laser Configuration Dialog.

	The program will automatically run in DEBUG mode if the Data Acquisition device is not detected. Once the device is detected, there are a few simple steps:
	<ul>
	  <li>Ensure the pins are set correctly (and optionally name your lasers), by going to Settings>Configure Ports</li>
	  <li>Toggle the lasers with the large named buttons to ensure both work correctly</li>
	  <li>Relocate and resize the window to span over your view</li>
	  <li>Set the opacity of the window so you can see the image behind it</li>
	  <li>Calibrate the controller so that the laser lies beneath the red crosshair</li>
	</ul>
	</p>
	<br>
	<p>Once the calibration is complete, use the mouse to move the crosshair, or draw a line or ROI to specify a path for the laser<p>
</div>
			""")
		self.helpText.setReadOnly(True)
		self.helpText.show()
		self.helpText.window().resize(700, 500)

	def _connect_signals(self):

		self.actionShow_Help.triggered.connect(self.showHelp)
		self.clearButton.pressed.connect(self.scene.clear)
		self.closeButton.pressed.connect(self.close)

		self.laser1Button.pressed.connect(lambda : self.pressed(0))
		self.laser1Button.released.connect(lambda : self.released(0))
		self.pulseButton.pressed.connect(lambda : self.pulse(0))

		self.laser2Button.pressed.connect(lambda : self.pressed(1))
		self.laser2Button.released.connect(lambda : self.released(1))
		self.pulse2Button.pressed.connect(lambda : self.pulse(1))

		self.roiButton.pressed.connect(lambda : self.scene.setDrawMethod('ROI'))
		self.lineButton.pressed.connect(lambda : self.scene.setDrawMethod('Line'))
		self.pointButton.pressed.connect(lambda : self.scene.setDrawMethod('Point'))
		self.lineSepCounter.valueChanged.connect(lambda v: setattr(g, 'intervals', v))
		self.lineSepCounter.valueChanged.connect(lambda v: [roi.update() for roi in self.scene.rois] if self.scene.drawMethod == 'ROI' else self.scene.line.update())

		self.opacitySlider.valueChanged.connect(lambda v: self.setWindowOpacity(v/100.))
		self.opacitySlider.setValue(85)

		self.actionConfigure.triggered.connect(self.configure)
		self.actionCalibrate.triggered.connect(self.calibrate)
		self.actionReset.triggered.connect(self.reset)
		self.actionDisconnect.triggered.connect(lambda : sys.exit(0))
		self.actionImport.triggered.connect(lambda : g.import_settings(QtWidgets.QFileDialog.getOpenFileName(filter='Pickled files (*.p)')))
		self.actionExport.triggered.connect(lambda : g.export_settings(QtWidgets.QFileDialog.getSaveFileName(filter='Pickled files (*.p)')))
		
		self.scene.galvo.lasers[0].sigRenamed.connect(self.laser1Button.setText)
		self.scene.galvo.lasers[1].sigRenamed.connect(self.laser2Button.setText)

	def configure(self):
		self.configWindow.update(self.scene.galvo.lasers)
		self.configWindow.show()

	def settingsChanged(self, lasers):
		self.scene.galvo.lasers[0].rename(lasers[0]['name'])
		self.scene.galvo.lasers[1].rename(lasers[1]['name'])
		self.scene.galvo.lasers[0].changePin(lasers[0]['pin'])
		self.scene.galvo.lasers[1].changePin(lasers[1]['pin'])

	def reset(self):
		self.pointButton.click()
		self.scene.center()
		self.scene.resetBounds()

	def calibrate(self):
		''' Require the user to aim the curson in the top left and bottom right corners to set the boundaries of the controller
		'''
		self.setFixedSize(self.size())
		self.reset()
		aimRect = QtCore.QRectF(self.graphicsView.mapToScene(0, 0), self.graphicsView.mapToScene(20, 20))
		aim = QtWidgets.QGraphicsRectItem(aimRect)
		aim.setBrush(QtGui.QColor(255, 0, 0))
		self.scene.addItem(aim)
		font = QtGui.QFont("Helvetica", 15, 3)
		ti = self.scene.addText('Position the laser in optimal top\n   left, then press any key', font = font)
		self.scene.keyPressEvent = lambda ev: setattr(self.scene, 'tempRect', QtCore.QRectF(self.scene.galvo.pos, QtCore.QSizeF()))
		while not hasattr(self.scene, 'tempRect'):
			QtWidgets.qApp.processEvents()
			time.sleep(.01)
		aimRect.moveTo(self.graphicsView.mapToScene(self.graphicsView.width() - 20, self.graphicsView.height() - 20))
		aim.setRect(aimRect)
		self.scene.keyPressEvent = lambda ev: self.scene.tempRect.setSize(QtCore.QSizeF(self.scene.galvo.pos.x() - self.scene.tempRect.x(), self.scene.galvo.pos.y() - self.scene.tempRect.y()))
		ti.setPlainText('Now position the laser in optimal bottom \n      right, and press a key')
		while self.scene.tempRect.isEmpty():
			app.processEvents()
			time.sleep(.01)
		self.scene.removeItem(aim)
		self.scene.keyPressEvent = lambda ev: GalvoScene.keyPressEvent(self.scene, ev)
		self.scene.galvo.setBounds(self.scene.tempRect)
		del self.scene.tempRect
		self.scene.removeItem(ti)
		self.setMaximumSize(2000,2000)
		self.setMinimumSize(0,0)

	def pulse(self, num):
		''' Activate the laser (with id 'num') for a given amount of time. Works with Line, ROI, and crosshair
		Generate raster points by roi type
		'''
		laser = self.scene.galvo.lasers[num]
		if any([laser.active for laser in self.scene.galvo.lasers]):
			return
		pulse_time = self.pulseSpin.value() / 1000.0
		if self.scene.drawMethod == 'Line':
			pts = [self.scene.mapToGalvo(p) for p in self.scene.line.rasterPoints()]
			timers = [Timer(i * pulse_time/g.intervals, self.scene.galvo.moveTo, args = (pts[i],)) for i in range(len(pts))]
			timers.append(Timer(pulse_time, self.scene.galvo.setLaserActive, args = (num, False)))
			self.scene.galvo.setLaserActive(num, True)
			[ti.start() for ti in timers]
		elif self.scene.drawMethod == 'ROI':
			ps = []
			for roi in self.scene.rois:
				ps.extend([self.scene.mapToGalvo(p) for p in roi.rasterPoints()])
			self.scene.galvo.setLaserActive(num, True)
			Timer(pulse_time, self.scene.galvo.setLaserActive, args=(num, False)).start()
			self.scene.galvo.write_points(ps)
		else:
			self.scene.galvo.setLaserActive(num, True)
			Timer(pulse_time, self.scene.galvo.setLaserActive, args=(num, False)).start()

	def pressed(self, num):
		laser = self.scene.galvo.lasers[num]
		button = [self.laser1Button, self.laser2Button][num]
		button.presstime = time.time()
		if not button.isChecked():
			if self.scene.drawMethod == 'Point':
				self.scene.galvo.setLaserActive(num, True)

	def released(self, num):
		laser = self.scene.galvo.lasers[num]
		button = [self.laser1Button, self.laser2Button][num]
		if time.time() - button.presstime > .2: # used as manual button
			button.setChecked(False)
			self.scene.galvo.setLaserActive(num, False)
		elif not button.isChecked():
			self.scene.galvo.setLaserActive(num, button.isChecked())

def main():
	global app
	app = QtWidgets.QApplication([])
	controller = GalvoController()
	controller.show()
	app.exec_()
