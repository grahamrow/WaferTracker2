#!/usr/bin/python

import sys
import PyQt4 as Qt
from PyQt4 import QtGui, QtCore, uic
import xml.etree.cElementTree as ElementTree


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

class NewWaferWindow(QtGui.QDialog):  # For configuring the lockin NewWafer
    def __init__(self, parent=None):
        super(NewWaferWindow, self).__init__(parent)
        self.ui = uic.loadUi("NewWafer.ui")
    def show(self):
        self.ui.show()

class MainApp(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.ui = uic.loadUi('mainWindow2.ui')
        self.waferInspector   = uic.loadUi('waferProperties.ui')
        self.dieInspector     = uic.loadUi('dieProperties.ui')
        self.sampleInspector  = uic.loadUi('sampleProperties.ui')
        self.new_wafer_window = NewWaferWindow(self)
        self.waferDisplay = DrawWafer(controller=self)
        self.filename = ""
        self.file_types = "Wafer Files (*.xml)"
        self.currentSelection  = None
        self.currentSelections = []

        # Load inspectors
        self.inspectorStack = QtGui.QStackedWidget()
        self.inspectorStack.addWidget(self.waferInspector)
        self.inspectorStack.addWidget(self.dieInspector)
        self.inspectorStack.addWidget(self.sampleInspector)

        # Fill the splitter
        self.scroller = QtGui.QScrollArea()
        self.scroller.setWidgetResizable(True)
        self.waferDisplay.setMinimumSize(300,300)
        self.ui.splitter.addWidget(self.scroller)
        self.scroller.setWidget(self.waferDisplay)
        self.ui.splitter.addWidget(self.inspectorStack)
        self.scroller.verticalScrollBar().valueChanged.connect(self.waferDisplay.repaint)
        self.scroller.horizontalScrollBar().valueChanged.connect(self.waferDisplay.repaint)

        #------------------------------------------------------------------
        # Display state
        #------------------------------------------------------------------
        self.showSamples = 1
        self.showAnnealing = 0

        #------------------------------------------------------------------
        # Connect general interface ports
        #------------------------------------------------------------------
        self.ui.showSamples.stateChanged.connect(self.setShowSamples)
        self.ui.showAnnealing.stateChanged.connect(self.setShowAnnealing)
        self.ui.showSamples.stateChanged.connect(self.waferDisplay.repaint)
        self.ui.showAnnealing.stateChanged.connect(self.waferDisplay.repaint)

        self.ui.actionSave_Wafer.triggered.connect(self.save)
        self.ui.actionSaveAs_Wafer.triggered.connect(self.saveAs)
        self.ui.actionOpen_Wafer.triggered.connect(self.open)
        self.ui.actionNew_Wafer.triggered.connect(self.new_wafer_window.show)
        self.new_wafer_window.ui.buttonBox.accepted.connect(self.new)

        #------------------------------------------------------------------
        # Connect the relevant ports to methods for setting object data
        #------------------------------------------------------------------

        # Wafer Inspector
        self.waferInspector.waferName.textChanged.connect(self.changeWaferName)
        self.waferInspector.waferSubstrate.textChanged.connect(self.changeWaferSubstrate)
        self.waferInspector.waferNotes.textChanged.connect(self.changeWaferNotes)

        # Die Inspector
        self.dieInspector.dieAnnealTemp.valueChanged.connect(self.changeDieTemp)
        self.dieInspector.dieAnnealTemp.valueChanged.connect(self.waferDisplay.repaint)
        self.dieInspector.dieAnnealTime.valueChanged.connect(self.changeDieTime)
        self.dieInspector.dieDead.stateChanged.connect(self.changeDieDead)
        self.dieInspector.dieDead.stateChanged.connect(self.waferDisplay.repaint)
        self.dieInspector.dieNotes.textChanged.connect(self.changeDieNotes)

        # Sample Inspector
        self.sampleInspector.sampleResLong.valueChanged.connect(self.changeSampleResLong)
        self.sampleInspector.sampleResTrans.valueChanged.connect(self.changeSampleResTrans)
        self.sampleInspector.sampleDimensions.textChanged.connect(self.changeSampleDimensions)
        self.sampleInspector.sampleNotes.textChanged.connect(self.changeSampleNotes)
        self.sampleInspector.sampleState.currentIndexChanged.connect(self.changeSampleState)
        self.sampleInspector.sampleState.currentIndexChanged.connect(self.waferDisplay.repaint)

        # Inspected State, which we rely upon to point to the correct object
        # self.setCurrentSelection(self.waferDisplay.waf)
        self.currentSelections = [self.waferDisplay.waf]

        self.ui.show()
    #
    # def getCurrentSelection(self):
    #     return self.currentSelection

    def setSelection(self, selection, append=False):
        if len(self.currentSelections) == 0 or not append:
            self.currentSelections = [selection]
        else:
            # Add to the selection only if the selection is of the same type
            # This seems like a reasonable way to use "type"... no inheritance to deal with
            if type(self.currentSelections[0]) == type(selection):
                self.currentSelections.append(selection)
            else:
                self.currentSelections = [selection]
            self.waferDisplay.repaint()

        if len(self.currentSelections) == 1:
            if isinstance(self.currentSelections[0], Die):
                self.inspectorStack.setCurrentIndex(1)
                self.dieInspector.dieAnnealTemp.setValue(self.currentSelections[0].annealTemp)
                self.dieInspector.dieAnnealTime.setValue(self.currentSelections[0].annealTime)
                self.dieInspector.dieNotes.setText(self.currentSelections[0].notes)
                self.dieInspector.dieDead.setChecked(2 if self.currentSelections[0].dead else 0)
                self.dieInspector.dieName.setText(
                    "Row %d, Col %d" % (self.currentSelections[0].row + 1, self.currentSelections[0].col + 1))
            elif isinstance(self.currentSelections[0], Wafer):
                self.inspectorStack.setCurrentIndex(0)
                self.waferInspector.waferName.setText(self.currentSelections[0].name)
                self.waferInspector.waferSubstrate.setText(self.currentSelections[0].substrate)
                self.waferInspector.waferNotes.setText(self.currentSelections[0].notes)
            elif isinstance(self.currentSelections[0], Sample):
                self.inspectorStack.setCurrentIndex(2)
                self.sampleInspector.sampleResTrans.setValue(self.currentSelections[0].resTrans)
                self.sampleInspector.sampleResLong.setValue(self.currentSelections[0].resLong)
                self.sampleInspector.sampleState.setCurrentIndex(self.currentSelections[0].state)
                self.sampleInspector.sampleName.setText("Die Row %d, Col %d : Sample Row %d, Col %d" % (
                    self.currentSelections[0].parentRow + 1, self.currentSelections[0].parentCol + 1, self.currentSelections[0].row + 1,
                    self.currentSelections[0].col + 1))
                self.sampleInspector.sampleNotes.setText(self.currentSelections[0].notes)
                self.sampleInspector.sampleDimensions.setText(self.currentSelections[0].dimensions)
            else:
                raise Exception("Invalid Inspector")

        self.waferDisplay.repaint()

    #------------------------------------------------------------------
    # Methods for setting the object data from the inspectors
    #------------------------------------------------------------------

    # Wafer
    def changeWaferName(self, string):
        self.currentSelections[0].name = string
        self.ui.setWindowTitle(string)

    def changeWaferSubstrate(self, string):
        self.currentSelections[0].substrate = string

    def changeWaferNotes(self):
        self.currentSelections[0].notes = self.waferInspector.waferNotes.toPlainText()

    # Die
    def changeDieTemp(self, value):
        for sel in self.currentSelections:
            sel.annealTemp = value

    def changeDieTime(self, value):
        for sel in self.currentSelections:
            sel.annealTime = value

    def changeDieNotes(self):
        for sel in self.currentSelections:
            sel.notes = self.dieInspector.dieNotes.toPlainText()

    def changeDieDead(self, value):
        for sel in self.currentSelections:
            sel.dead = True if value == 2 else False

    # Sample
    def changeSampleResLong(self, value):
        for sel in self.currentSelections:
            sel.resLong = value

    def changeSampleResTrans(self, value):
        for sel in self.currentSelections:
            sel.resTrans = value

    def changeSampleNotes(self):
        for sel in self.currentSelections:
            sel.notes = self.sampleInspector.sampleNotes.toPlainText()

    def changeSampleDimensions(self, string):
        for sel in self.currentSelections:
            sel.dimensions = string

    def changeSampleState(self, value):
        for sel in self.currentSelections:
            sel.state = value

    def setShowSamples(self, value):
        self.showSamples = value

    def setShowAnnealing(self, value):
        self.showAnnealing = value

    def showingSamples(self):
        return self.showSamples

    def showingAnnealing(self):
        return self.showAnnealing

    #------------------------------------------------------------------
    # File operations
    #------------------------------------------------------------------

    def save(self):
        if self.filename == "":
            filename = QtGui.QFileDialog.getSaveFileName(self, "Save File", "~/", self.file_types)
            if filename != "":
                self.filename = filename

        tree = self.waferDisplay.waf.generateXML()
        tree.write(self.filename, encoding="utf-8", xml_declaration=True)

    def saveAs(self):
        filename = QtGui.QFileDialog.getSaveFileName(self, "Save File As", "~/", self.file_types)
        if filename != "":
            self.filename = filename
            tree = self.waferDisplay.waf.generateXML()
            tree.write(self.filename, encoding="utf-8", xml_declaration=True)

    def open(self):
        filename = QtGui.QFileDialog.getOpenFileName(self, "Open File", "~/", self.file_types)
        if filename != "":
            self.filename = filename
            self.parseXML()
            self.ui.setWindowTitle(self.waferDisplay.waf.name)
            self.setSelection(self.waferDisplay.waf)

    def new(self):
        name  = self.new_wafer_window.ui.waferName.text()
        drows = self.new_wafer_window.ui.dieRows.value()
        dcols = self.new_wafer_window.ui.dieCols.value()
        srows = self.new_wafer_window.ui.deviceRows.value()
        scols = self.new_wafer_window.ui.deviceCols.value()
        self.filename = ""
        self.waferDisplay.waf = Wafer(drows, dcols, srows, scols, name=name, controller=self.waferDisplay.controller)
        self.setCurrentSelection(self.waferDisplay.waf)
        self.waferDisplay.repaint()

    def parseXML(self):
        tree = ElementTree.parse(self.filename)
        root = tree.getroot()
        drows = int(root.get("dieRows"))
        dcols = int(root.get("dieCols"))
        srows = int(root.get("sampleRows"))
        scols = int(root.get("sampleCols"))

        self.waferDisplay.waf = Wafer(drows, dcols, srows, scols, controller=self.waferDisplay.controller)
        # self.waferDisplay.waf.status   = int(root.get("status"))
        # self.waferDisplay.waf.dieSpacingX    = float(root.get("dieSpacingX")   )
        # self.waferDisplay.waf.dieSpacingY    = float(root.get("dieSpacingY")   )
        # self.waferDisplay.waf.sampleSpacingX = float(root.get("sampleSpacingX"))
        # self.waferDisplay.waf.sampleSpacingY = float(root.get("sampleSpacingY"))

        notes = root.text
        if notes == None:
            notes = ""
        self.waferDisplay.waf.notes = notes
        self.waferDisplay.waf.name = root.get("name")
        self.waferDisplay.waf.substrate = root.get("substrate")

        for i, dierow in enumerate(root.findall('dierow')):
            for j, die in enumerate(dierow.findall('die')):
                for item in die.items():
                    name, val = item
                    if val is not None:
                        val = self.waferDisplay.waf.dies[i][j].dataTypes[name](val)
                        setattr(self.waferDisplay.waf.dies[i][j], name, val)
                    notes = die.text
                    if notes == None:
                        notes = ""
                    self.waferDisplay.waf.dies[i][j].notes = notes

                for ii, deviceRow in enumerate(die.findall('deviceRow')):
                    for jj, device in enumerate(deviceRow.findall('device')):
                        for item in device.items():
                            name, val = item
                            if val is not None:
                                val = self.waferDisplay.waf.dies[i][j].samples[ii][jj].dataTypes[name](val)
                                setattr(self.waferDisplay.waf.dies[i][j].samples[ii][jj], name, val)
                            notes = device.text
                            if notes is None:
                                notes = ""
                            self.waferDisplay.waf.dies[i][j].samples[ii][jj].notes = notes

        self.waferDisplay.repaint()


class DrawWafer(QtGui.QWidget):
    def __init__(self, controller, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.controller = controller
        self.setGeometry(300, 300, 350, 350)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHeightForWidth(True)
        sizePolicy.setWidthForHeight(True)
        self.setSizePolicy(sizePolicy)
        self.waf = Wafer(5, 5, 5, 8, controller=self.controller, parent=self)

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

        # Dimensions
        w = self.size().width()
        h = self.size().height()
        self.centerX = 0.5 * w
        self.centerY = 0.5 * h
        margin = 10.0 * w / 1000.0
        diameter = min(w, h) - 20.0
        radius = diameter / 2.0

        # Move to centered coordinates with usual (x,y) conventions
        paint.save()
        paint.translate(self.centerX, self.centerY)
        paint.scale(1, -1)

        self.waf.draw(paint, diameter, self.centerX, self.centerY)

        paint.restore()
        paint.end()

    def mousePressEvent(self, event):
        super(DrawWafer, self).mousePressEvent(event)
        if not self.waf.checkMousePressEvent(event, self.centerX, self.centerY):
            self.controller.setSelection(self.waf)

    def wheelEvent(self, event):
        zoom = 1.0 + event.delta()/2400.0
        if (self.size().width()*zoom > 300) and (self.size().height()*zoom > 300):
            self.setFixedSize(self.size().width()*zoom, self.size().height()*zoom)
            self.repaint()

class Wafer(QtGui.QWidget):
    def __init__(self, dieRows, dieCols, sampleRows, sampleCols, name="New Wafer", controller=None, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.controller = controller
        self.name = name
        self.substrate = ""
        self.notes = ""
        self.sampleRows = sampleRows
        self.sampleCols = sampleCols
        self.dieRows = dieRows
        self.dieCols = dieCols
        self.dies = [
            [Die(i, j, sampleRows, sampleCols, controller=self.controller, parent=self) for j in range(dieCols)] for i
            in range(dieRows)]

    def draw(self, paint, diameter, centerX, centerY):

        # Draw the actual wafer
        radius = diameter * 0.5
        boundingRect = QtCore.QRectF(-radius, -radius, diameter, diameter)
        grad = QtGui.QLinearGradient(-radius, -radius, radius, radius)
        grad.setColorAt(.75, QtGui.QColor(253, 210, 255))
        grad.setColorAt(.5, QtGui.QColor(217, 226, 255))
        grad.setColorAt(.25, QtGui.QColor(191, 255, 255))
        paint.setBrush(grad)

        if self in self.controller.currentSelections:
            thickness = 1.5
        else:
            thickness = 0.5

        pen = QtGui.QPen(QtCore.Qt.black, thickness, QtCore.Qt.SolidLine)
        paint.setPen(pen)
        paint.drawChord(boundingRect, 290 * 16, 320 * 16)

        # Draw the dies
        self.boxSize = 1.3 * radius
        self.dieMargin = 4 * self.boxSize / 800.0
        self.sizeX = (self.boxSize - (self.dieCols - 1) * self.dieMargin) / self.dieCols
        self.sizeY = (self.boxSize - (self.dieRows - 1) * self.dieMargin) / self.dieRows
        for i, row in enumerate(self.dies):
            for j, die in enumerate(row):
                transX = (j - 0.5 * (self.dieCols - 1)) * (self.sizeX + self.dieMargin)
                transY = (i - 0.5 * (self.dieRows - 1)) * (self.sizeY + self.dieMargin)
                paint.save()
                paint.translate(transX, -transY)
                if die.dead:
                    paint.setBrush(QtGui.QColor(100, 100, 100))
                else:
                    paint.setBrush(QtCore.Qt.NoBrush)
                die.draw(paint, self.sizeX, self.sizeY)
                paint.restore()

    def checkMousePressEvent(self, event, centerX, centerY):
        for i, row in enumerate(self.dies):
            for j, die in enumerate(row):
                eventX = event.x() - centerX
                eventY = event.y() - centerY
                transX = (j - 0.5 * (self.dieCols - 1)) * (self.sizeX + self.dieMargin)
                transY = (i - 0.5 * (self.dieRows - 1)) * (self.sizeY + self.dieMargin)
                if (-0.5 * self.sizeX <= eventX - transX <= 0.5 * self.sizeX):
                    if (-0.5 * self.sizeY <= eventY - transY <= 0.5 * self.sizeY):
                        # Check to see if we hit a die too
                        if not self.dies[i][j].checkMousePressEvent(event, eventX - transX, eventY - transY):
                            doAppend = (event.modifiers() == QtCore.Qt.ShiftModifier)
                            self.controller.setSelection(self.dies[i][j], append=doAppend)
                        # Return true if we hit anything
                        return True
        return False

    def generateXML(self):
        root = ElementTree.Element("wafer")
        root.set("name", str(self.name))
        root.text = str(self.notes)
        root.set("dieRows", str(self.dieRows))
        root.set("dieCols", str(self.dieCols))
        root.set("sampleRows", str(self.sampleRows))
        root.set("sampleCols", str(self.sampleCols))
        root.set("substrate", str(self.substrate))

        for i in range(self.dieRows):
            dierow = ElementTree.SubElement(root, "dierow")
            for j in range(self.dieCols):
                dieObj = self.dies[i][j]
                die = ElementTree.SubElement(dierow, "die")
                die.text = str(dieObj.notes)
                die.set("sampleRows", str(dieObj.sampleRows))
                die.set("sampleCols", str(dieObj.sampleCols))
                die.set("annealTemp", str(dieObj.annealTemp))
                die.set("annealTime", str(dieObj.annealTime))
                die.set("dead", str(dieObj.dead))

                for ii in range(self.sampleRows):
                    deviceRow = ElementTree.SubElement(die, "deviceRow")
                    for jj in range(self.sampleCols):
                        devObj = self.dies[i][j].samples[ii][jj]
                        device = ElementTree.SubElement(deviceRow, "device")
                        device.text = str(devObj.notes)
                        device.set("state", str(devObj.state))
                        device.set("dimensions", str(devObj.dimensions))
                        device.set("resTrans", str(devObj.resTrans))
                        device.set("resLong", str(devObj.resLong))

        tree = ElementTree.ElementTree(root)
        return tree


class Die(QtGui.QWidget):
    def __init__(self, thisRow, thisCol, sampleRows, sampleCols, controller=None, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.contextMenu = QtGui.QMenu()

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu.show)
        self.controller = controller
        self.sampleRows = sampleRows
        self.sampleCols = sampleCols
        self.row = thisRow
        self.col = thisCol
        self.samples = [
            [Sample(i, j, thisRow, thisCol, controller=self.controller, parent=self) for j in range(sampleCols)] for i
            in range(sampleRows)]

        # Actual Values
        self.notes = ""
        self.annealTemp = 0.0
        self.annealTime = 0.0
        self.dead = False
        self.dataTypes = {'notes': str, 'annealTemp': float, 'annealTime': float, 'dead': str2bool,
                          'sampleRows': int, 'sampleCols': int, }

    def name(self):
        return "Die(%d,%d)" % (self.row, self.col)

    def draw(self, paint, sizeX, sizeY):
        # Draw the die
        self.sizeX = sizeX
        self.sizeY = sizeY
        if self in self.controller.currentSelections:
            thickness = 1.5
        else:
            thickness = 0.5

        if self.notes != "":
            pen = QtGui.QPen(QtCore.Qt.blue, thickness, QtCore.Qt.SolidLine)
        else:
            pen = QtGui.QPen(QtCore.Qt.black, thickness, QtCore.Qt.SolidLine)

        paint.setPen(pen)
        if self.annealTemp > 150 and self.controller.showingAnnealing():
            brush = QtGui.QColor()
            temp = self.annealTemp
            if temp > 600.0:
                temp = 600.0
            brush.setHsvF(0.75 + 0.25 * temp / 600.0, 1.0, 1.0)
            paint.setBrush(brush)

        paint.drawRect(-0.5 * self.sizeX, -0.5 * self.sizeY, self.sizeX, self.sizeY)

        # Draw the devices
        self.sampleMargin = 2 * self.sizeX / 100.0
        self.sizeX = (
                         (self.sizeX - 4 * self.sampleMargin) - (
                             self.sampleCols - 1) * self.sampleMargin) / self.sampleCols
        self.sizeY = (
                         (self.sizeY - 4 * self.sampleMargin) - (
                             self.sampleRows - 1) * self.sampleMargin) / self.sampleRows
        for i, row in enumerate(self.samples):
            for j, dev in enumerate(row):
                transX = (j - 0.5 * (self.sampleCols - 1)) * (self.sizeX + self.sampleMargin)
                transY = (i - 0.5 * (self.sampleRows - 1)) * (self.sizeY + self.sampleMargin)
                paint.save()
                paint.translate(transX, -transY)
                dev.draw(paint, self.sizeX, self.sizeY)
                paint.restore()

    def checkMousePressEvent(self, event, eventX, eventY):
        if self.controller.showingSamples():
            for i, row in enumerate(self.samples):
                for j, die in enumerate(row):
                    transX = (j - 0.5 * (self.sampleCols - 1)) * (self.sizeX + self.sampleMargin)
                    transY = (i - 0.5 * (self.sampleRows - 1)) * (self.sizeY + self.sampleMargin)
                    if (-0.5 * self.sizeX <= eventX - transX <= 0.5 * self.sizeX):
                        if (-0.5 * self.sizeY <= eventY - transY <= 0.5 * self.sizeY):
                            doAppend = (event.modifiers() == QtCore.Qt.ShiftModifier)
                            self.controller.setSelection(self.samples[i][j], append=doAppend)
                            return True
        return False


class Sample(QtGui.QWidget):
    def __init__(self, thisRow, thisCol, parentRow, parentCol, controller=None, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.controller = controller
        self.row = thisRow
        self.col = thisCol
        self.parentRow = parentRow
        self.parentCol = parentCol

        self.notes = ""
        self.dimensions = ""
        self.resTrans = 0.0
        self.resLong = 0.0
        self.state = 0
        self.dataTypes = {'notes': str, 'dimensions': str,
                          'resTrans': float, 'resLong': float, 'state': int, }

        self.sizeX = 0
        self.sizeY = 0

    def name(self):
        return "Die(%d,%d) Sample(%d,%d)" % (self.parentRow, self.parentCol, self.row, self.col)

    def draw(self, paint, sizeX, sizeY):
        self.sizeX = sizeX
        self.sizeY = sizeY

        if self.controller.showingSamples():
            if self.state == 1:
                brush = QtGui.QColor(100, 100, 100)
            elif self.state == 2:
                brush = QtGui.QColor(0, 100, 255)
            elif self.state == 3:
                brush = QtGui.QColor(0, 255, 100)
            elif self.state == 4:
                brush = QtGui.QColor(255, 50, 50)
            else:
                brush = QtCore.Qt.NoBrush
            paint.setBrush(brush)
            if self in self.controller.currentSelections:
                thickness = 1.5
            else:
                thickness = 0.5
            pen = QtGui.QPen(QtCore.Qt.black, thickness, QtCore.Qt.SolidLine)
            paint.setPen(pen)
            paint.drawRect(-0.5 * self.sizeX, -0.5 * self.sizeY, self.sizeX, self.sizeY)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    win = MainApp()
    sys.exit(app.exec_())