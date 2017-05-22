from qtpy import QtWidgets, uic, QtCore
import os

class LaserConfigureWindow(QtWidgets.QWidget):
	''' Dialog window used to set the Analog pins used to toggle lasers
	'''
	sigAccepted = QtCore.Signal(list)
	def __init__(self):
		QtWidgets.QWidget.__init__(self)
		uic.loadUi(os.path.join(os.path.dirname(__file__), 'laserConfig.ui'), self)
		self.buttonBox.accepted.connect(self.accepted)
		self.buttonBox.rejected.connect(self.rejected)

	def update(self, lasers):
		self.laser1nameEdit.setText(lasers[0].name)
		self.laser2nameEdit.setText(lasers[1].name)
		self.__dict__['laser1pin%d' % lasers[0].pin].setChecked(True)
		self.__dict__['laser2pin%d' % lasers[1].pin].setChecked(True)

	def accepted(self):
		pin1 = [self.__dict__['laser1pin%d' % i].isChecked() for i in range(8)].index(True)
		pin2 = [self.__dict__['laser2pin%d' % i].isChecked() for i in range(8)].index(True)
		results = [{'name': self.laser1nameEdit.text(), 'pin': pin1}, {'name': self.laser2nameEdit.text(), 'pin': pin2}]
		self.sigAccepted.emit(results)
		self.close()

	def rejected(self):
		self.close()

if __name__ == '__main__':
	app = QtWidgets.QApplication([])
	c = LaserConfigureWindow()
	c.show()
	app.exec_()
