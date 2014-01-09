import sys
from PyQt4 import QtGui, QtCore, uic

class MainApp(QtGui.QMainWindow):
	def __init__(self):
		QtGui.QMainWindow.__init__(self)
 
		self.ui              = uic.loadUi('mainWindow2.ui')
		self.waferInspector  = uic.loadUi('waferProperties.ui')
		self.dieInspector    = uic.loadUi('dieProperties.ui')
		self.sampleInspector = uic.loadUi('sampleProperties.ui')
		self.waferDisplay    = DrawWafer(controller              = self)

		# Load inspectors
		self.inspectorStack = QtGui.QStackedWidget()
		self.inspectorStack.addWidget(self.waferInspector)
		self.inspectorStack.addWidget(self.dieInspector)
		self.inspectorStack.addWidget(self.sampleInspector)

		# Fill the splitter
		self.ui.splitter.addWidget(self.waferDisplay)
		self.ui.splitter.addWidget(self.inspectorStack)

		# Connect the relevant ports
		self.waferInspector.waferName.textChanged.connect(self.changeWaferName)
		self.waferInspector.waferSubstrate.textChanged.connect(self.changeWaferSubstrate)
		self.waferInspector.waferNotes.textChanged.connect(self.changeWaferNotes)

		self.dieInspector.dieAnnealTemp.valueChanged.connect(self.changeDieTemp)
		self.dieInspector.dieAnnealTime.valueChanged.connect(self.changeDieTime)
		self.dieInspector.dieNotes.textChanged.connect(self.changeDieNotes)

		#self.ui.splitter.widget(1).dieAnnealTime.valueChanged.connect(self.ui.splitter.widget(1).dieAnnealTemp.setValue)
		self.ui.show()

		# Inspected State
		self.currentSelection = self.waferDisplay.waf

	def setCurrentSelection(self, selection):
		"""Set the correct inspector"""
		self.currentSelection = selection
		if isinstance(self.currentSelection, Die):
			self.inspectorStack.setCurrentIndex(1)
			self.dieInspector.dieAnnealTemp.setValue(self.currentSelection.annealTemp)
			self.dieInspector.dieAnnealTime.setValue(self.currentSelection.annealTime)
			self.dieInspector.dieNotes.setText(self.currentSelection.notes)
			self.dieInspector.dieName.setText("Row %d, Col %d" % (self.currentSelection.row+1, self.currentSelection.col+1))
		elif isinstance(self.currentSelection, Wafer):
			self.inspectorStack.setCurrentIndex(0)
		elif isinstance(self.currentSelection, Sample):
			self.inspectorStack.setCurrentIndex(2)
		else:
			print "Invalid Inspector"
			raise 

	def changeWaferName(self, string):
		self.currentSelection.name = string
	def changeWaferSubstrate(self, string):
		self.currentSelection.substrate = string
	def changeWaferNotes(self):
		self.currentSelection.notes = self.waferInspector.waferNotes.toPlainText()
	def changeDieTemp(self, value):
		self.currentSelection.annealTemp = value
	def changeDieTime(self, value):
		self.currentSelection.annealTime = value
	def changeDieNotes(self):
		self.currentSelection.notes = self.dieInspector.dieNotes.toPlainText()

class DrawWafer(QtGui.QWidget):
	def __init__(self, controller, parent=None):
		QtGui.QWidget.__init__(self, parent)
		self.controller = controller
		# setGeometry(x_pos, y_pos, width, height)
		self.setGeometry(300, 300, 350, 350)
		self.setWindowTitle('Draw circles')
		sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
		sizePolicy.setHeightForWidth(True)
		sizePolicy.setWidthForHeight(True)
		self.setSizePolicy(sizePolicy)
		self.thingy = 12342349.0
		self.waf = Wafer(5,5,5,8, controller=self.controller, parent=self)

	def sizeHint(self):
		return QtCore.QSize(400, 400)

	def heightForWidth(self, width):
		return width * 1.0

	def widthForHeight(self, height):
		return height * 1.0

	def paintEvent(self, event):
		paint = QtGui.QPainter()
		paint.begin(self)
		paint.setRenderHint(QtGui.QPainter.Antialiasing)
		
		# Background
		paint.setBrush(QtCore.Qt.white)
		paint.drawRect(event.rect())

		# Dimensions
		w = self.size().width()
		h = self.size().height()
		self.centerX = 0.5*w
		self.centerY = 0.5*h
		margin  = 10.0*w/1000.0
		diameter = min(w,h)-20.0
		radius   = diameter/2.0

		# Move to centered coordinates with usual (x,y) conventions
		paint.save()
		paint.translate(self.centerX, self.centerY)
		paint.scale(1, -1)

		self.waf.draw(paint, diameter, self.centerX, self.centerY)

		paint.restore()
		paint.end()

	def mousePressEvent(self, event):
		super(DrawWafer, self).mousePressEvent(event)
		#print "Mouse press in main area:",  event.button(), event.pos()
		#self.parent().widget(1).dieNotes.setText("Coords %f,%f" % (event.x(), event.y()))
		position = QtCore.QPointF(event.pos())
		if not self.waf.checkMousePressEvent(event, self.centerX, self.centerY):
			#print "Click within wafer"
			self.controller.setCurrentSelection(self.waf)

class Wafer(QtGui.QWidget):
	def __init__(self, dieRows, dieCols, sampleRows, sampleCols, controller=None, parent=None):
		QtGui.QWidget.__init__(self, parent)
		self.controller   = controller
		self.name         = ""
		self.substrate    = ""
		self.notes        = ""
		self.status       = -1
		self.sampleRows   = sampleRows
		self.sampleCols   = sampleCols
		self.dieRows      = dieRows
		self.dieCols      = dieCols
		self.dies         = [[Die(i, j, dieRows, dieCols, controller=self.controller, parent=self) for j in range(dieCols)] for i in range(dieRows)]

	def draw(self, paint, diameter, centerX, centerY):
		
		# Draw the actual wafer
		radius = diameter*0.5
		paint.setPen(QtCore.Qt.black)
		paint.setBrush(QtGui.QColor(220, 220, 220))
		boundingRect = QtCore.QRectF(-radius, -radius, diameter, diameter)
		paint.drawChord(boundingRect, 290*16, 320*16)

		# Draw the dies
		self.boxSize   = 1.3*radius
		self.dieMargin = 4*self.boxSize/800.0
		self.sizeX     = (self.boxSize - (self.dieCols-1)*self.dieMargin)/self.dieCols
		self.sizeY     = (self.boxSize - (self.dieRows-1)*self.dieMargin)/self.dieRows
		for i, row in enumerate(self.dies):
			for j, die in enumerate(row):
				transX = (j-0.5*(self.dieCols-1))*(self.sizeX+self.dieMargin)
				transY = (i-0.5*(self.dieRows-1))*(self.sizeY+self.dieMargin)
				paint.save()
				paint.translate(transX, transY)
				die.draw(paint, self.sizeX, self.sizeY)
				paint.restore()

	def checkMousePressEvent(self, event, centerX, centerY):
		for i, row in enumerate(self.dies):
			for j, die in enumerate(row):
				eventX = event.x() - centerX
				eventY = event.y() - centerY
				transX = (j-0.5*(self.dieCols-1))*(self.sizeX+self.dieMargin)
				transY = (i-0.5*(self.dieRows-1))*(self.sizeY+self.dieMargin)
				if (-0.5*self.sizeX <= eventX-transX <= 0.5*self.sizeX):
					#print "Within die %d,%d column" % (i,j)
					if (-0.5*self.sizeY <= eventY-transY <= 0.5*self.sizeY):
						# Check to see if we hit a die too
						if not self.dies[i][j].checkMousePressEvent(eventX-transX, eventY-transY):
							#print "Click within die %d,%d" % (i+1,j+1)
							self.controller.setCurrentSelection(self.dies[i][j])
						# Return true if we hit anything
						return True
		return False
						

class Die(QtGui.QWidget):
	def __init__(self, thisRow, thisCol, sampleRows, sampleCols, controller=None, parent=None):
		QtGui.QWidget.__init__(self, parent)
		self.controller   = controller
		self.sampleRows   = sampleRows
		self.sampleCols   = sampleCols
		self.row          = thisRow
		self.col          = thisCol
		self.samples      = [[Sample(i, j, sampleRows, sampleCols, controller=self.controller) for j in range(sampleCols)] for i in range(sampleRows)]

		# Actual Values
		self.notes        = ""
		self.annealTemp   = 175.0
		self.annealTime   = 0.0

	def name(self):
		return "Die(%d,%d)" % (self.row, self.col)
	def draw(self, paint, sizeX, sizeY):
		# Draw the die
		self.sizeX = sizeX
		self.sizeY = sizeY
		paint.drawRect(-0.5*self.sizeX,-0.5*self.sizeY, self.sizeX, self.sizeY)

		# Draw the devices
		self.sampleMargin = 4*self.sizeX/100.0
		self.sizeX     = ((self.sizeX-4*self.sampleMargin) - (self.sampleCols-1)*self.sampleMargin)/self.sampleCols
		self.sizeY     = ((self.sizeY-4*self.sampleMargin) - (self.sampleRows-1)*self.sampleMargin)/self.sampleRows
		for i, row in enumerate(self.samples):
			for j, dev in enumerate(row):
				transX = (j-0.5*(self.sampleCols-1))*(self.sizeX+self.sampleMargin)
				transY = (i-0.5*(self.sampleRows-1))*(self.sizeY+self.sampleMargin)
				paint.save()
				paint.translate(transX, transY)
				dev.draw(paint, self.sizeX, self.sizeY)
				paint.restore()

	def checkMousePressEvent(self, eventX, eventY):
		for i, row in enumerate(self.samples):
			for j, die in enumerate(row):
				transX = (j-0.5*(self.sampleCols-1))*(self.sizeX+self.sampleMargin)
				transY = (i-0.5*(self.sampleRows-1))*(self.sizeY+self.sampleMargin)
				#print "Checking for samples", eventX, eventY, transX, transY
				if (-0.5*self.sizeX <= eventX-transX <= 0.5*self.sizeX):
					#print "Within die %d,%d column" % (i,j)
					if (-0.5*self.sizeY <= eventY-transY <= 0.5*self.sizeY):
						#print "Click within sample %d,%d die %d,%d" % (i+1,j+1,self.row+1,self.col+1)
						self.controller.setCurrentSelection(self.samples[i][j])
						return True
		return False

class Sample(QtGui.QWidget):
	def __init__(self, thisRow, thisCol, parentRow, parentCol, controller=None, parent=None):
		QtGui.QWidget.__init__(self, parent)
		self.controller = controller
		self.row       = thisRow
		self.col       = thisCol
		self.parentRow = parentRow
		self.parentCol = parentCol

		self.notes        = ""
	def name(self):
		return "Die(%d,%d) Sample(%d,%d)" % (self.parentRow, self.parentCol, self.row, self.col)
	# def mousePressEvent(self, event):
	# 	print "Mouse press:",  event.button(), int(event.buttons()), self.name()
	def draw(self, paint, sizeX, sizeY):
		self.sizeX = sizeX
		self.sizeY = sizeY
		paint.drawRect(-0.5*self.sizeX,-0.5*self.sizeY, self.sizeX, self.sizeY)


if __name__ == "__main__":
	app = QtGui.QApplication(sys.argv)
	win = MainApp()
	sys.exit(app.exec_())