from daq import *
from report import *
from signal_analysis import *
import json
import os
import sys
import random
import matplotlib
import profig

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.animation as animation

grey1 = QColor("#F8F9FA")
grey2 = QColor("#E9ECEF")
grey3 = QColor("#DEE2E6")
grey4 = QColor("#CED4DA")
grey5 = QColor("#ADB5BD")


# create DAQ to be used in application
reader = Reader()

# create Signal Generator for testing
generator = Generator()

# create signal analysis object
analyzer = Analyzer()


# holds signal
class Communicate(QObject):
    testDone = Signal()
    testListChanged = Signal()
    testSuiteChanged = Signal()


# horizontal divider
class QHLine(QFrame):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(1)
        self.setFixedHeight(20)
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        return


# overrides QListWidgetItem
class ListWidgetItem(QListWidgetItem):
    def __init__(self, parent):
        super().__init__(parent)
        self.setSizeHint(QSize(300, 50))
        return


# overrides QListWidgetItem
class ListWidgetItemB(QListWidgetItem):
    def __init__(self, parent):
        super().__init__(parent)
        self.setSizeHint(QSize(75, 75))
        # self.setBackground(grey3)
        return


# creates matplotlib graph
class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)


class TestRunner(QWidget):
    # Graph controls, graph, and device controls on the left (mainGrid). QTabWidget holding tabs for TestSuite and TestConfig on the right (rightPane).
    def __init__(self, parent):
        super(TestRunner, self).__init__(parent)

        self.testList = self.parent().testList
        self.testSuite = self.parent().testSuite
        self.configuredTests = self.parent().configuredTests
        self.results = self.parent().results
        self.testData = self.parent().testData
        self.comm = self.parent().comm
        self.inputDevices = reader.ai_channels
        self.outputDevices = generator.ao_channels

        self.canvas = MplCanvas(
            self, width=5, height=4, dpi=100
        )  # Matplotlib canvas where live graph is shown
        self.n_data = 50  # number of data points required to start graphing
        self.currTest = 0  # iterator to indicate which test is running
        self.testsFinished = True  # State to see if tests are still running

        toolbar = NavigationToolbar(self.canvas, self)

        self.update_plot()
        self.show()
        self.timer = QTimer()  # live graph timer so that it'll update as data comes in
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_plot)

        self.testTimer = QTimer()

        # Statuses and buttons
        self.status = "pause"
        self.live_status = "pause"
        self.run_test = QPushButton("Start Test Suite")
        self.run_test.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaPlay))
        self.stop_test = QPushButton("Cancel Test Suite")
        self.stop_test.setIcon(QApplication.style().standardIcon(QStyle.SP_MediaStop))
        self.pause_graph = QPushButton("Pause Live Graph")
        self.pause_graph.setIcon(
            QApplication.style().standardIcon(QStyle.SP_MediaPause)
        )
        self.run_test.pressed.connect(self.runTest)
        self.stop_test.pressed.connect(self.stopTest)
        self.pause_graph.pressed.connect(self.pause_live_graph)
        runbar = QHBoxLayout()
        runbar.addWidget(self.run_test)
        runbar.addWidget(self.stop_test)
        runbar.addWidget(self.pause_graph)

        # Sets up device selection widget at the bottom of screen
        deviceTabs = QTabWidget()
        deviceTabs.setTabPosition(QTabWidget.TabPosition.West)
        deviceTabs.setMovable(False)
        deviceTabs.addTab(DeviceSelect(self, "input"), "Input")
        deviceTabs.addTab(DeviceSelect(self, "output"), "Output")

        outerLayout = QHBoxLayout()
        mainGrid = QVBoxLayout()  # grey4
        topbar = QHBoxLayout()
        topbar.addWidget(toolbar)
        topbar.addLayout(runbar)
        mainGrid.addLayout(topbar)
        mainGrid.addWidget(self.canvas, 4)
        mainGrid.addWidget(deviceTabs, 1)

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.setMovable(True)
        tabs.addTab(TestSuite(self), "Test Suite")
        tabs.addTab(TestConfig(self), "Configuration")
        rightPane = QVBoxLayout()  # grey3
        rightPane.addWidget(tabs)
        outerLayout.addLayout(mainGrid, 3.5)
        outerLayout.addLayout(rightPane, 1)
        self.setLayout(outerLayout)

    # Does the computation to graph incoming signal
    def update_plot(self):
        self.fulldatasize = reader.getCurrDataSize()
        self.xdata = np.linspace(
            (self.fulldatasize / reader.sample_rate)
            - (self.n_data / reader.sample_rate),
            self.fulldatasize / reader.sample_rate,
            self.n_data,
        )
        self.ydata = reader.getEndArray(self.n_data)
        if self.xdata.size != len(
            self.ydata
        ):  # when there isn't enough data to start graphing yet
            self.xdata = np.zeros(0)
            self.ydata = []
        self.canvas.axes.cla()
        self.canvas.axes.plot(self.xdata, self.ydata, "r")
        self.canvas.draw()

    # is called when play button is clicked
    # runs all of the test in the test suite
    def runTest(self):
        # base case: when tests are finished we pause the live graph
        if self.status == "run" and self.testsFinished:
            self.status = "pause"
            self.timer.stop()
            self.live_status = "pause"
            self.pause_graph.setIcon(
                QApplication.style().standardIcon(QStyle.SP_MediaPause)
            )
            self.pause_graph.setText("Pause Live Graph")
        # if we are fresh starting the testing suite
        elif self.status == "pause" and self.testsFinished:
            if len(self.testSuite) == 0:
                print("No tests to run, restting suite")
                return
            self.results.clear()
            self.testData.clear()
            self.testsFinished = False
            self.timer.start()  # start live graphing
            self.live_status = "run"
            self.status = "run"
            reader.clearArray()  # clear read data in reader
            test = self.testSuite[
                self.currTest
            ]  # gets name of test we want to do from testSuite
            testIndex = self.testList.index(
                test
            )  # gets index of test config from testList
            testDict = self.configuredTests[
                testIndex
            ]  # gets dictionary of the configed test
            test_duration = testDict[
                "test_duration"
            ]  # get specifcally the test duration from test config
            self.testTimer.setInterval(
                test_duration * 1000 + 1000
            )  # timer for test_duration seconds (this is so we can iterate to next test when we finish a test in testsuite)
            sampleRate = testDict["sample_rate"]  # get the sample rate from config
            reader.start_reader_thread(
                sampleRate, test_duration
            )  # set reader thread with test sample rate
            generator.start_generator_thread()  # start signal generation thread
            self.testTimer.timeout.connect(
                self.recordData
            )  # call test record data when we finish the above timer
            self.testTimer.start()  # start the testTimer
        # if we are still running the tests in the test suite
        elif self.status == "run" and not self.testsFinished:
            self.timer.start()  # start live graphing
            self.live_status = "run"

            reader.clearArray()  # clear read data in reader

            test = self.testSuite[
                self.currTest
            ]  # gets name of test we want to do from testSuite
            testIndex = self.testList.index(
                test
            )  # gets index of test config from testList
            testDict = self.configuredTests[
                testIndex
            ]  # gets dictionary of the configed test
            test_duration = testDict[
                "test_duration"
            ]  # get specifcally the test duration from test config
            self.testTimer.setInterval(
                test_duration * 1000 + 1000
            )  # timer for test_duration seconds (this is so we can iterate to next test when we finish a test in testsuite) has a 1 second buffer to make sure nidaqmx task closes before text ones starts
            sampleRate = testDict["sample_rate"]  # get the sample rate from config
            reader.start_reader_thread(
                sampleRate, test_duration
            )  # set reader thread with test sample rate

            self.testTimer.timeout.connect(
                self.recordData
            )  # call test record data when we finish the above timer
            self.testTimer.start()  # start the testTimer

    # Handles pausing the live graph
    # Is tied to the pause button
    def pause_live_graph(self):
        # if we are the middle of testing and we want to pause
        if self.live_status == "run" and not self.testsFinished:
            self.timer.stop()  # stop live graphing
            self.live_status = "pause"
            # self.status = "pause"
            self.pause_graph.setIcon(
                QApplication.style().standardIcon(QStyle.SP_MediaPlay)
            )
            self.pause_graph.setText("Resume Live Graph")
        else:
            self.timer.start()
            self.live_status = "run"
            self.pause_graph.setIcon(
                QApplication.style().standardIcon(QStyle.SP_MediaPause)
            )
            self.pause_graph.setText("Pause Live Graph")

    # Function: Data collection for a test
    # Grabs data from the reader and brings it into app
    # Starts next test in test suite
    def recordData(self):
        self.testTimer.stop()
        self.testTimer.timeout.disconnect(
            self.recordData
        )  # this is done to ensure we don't duplicate the timer (if not done we recursively start timers)
        self.testData.append(
            reader.getArray().copy()
        )  # get the data recorded in reader and put it in testData
        reader.clearArray()  # reset the reader read data
        self.currTest += 1  # iterate test index
        if self.currTest == len(self.testSuite):  # if we've completed all tests
            self.testsFinished = True
            self.currTest = 0
            self.comm.testDone.emit()  # emit testsfinished signal
            # kill reader/generator thread here
            reader.kill_reader_thread()
            generator.kill_generator_thread()
        else:
            reader.kill_reader_thread()  # kill reader thread so we can start with next test's sample rate

        self.runTest()  # call runTest to either start next test or finished test behavior

    # Function: Stops the test suite and resets all values
    def stopTest(self):
        try:
            self.testTimer.stop()  # stop the test timers
            self.testTimer.timeout.disconnect(
                self.recordData
            )  # disconnect the test timer
            self.testData.clear()  # reset all test data
            self.testsFinished = True  # reset testing state
            self.timer.stop()  # stop live graphing
            self.status = "pause"  # reset testing status
            self.currTest = 0  # reset test iterator index
            reader.clearArray()  # clear data in the reader
            self.update_plot()  # reset graph screen to be blank
            reader.kill_reader_thread()
            generator.kill_generator_thread()

        except:
            print("nothing to stop")


# Class for device and channel selection box on test runner tab
class DeviceSelect(QWidget):
    # io determines the type, which is either "input" or "output"
    def __init__(self, parent, io):
        super(DeviceSelect, self).__init__(parent)
        if io == "input":
            self.devices = self.parent().inputDevices
        else:
            self.devices = self.parent().outputDevices
        self.io = io
        self.deviceCombo = QComboBox()
        self.deviceCombo.addItems(self.devices.keys())
        self.deviceCombo.setMinimumWidth(150)
        self.deviceCombo.currentIndexChanged.connect(self.deviceComboIndexChanged)
        self.signalCombo = QComboBox()
        self.signalCombo.addItems(generator.get_signals())
        self.signalCombo.setMinimumWidth(150)
        self.signalCombo.currentIndexChanged.connect(self.signalComboIndexChanged)
        self.listWidget = QListWidget()
        self.listWidget.setFlow(QListView.LeftToRight)
        # self.listWidget.setSpacing(1)
        self.listWidget.setStyleSheet(
            "QListWidget::item { border: 1px solid #DEE2E6; background-color: #F8F9FA; } QListWidget::item:selected { background: #0e81dc; }"
        )
        if self.deviceCombo.currentIndex() != -1:
            for i in self.devices[self.deviceCombo.currentText()]:
                item = ListWidgetItemB(i)
                self.listWidget.addItem(item)
        self.listWidget.itemSelectionChanged.connect(self.changeChannel)

        outerLayout = QVBoxLayout()
        top = QHBoxLayout()
        top.addWidget(self.deviceCombo)
        if io != "input":
            top.addWidget(QLabel("Signal:"))
            top.addWidget(self.signalCombo)
        top.addStretch()
        outerLayout.addLayout(top)
        outerLayout.addWidget(self.listWidget)
        self.setLayout(outerLayout)

    # connected to self.deviceCombo.currentIndexChanged
    def deviceComboIndexChanged(self):
        self.listWidget.clear()
        for i in self.devices[self.deviceCombo.currentText()]:
            item = ListWidgetItemB(i)
            self.listWidget.addItem(item)

    # choose between simulated signals
    def signalComboIndexChanged(self):
        generator.set_signal(self.signalCombo.currentText())

    # Changes the channel that the daq either reads or generates on
    def changeChannel(self):
        if self.io == "input":
            reader.set_ai_channel(self.listWidget.selectedItems()[0].text())
        else:
            generator.set_ao_channel(self.listWidget.selectedItems()[0].text())


class TestSuite(QWidget):
    # drag-and-drop list that determines the run order of the tests
    def __init__(self, parent):
        super(TestSuite, self).__init__(parent)
        self.testList = self.parent().parent().testList
        self.testSuite = self.parent().parent().testSuite
        self.configuredTests = self.parent().parent().configuredTests
        self.comm = self.parent().parent().comm
        self.comm.testListChanged.connect(self.comboChange)

        self.list_widget = QListWidget(self)
        for t in self.testSuite:
            item = ListWidgetItem(t)
            self.list_widget.addItem(item)
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.model().rowsMoved.connect(self.listChange)
        # self.list_widget.model().rowsRemoved.connect(self.listChange)
        self.delete_test = QPushButton("Delete")
        self.add_test = QPushButton("Add")
        self.delete_test.pressed.connect(self.deleteTest)
        self.add_test.pressed.connect(self.addTest)
        self.pageCombo = QComboBox()
        self.pageCombo.addItems(self.testList)

        rightPane = QVBoxLayout()  # grey3
        rightPane.addWidget(self.list_widget)
        rightPane.addWidget(self.delete_test)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_test)
        button_layout.addWidget(self.pageCombo)
        rightPane.addLayout(button_layout)
        self.setLayout(rightPane)

    # connected to self.comm.testListChanged
    def comboChange(self):
        self.pageCombo.clear()
        self.pageCombo.addItems(self.testList)

    # connected to self.list_widget.model().rowsMoved
    def listChange(self):
        self.testSuite = []
        for i in range(self.list_widget.count()):
            self.testSuite.append(self.list_widget.item(i).text())
        self.comm.testSuiteChanged.emit()

    # connected to self.add_test button
    def addTest(self):
        t = self.pageCombo.currentText()
        self.testSuite.append(t)
        self.list_widget.addItem(ListWidgetItem(t))
        self.comm.testSuiteChanged.emit()

    # connected to self.delete_test button
    def deleteTest(self):
        index = self.list_widget.row(self.list_widget.selectedItems()[0])
        self.list_widget.takeItem(index)
        self.testSuite.pop(index)
        self.comm.testSuiteChanged.emit()


class TestConfig(QWidget):
    # form to input test configuration parameters
    def __init__(self, parent):
        super(TestConfig, self).__init__(parent)
        self.testList = self.parent().parent().testList
        self.testSuite = self.parent().parent().testSuite
        self.configuredTests = self.parent().parent().configuredTests
        self.comm = self.parent().parent().comm

        self.pageCombo = QComboBox()
        self.pageCombo.addItems(self.testList)
        self.pageCombo.setCurrentIndex(-1)
        self.pageCombo.setInsertPolicy(QComboBox.InsertPolicy.InsertAtBottom)
        self.pageCombo.currentIndexChanged.connect(self.comboIndexChanged)
        self.name = QLineEdit()
        generalSettingsLabel = QLabel("General Test Settings")
        self.peakState = False
        self.findPeaks = QCheckBox()
        signalLabel = QLabel("Minumum/Maximum Signal")
        self.minSignal = QLineEdit()
        self.maxSignal = QLineEdit()
        avgSignalLabel = QLabel("Average Signal")
        self.avgSigMinTolerance = QLineEdit()
        self.avgSigMaxTolerance = QLineEdit()
        riseTimePeakLabel = QLabel("Rise Time Peak")
        self.riseStartPercent = QLineEdit()
        self.riseEndPercent = QLineEdit()
        self.riseTimeMinTol = QLineEdit()
        self.riseTimeMaxTol = QLineEdit()
        fallTimePeakLabel = QLabel("Fall Time Peak")
        self.fallStartPercent = QLineEdit()
        self.fallEndPercent = QLineEdit()
        self.fallTimeMinTol = QLineEdit()
        self.fallTimeMaxTol = QLineEdit()
        avgRiseTimeLabel = QLabel("Average Rise Time")
        self.avgRiseStartPercent = QLineEdit()
        self.avgRiseEndPercent = QLineEdit()
        self.avgRiseTimeMinTol = QLineEdit()
        self.avgRiseTimeMaxTol = QLineEdit()
        avgFallTimeLabel = QLabel("Average Fall Time")
        self.avgFallStartPercent = QLineEdit()
        self.avgFallEndPercent = QLineEdit()
        self.avgFallTimeMinTol = QLineEdit()
        self.avgFallTimeMaxTol = QLineEdit()
        self.testDuration = QLabel("Test Duration (s)")
        self.testTime = QLineEdit()
        self.sampleRateLabel = QLabel("Sample Rate (hz)")
        self.sampleRate = QLineEdit()
        self.clear_test = QPushButton("Clear")
        self.save_test = QPushButton("Save")
        self.delete_test = QPushButton("Delete")
        self.clear_test.pressed.connect(self.clearTest)
        self.save_test.pressed.connect(self.saveTest)
        self.delete_test.pressed.connect(self.deleteTest)

        form = QFormLayout()
        form.addRow(self.pageCombo)
        form.addRow("Test Name", self.name)
        form.addRow(QHLine())
        form.addRow(generalSettingsLabel)
        form.addRow("Find Peaks", self.findPeaks)
        form.addRow(signalLabel)
        form.addRow("Minimum Limit", self.minSignal)
        form.addRow("Maximum Limit", self.maxSignal)
        form.addRow(QHLine())
        form.addRow(avgSignalLabel)
        form.addRow("Minimum Tolerance", self.avgSigMinTolerance)
        form.addRow("Maximum Tolerance", self.avgSigMaxTolerance)
        form.addRow(QHLine())
        form.addRow(riseTimePeakLabel)
        form.addRow("Start Percent", self.riseStartPercent)
        form.addRow("End Percent", self.riseEndPercent)
        form.addRow("Minimum Tolerance", self.riseTimeMinTol)
        form.addRow("Maximum Tolerance", self.riseTimeMaxTol)
        form.addRow(QHLine())
        form.addRow(fallTimePeakLabel)
        form.addRow("Start Percent", self.fallStartPercent)
        form.addRow("End Percent", self.fallEndPercent)
        form.addRow("Minimum Tolerance", self.fallTimeMinTol)
        form.addRow("Maximum Tolerance", self.fallTimeMaxTol)
        form.addRow(QHLine())
        form.addRow(avgRiseTimeLabel)
        form.addRow("Start Percent", self.avgRiseStartPercent)
        form.addRow("End Percent", self.avgRiseEndPercent)
        form.addRow("Minimum Tolerance", self.avgRiseTimeMinTol)
        form.addRow("Maximum Tolerance", self.avgRiseTimeMaxTol)
        form.addRow(QHLine())
        form.addRow(avgFallTimeLabel)
        form.addRow("Start Percent", self.avgFallStartPercent)
        form.addRow("End Percent", self.avgFallEndPercent)
        form.addRow("Minimum Tolerance", self.avgFallTimeMinTol)
        form.addRow("Maximum Tolerance", self.avgFallTimeMaxTol)
        form.addRow(QHLine())
        form.addRow(self.testDuration)
        form.addRow("Test Time (s)", self.testTime)
        form.addRow(self.sampleRateLabel)
        form.addRow("Sample Rate (hz)", self.sampleRate)
        form.addRow(self.clear_test)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_test)
        button_layout.addWidget(self.delete_test)
        form.addRow(button_layout)

        # rightPane = QVBoxLayout()  # grey3
        # rightPane.addLayout(form)
        # self.setLayout(rightPane)

        rightPane = QVBoxLayout()
        self.scrollWidget = QWidget()
        self.scrollWidget.setLayout(form)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.scrollWidget)
        self.scroll.setWidgetResizable(True)
        self.scrollWidget.setStyleSheet(
            "QWidget { background-color: %s }" % grey1.name()
        )
        rightPane.addWidget(self.scroll)
        self.setLayout(rightPane)

    # return as a string after checking if input is N/A
    def checkNA(self, lineEdit, i, name):
        text = str(self.configuredTests[i][name])
        # if
        if text != "N/A":
            lineEdit.setText(text)
        else:
            lineEdit.clear()

    # set the QLabels to the parameters of the selected test when the combo selection changes
    def comboIndexChanged(self, i):
        self.name.setText(self.configuredTests[i]["name"])
        if self.configuredTests[i]["find_peaks"]:
            self.findPeaks.setChecked(True)
        self.checkNA(self.minSignal, i, "min_sig")
        self.checkNA(self.maxSignal, i, "max_sig")
        self.checkNA(self.avgSigMinTolerance, i, "avg_sig_min_tol")
        self.checkNA(self.avgSigMaxTolerance, i, "avg_sig_max_tol")
        self.checkNA(self.riseStartPercent, i, "rise_start_percent")
        self.checkNA(self.riseEndPercent, i, "rise_end_percent")
        self.checkNA(self.riseTimeMinTol, i, "rise_time_min_tol")
        self.checkNA(self.riseTimeMaxTol, i, "rise_time_max_tol")
        self.checkNA(self.fallStartPercent, i, "fall_start_percent")
        self.checkNA(self.fallEndPercent, i, "fall_end_percent")
        self.checkNA(self.fallTimeMinTol, i, "fall_time_min_tol")
        self.checkNA(self.fallTimeMaxTol, i, "fall_time_max_tol")
        self.checkNA(self.avgRiseStartPercent, i, "avg_rise_start_percent")
        self.checkNA(self.avgRiseEndPercent, i, "avg_rise_end_percent")
        self.checkNA(self.avgRiseTimeMinTol, i, "avg_rise_min_tol")
        self.checkNA(self.avgRiseTimeMaxTol, i, "avg_rise_max_tol")
        self.checkNA(self.avgFallStartPercent, i, "avg_fall_start_percent")
        self.checkNA(self.avgFallEndPercent, i, "avg_fall_end_percent")
        self.checkNA(self.avgFallTimeMinTol, i, "avg_fall_min_tol")
        self.checkNA(self.avgFallTimeMaxTol, i, "avg_fall_max_tol")
        self.checkNA(self.testTime, i, "test_duration")
        self.checkNA(self.sampleRate, i, "sample_rate")

    # Connected to self.clear_test button; clears text from the QLabels
    def clearTest(self):
        self.findPeaks.setChecked(False)
        self.minSignal.clear()
        self.maxSignal.clear()
        self.avgSigMinTolerance.clear()
        self.avgSigMaxTolerance.clear()
        self.riseStartPercent.clear()
        self.riseEndPercent.clear()
        self.riseTimeMinTol.clear()
        self.riseTimeMaxTol.clear()
        self.fallStartPercent.clear()
        self.fallEndPercent.clear()
        self.fallTimeMinTol.clear()
        self.fallTimeMaxTol.clear()
        self.avgRiseStartPercent.clear()
        self.avgRiseEndPercent.clear()
        self.avgRiseTimeMinTol.clear()
        self.avgRiseTimeMaxTol.clear()
        self.avgFallStartPercent.clear()
        self.avgFallEndPercent.clear()
        self.avgFallTimeMinTol.clear()
        self.avgFallTimeMaxTol.clear()
        self.testTime.clear()
        self.sampleRate.clear()

    # returns an int or "N/A"
    def validateInt(self, text):
        if text == "":
            return "N/A"
        else:
            return int(text)

    # returns a float or "N/A"
    def validateFloat(self, text):
        if text == "":
            return "N/A"
        else:
            return float(text)

    # Connected to self.save_test button; if the Qlabel is empty, the parameter is saved as "N/A"
    def saveTest(self):
        testName = self.name.text()
        test_index = self.testList.index(testName) if testName in self.testList else -1
        newDict = {"name": testName}
        newDict["find_peaks"] = bool(self.findPeaks.checkState())
        newDict["min_sig"] = self.validateFloat(self.minSignal.text())
        newDict["max_sig"] = self.validateFloat(self.maxSignal.text())
        newDict["avg_sig_min_tol"] = self.validateFloat(self.avgSigMinTolerance.text())
        newDict["avg_sig_max_tol"] = self.validateFloat(self.avgSigMaxTolerance.text())
        newDict["rise_start_percent"] = self.validateInt(self.riseStartPercent.text())
        newDict["rise_end_percent"] = self.validateInt(self.riseEndPercent.text())
        newDict["rise_time_min_tol"] = self.validateFloat(self.riseTimeMinTol.text())
        newDict["rise_time_max_tol"] = self.validateFloat(self.riseTimeMaxTol.text())
        newDict["fall_start_percent"] = self.validateInt(self.fallStartPercent.text())
        newDict["fall_end_percent"] = self.validateInt(self.fallEndPercent.text())
        newDict["fall_time_min_tol"] = self.validateFloat(self.fallTimeMinTol.text())
        newDict["fall_time_max_tol"] = self.validateFloat(self.fallTimeMaxTol.text())
        newDict["avg_rise_start_percent"] = self.validateFloat(
            self.avgRiseStartPercent.text()
        )
        newDict["avg_rise_end_percent"] = self.validateFloat(
            self.avgRiseEndPercent.text()
        )
        newDict["avg_rise_min_tol"] = self.validateFloat(self.avgRiseTimeMinTol.text())
        newDict["avg_rise_max_tol"] = self.validateFloat(self.avgRiseTimeMaxTol.text())
        newDict["avg_fall_start_percent"] = self.validateFloat(
            self.avgFallStartPercent.text()
        )
        newDict["avg_fall_end_percent"] = self.validateFloat(
            self.avgFallEndPercent.text()
        )
        newDict["avg_fall_min_tol"] = self.validateFloat(self.avgFallTimeMinTol.text())
        newDict["avg_fall_max_tol"] = self.validateFloat(self.avgFallTimeMaxTol.text())
        newDict["test_duration"] = self.validateFloat(self.testTime.text())
        newDict["sample_rate"] = self.validateFloat(self.sampleRate.text())
        if test_index == -1:
            self.testList.append(testName)
            self.configuredTests.append(newDict)
            self.pageCombo.addItem(testName)
            self.pageCombo.setCurrentIndex(len(self.testList) - 1)
            self.comm.testListChanged.emit()
        else:
            self.configuredTests[test_index].update(newDict)
            self.pageCombo.setCurrentIndex(test_index)

    # Connected to self.delete_test button
    def deleteTest(self):
        combo_index = self.pageCombo.currentIndex()
        if combo_index == -1:
            print("No test selected")
        else:
            self.testList.pop(combo_index)
            self.configuredTests.pop(combo_index)  # TODO: delete in config file as well
            self.pageCombo.removeItem(combo_index)
            self.comm.testListChanged.emit()


# The purpose of this class is to handle the analysis of the signal once the data collection is complete
# Any tests that are in the test suite will be run, and the results panel will be updated accordingly
class Analysis(QWidget):
    # Graph controls and graph on the left (mainGrid). List of tests on the right (rightPane).
    def __init__(self, parent):
        super(Analysis, self).__init__(parent)
        # Graph in the results panel for displaying analysis results
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        toolbar = NavigationToolbar(self.canvas, self)
        self.testSuite = self.parent().testSuite
        self.testData = self.parent().testData
        self.comm = self.parent().comm
        self.configuredTests = self.parent().configuredTests
        # List of dicts to store the results for each test
        # Since each test is made up of multiple steps, each test has a field named "results"
        # which contains a list of dicts where each dict is the results for a specific step.
        # The format of the internal step dict can be found in signal_analysis.py
        self.results = self.parent().results
        # keeps track of which step graph to display
        self.step_index = 0
        self.step_right_button = QPushButton("Next Step")
        self.step_right_button.pressed.connect(self.step_right)
        self.step_left_button = QPushButton("Previous Step")
        self.step_left_button.setEnabled(False)
        self.step_left_button.pressed.connect(self.step_left)
        # list of tests in the test suite
        self.list_widget = QListWidget(self)
        for t in self.testSuite:
            item = ListWidgetItem(t)
            self.list_widget.addItem(item)
        self.comm.testSuiteChanged.connect(self.listChange)
        self.comm.testDone.connect(self.updateResults)
        self.list_widget.itemSelectionChanged.connect(self.list_click_helper)

        self.canvas.axes.plot(self.testData)
        self.show()
        # visual formatting
        resultsPane = QVBoxLayout()
        buttonLayout = QHBoxLayout()
        self.step_left_button.setFixedSize(QSize(250, 75))
        self.step_right_button.setFixedSize(QSize(250, 75))
        buttonLayout.addStretch()
        buttonLayout.addWidget(self.step_left_button)
        buttonLayout.addSpacing(20)
        buttonLayout.addWidget(self.step_right_button)
        buttonLayout.addStretch()
        resultsPane.addLayout(buttonLayout)
        resultsPane.addWidget(self.canvas)

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.setMovable(True)
        tabs.addTab(self.list_widget, "Test List")

        outerLayout = QHBoxLayout()
        mainGrid = QVBoxLayout()  # grey4
        mainGrid.addWidget(toolbar)
        mainGrid.addLayout(resultsPane)
        rightPane = QVBoxLayout()  # grey3
        rightPane.addWidget(tabs)
        outerLayout.addLayout(mainGrid, 3.5)
        outerLayout.addLayout(rightPane, 1)
        self.setLayout(outerLayout)

    # Funtion to increment the current step
    def step_right(self):
        # Grabbing various information in order to get the list of steps
        current_test = self.list_widget.selectedItems()[0].text()
        index = self.testSuite.index(current_test)
        data = self.testData[index]
        params = self.getTestParams(current_test)
        step_list = self.getStepList(data, params)
        # Bounds checking to make sure the step_index doesn't go beyond the
        # testSuite length. Disables right_button when the end is reached and
        # re-enables the left_button if the step_index is incremented past zero
        if self.step_index < len(step_list) - 1:
            self.step_index += 1
        if self.step_index == len(step_list) - 1:
            self.step_right_button.setEnabled(False)
        if self.step_index > 0:
            self.step_left_button.setEnabled(True)

        # Update the results graph with the newly selected step
        self.updateResultsGraph()

    # Function to decrement the current step
    def step_left(self):
        # Grabbing various information in order to get the list of steps
        current_test = self.list_widget.selectedItems()[0].text()
        index = self.testSuite.index(current_test)
        data = self.testData[index]
        params = self.getTestParams(current_test)
        step_list = self.getStepList(data, params)
        # Bounds checking to make sure the step_index doesn't go beyond the
        # testSuite. Disables the left_button when step_index becomes zero and
        # re-enables the right_button if the step_index is decremented below
        # the last step.
        if self.step_index > 0:
            self.step_index -= 1
        if self.step_index == 0:
            self.step_left_button.setEnabled(False)
        if self.step_index < len(step_list) - 1:
            self.step_right_button.setEnabled(True)
        self.updateResultsGraph()

    # Updates the list of tests in the analysis tab whenever the testSuite is changed
    # Should be attached to the testSuiteChanged signal in the comm class
    def listChange(self):
        self.list_widget.clear()
        for t in self.testSuite:
            item = ListWidgetItem(t)
            self.list_widget.addItem(item)

    # Gets the parameters of a specified test in configuredTests
    def getTestParams(self, test_name):
        for test in self.configuredTests:
            # print(test["name"])
            if test["name"] == test_name:
                return test
            # print(test)

    # Returns a list of dicts where each dict is the results of a step in a test
    # The steps in the test are determined by which fields in the test configuration
    # are not set to "N/A"
    def getStepList(self, data, params):
        step_list = []
        if params["min_sig"] != "N/A" and params["max_sig"] != "N/A":
            step_list.append(
                analyzer.min_max_signal(data, params["min_sig"], params["max_sig"])
            )
        if params["avg_sig_min_tol"] != "N/A" and params["avg_sig_max_tol"] != "N/A":
            step_list.append(
                analyzer.avg_signal(
                    data, params["avg_sig_min_tol"], params["avg_sig_max_tol"]
                )
            )
        if (
            params["rise_start_percent"] != "N/A"
            and params["rise_end_percent"] != "N/A"
            and params["rise_time_min_tol"] != "N/A"
            and params["rise_time_max_tol"] != "N/A"
        ):
            step_list.append(
                analyzer.rise_time_all_peaks(
                    data,
                    params["rise_start_percent"],
                    params["rise_end_percent"],
                    params["rise_time_min_tol"],
                    params["rise_time_max_tol"],
                    params["sample_rate"],
                )
            )
        if (
            params["fall_start_percent"] != "N/A"
            and params["fall_end_percent"] != "N/A"
            and params["fall_time_min_tol"] != "N/A"
            and params["fall_time_max_tol"] != "N/A"
        ):
            step_list.append(
                analyzer.fall_time_all_peaks(
                    data,
                    params["fall_start_percent"],
                    params["fall_end_percent"],
                    params["fall_time_min_tol"],
                    params["fall_time_max_tol"],
                    params["sample_rate"],
                )
            )
        if (
            params["avg_rise_min_tol"] != "N/A"
            and params["avg_rise_max_tol"] != "N/A"
            and params["avg_rise_start_percent"] != "N/A"
            and params["avg_rise_end_percent"] != "N/A"
        ):
            step_list.append(
                analyzer.avg_rise_time(
                    data,
                    params["avg_rise_start_percent"],
                    params["avg_rise_end_percent"],
                    params["avg_rise_min_tol"],
                    params["avg_rise_max_tol"],
                    params["sample_rate"],
                )
            )
        if (
            params["avg_fall_min_tol"] != "N/A"
            and params["avg_fall_max_tol"] != "N/A"
            and params["avg_fall_start_percent"] != "N/A"
            and params["avg_fall_end_percent"] != "N/A"
        ):
            step_list.append(
                analyzer.avg_fall_time(
                    data,
                    params["avg_fall_start_percent"],
                    params["avg_fall_end_percent"],
                    params["avg_fall_min_tol"],
                    params["avg_fall_max_tol"],
                    params["sample_rate"],
                )
            )
        if params["find_peaks"]:
            step_list.append(analyzer.find_peaks(data))
        return step_list

    # Updates self.results with the results from the running of the testSuite.
    # self.results consists of a list of dicts where each dict represents a test
    # Each test dict contains the following keys:
    # test_name: the name of the test
    # test_passed: a boolean showing if the test passed or not. A test fails if any step within that test fails
    # results: a list of dicts where each dict is the results of an individual step. Refer to signal_analysis.py
    # for the structure of the step results dict
    def updateResults(self):
        for i in range(len(self.testSuite)):
            test_name = self.testSuite[i]
            # print(test_name)
            index = self.testSuite.index(test_name)
            data = self.testData[index]
            params = self.getTestParams(test_name)
            self.results.append(
                {"test_name": test_name, "test_passed": True, "results": []}
            )
            step_list = self.getStepList(data, params)
            for step in step_list:
                self.results[i]["results"].append(step)
                if step["status"] == False:
                    self.results[i]["test_passed"] = False

    # Updates the graph in the results pane with the data for the test that is currently clicked on
    # Depending on what step is currently selected, different markings are put on the graph to better display the results
    def updateResultsGraph(self):
        current_test = self.list_widget.selectedItems()[0].text()
        # print(current_test)
        index = self.testSuite.index(current_test)
        data = self.testData[index]
        params = self.getTestParams(current_test)
        self.canvas.axes.clear()
        self.canvas.axes.plot(data)
        step_list = self.getStepList(data, params)
        current_step = step_list[self.step_index]
        peak_info = analyzer.find_peaks(data)["measurement"]
        min_peak_len = min(len(peak_info[0]), len(peak_info[1]), len(peak_info[2]))

        # The user defined limits for maximum and minimum are shown with a dashed line
        # If the maximum line is below the maximum limit, it is displayed in green, otherwise red
        # If the minimum line is above the minimum limit, it is displayed in green, otherwise red
        # Both the recorded minimum and maximum are labeled with text
        if current_step["step_name"] == "min_max_signal":
            self.canvas.axes.set_title("Minimum/MaximumSignal")
            min_sig = current_step["measurement"][0]
            max_sig = current_step["measurement"][1]
            min_tol = current_step["low_limit"]
            max_tol = current_step["high_limit"]
            if min_sig < min_tol:
                self.canvas.axes.axhline(y=min_sig, color="r", linestyle="-")
            else:
                self.canvas.axes.axhline(y=min_sig, color="g", linestyle="-")
            self.canvas.axes.text(0, min_sig, "Minimum Signal")
            if max_sig > max_tol:
                self.canvas.axes.axhline(y=max_sig, color="r", linestyle="-")
            else:
                self.canvas.axes.axhline(y=max_sig, color="g", linestyle="-")
            self.canvas.axes.text(0, max_sig, "Maximum Signal")
            self.canvas.axes.axhline(y=min_tol, color="b", linestyle="dashed")
            self.canvas.axes.axhline(y=max_tol, color="b", linestyle="dashed")

        # The user defined maximum and minimum tolerances are displayed with dashed lines
        # If the average signal is within the limits, it is displayed as a green line, otherwise red
        if current_step["step_name"] == "average_signal":
            self.canvas.axes.set_title("Average Signal")
            if current_step["status"]:
                self.canvas.axes.axhline(
                    y=current_step["measurement"], color="g", linestyle="-"
                )
            else:
                self.canvas.axes.axhline(
                    y=current_step["measurement"], color="r", linestyle="-"
                )
            self.canvas.axes.axhline(
                y=params["avg_sig_min_tol"], color="b", linestyle="dashed"
            )
            self.canvas.axes.axhline(
                y=params["avg_sig_max_tol"], color="b", linestyle="dashed"
            )
        # The peaks are labeled with black dots and the beginning prominence is labeled with green dots
        # The rise time for each peak is labeled above the peak with text
        if current_step["step_name"] == "rise_time_peak":
            self.canvas.axes.set_title("Rise Time for Peak")
            for i in range(min_peak_len - 1):
                self.canvas.axes.plot(
                    peak_info[0][i],
                    data[peak_info[0][i]],
                    ".",
                    color="g",
                    markersize=20,
                )
                self.canvas.axes.plot(
                    peak_info[1][i],
                    data[peak_info[1][i]],
                    ".",
                    color="b",
                    markersize=20,
                )
                self.canvas.axes.text(
                    peak_info[1][i],
                    data[peak_info[1][i]],
                    str(current_step["measurement"][i]),
                )
        # The peaks are labeled with black dots and the ending prominence is labeled with red dots
        # The fall time for each peak is labeled above the peak with text
        if current_step["step_name"] == "fall_time_peak":
            self.canvas.axes.set_title("Fall Time for Peak")
            for i in range(min_peak_len - 1):
                self.canvas.axes.plot(
                    peak_info[2][i],
                    data[peak_info[2][i]],
                    ".",
                    color="r",
                    markersize=20,
                )
                self.canvas.axes.plot(
                    peak_info[1][i],
                    data[peak_info[1][i]],
                    ".",
                    color="b",
                    markersize=20,
                )
                self.canvas.axes.text(
                    peak_info[1][i],
                    data[peak_info[1][i]],
                    str(current_step["measurement"][i]),
                )
        # The peaks are labeled with black dots and the beginning prominence is labeled with green dots
        # The average rise time is labeled in the graph title
        if current_step["step_name"] == "avg_rise_time":
            self.canvas.axes.set_title("Average Rise Time")
            for i in range(min_peak_len - 1):
                self.canvas.axes.plot(
                    peak_info[0][i],
                    data[peak_info[0][i]],
                    ".",
                    color="g",
                    markersize=20,
                )
                self.canvas.axes.plot(
                    peak_info[1][i],
                    data[peak_info[1][i]],
                    ".",
                    color="b",
                    markersize=20,
                )
                self.canvas.axes.text(
                    1,
                    1,
                    ("Average Rise Time: " + str(current_step["measurement"])),
                    transform=self.canvas.axes.transAxes,
                )
        # The peaks are labeled with black dots and the ending prominence is labeled with red dots
        # The average rise time is labeled in the graph title
        if current_step["step_name"] == "avg_fall_time":
            self.canvas.axes.set_title("Average Fall Time")
            for i in range(min_peak_len - 1):
                self.canvas.axes.plot(
                    peak_info[1][i],
                    data[peak_info[1][i]],
                    ".",
                    color="b",
                    markersize=20,
                )
                self.canvas.axes.plot(
                    peak_info[2][i],
                    data[peak_info[2][i]],
                    ".",
                    color="r",
                    markersize=20,
                )
                self.canvas.axes.text(
                    1,
                    1,
                    ("Average Fall Time: " + str(current_step["measurement"])),
                    transform=self.canvas.axes.transAxes,
                )
        # Peaks are labeled with an x. The color is randomized
        # (this was initially unintended behavior, but I thought it looked pretty)
        if current_step["step_name"] == "find_peaks":
            self.canvas.axes.set_title("Find Peaks")
            for peak in peak_info[1]:
                self.canvas.axes.plot(peak, data[peak], "x")

        self.canvas.draw()

    # Updates the graph with the test which is currently selected.
    def list_click_helper(self):
        # Reset the step_index since we are on a new test
        self.step_index = 0

        # Disable the left_button since we're at zero and re-enable the right_button
        self.step_right_button.setEnabled(True)
        self.step_left_button.setEnabled(False)

        # Get the currently selected test and various other data which allows us to get the step_list
        current_test = self.list_widget.selectedItems()[0].text()
        index = self.testSuite.index(current_test)
        data = self.testData[index]
        params = self.getTestParams(current_test)
        step_list = self.getStepList(data, params)

        # If the current test only has one step, then diable the right_button as well
        if len(step_list) == 1:
            self.step_right_button.setEnabled(False)
        self.updateResultsGraph()


class MainWindow(QMainWindow):
    singleton: "MainWindow" = None

    # Holds important variables used by child classes
    # Creates the main tabs as well as a file menu
    def __init__(self):
        super().__init__()
        self.init = profig.Config("init.cfg")  # tracks last opened file
        self.cfg = profig.Config("default.cfg")  # tracks all other saved info
        self.testList = []  # list of all test names
        self.testSuite = []  # test names in the Test Suite run order
        self.configuredTests = []  # configurations matching index in self.testList
        self.testData = []
        self.results = []
        self.saved = False
        self.comm = Communicate()
        self.webView = QWebEngineView()

        self.setWindowTitle("Sandia User-Configurable Tester")
        self._config()

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.setMovable(True)
        tabs.addTab(TestRunner(self), "Test Runner")
        tabs.addTab(Analysis(self), "Analysis")
        tabs.addTab(ReportPreview(self), "Report Preview")
        self.setCentralWidget(tabs)
        self._createMenu()
        self.resize(1600, 900)

        # set webView as dummy, hide it, maximize window, and show it to as a workaround for close/reopen bug
        self.webView.setUrl(QUrl(""))
        self.webView.hide()
        self.showMaximized()
        self.webView.show()

    def closeEvent(self, e):
        print("window closed")

    # At the start of the program, load the last used config file using the profig library
    def _config(self):
        self.init = profig.Config("init.cfg")
        self.init.init("lastopenedfile", "default.cfg", str)
        self.init.sync()
        filename = self.init["lastopenedfile"]
        self.cfg = profig.Config(filename)
        if filename != "default.cfg" and filename != "___.cfg":
            self.saved = True
        self.setWindowTitle("Sandia User-Configurable Tester || " + filename)

        # splitList = lambda x: list(x.split(","))
        # listToStr = lambda x: ",".join(x)
        # dictToStr = lambda x: json.dumps(x)
        # splitDict = lambda x: json.loads(x)
        # cfg.coercer.register(list, lambda x: ",".join(x), lambda x: list(x.split(",")))
        self.cfg.coercer.register(
            dict, lambda x: json.dumps(x), lambda x: json.loads(x)
        )  # dict coercer does not work so string conversion/deconversion is needed when using dicts with the config file
        self.cfg.init("test_list", [], list)
        self.cfg.init("test_suite", [], list)
        self.cfg.sync()
        self.testList = self.cfg["test_list"]
        self.testSuite = self.cfg["test_suite"]
        for x in self.testList:
            self.configuredTests.append(json.loads(self.cfg["section_test." + x]))
        self.cfg.sync()

    # Connected to button_new; restart window with "___.cfg" set as the current config file
    def _new(self):
        if os.path.exists("___.cfg"):
            os.remove("___.cfg")
        self.init["lastopenedfile"] = "___.cfg"
        self.init.sync()
        MainWindow.restart()

    # Connected to button_open; choose file, then restart window
    def _open(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setViewMode(QFileDialog.Detail)
        dialog.setNameFilter("Any files (*)")
        dialog.setAcceptMode(QFileDialog.AcceptOpen)

        filenames = ""
        if dialog.exec():
            filenames = dialog.selectedFiles()
        filename = os.path.basename(filenames[0])
        self.init["lastopenedfile"] = filename
        self.init.sync()
        MainWindow.restart()

    # Connected to button_save; save values to config file
    def _save(self):
        if (
            self.saved != True
        ):  # If the config file is "default.cfg" or "___.cfg", treat the first _save as _saveas instead
            self._saveas()
        else:
            self.cfg["test_list"] = self.testList
            self.cfg["test_suite"] = self.testSuite
            for dic in self.configuredTests:
                self.cfg["section_test." + dic["name"]] = json.dumps(dic)
            self.cfg.sync()

    # Connected to button_save_as; choose file, then save values to config file
    def _saveas(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setViewMode(QFileDialog.Detail)
        dialog.setNameFilter("Any files (*)")
        dialog.setAcceptMode(QFileDialog.AcceptSave)

        filenames = ""
        if dialog.exec():
            filenames = dialog.selectedFiles()
        filename = os.path.basename(filenames[0])
        self.init["lastopenedfile"] = filename
        self.setWindowTitle("Sandia User-Configurable Tester || " + filename)

        newcfg = profig.Config(filename)
        self.cfg = newcfg
        self.cfg["test_list"] = self.testList
        self.cfg["test_suite"] = self.testSuite
        for dic in self.configuredTests:
            self.cfg["section_test." + dic["name"]] = json.dumps(dic)
        self.cfg.sync()

        self.init.sync()
        self.saved = True

    # Creates the file menus, "File" and "Help"
    def _createMenu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")

        button_new = QAction("&New Project", self)
        button_new.triggered.connect(self._new)
        button_new.setShortcut(QKeySequence("Ctrl+N"))
        file_menu.addAction(button_new)
        button_open = QAction("&Open Project...", self)
        button_open.triggered.connect(self._open)
        button_open.setShortcut(QKeySequence("Ctrl+O"))
        file_menu.addAction(button_open)

        file_menu.addSeparator()

        button_save = QAction("&Save", self)
        button_save.triggered.connect(self._save)
        button_save.setShortcut(QKeySequence("Ctrl+S"))
        file_menu.addAction(button_save)
        button_save_as = QAction("&Save as...", self)
        button_save_as.triggered.connect(self._saveas)
        button_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        file_menu.addAction(button_save_as)

        file_menu.addSeparator()

        button_close = QAction("&Close Window", self)
        button_close.triggered.connect(self.close)
        button_close.setShortcut(QKeySequence("Alt+F4"))
        file_menu.addAction(button_close)

        button_restart = QAction("&Restart Window", self)
        button_restart.triggered.connect(MainWindow.restart)
        file_menu.addAction(button_restart)

        help_menu = menu.addMenu("&Help")

        button_graph = QAction("&Graph Controls", self)
        button_graph.triggered.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://matplotlib.org/3.1.1/users/navigation_toolbar.html")
            )
        )
        help_menu.addAction(button_graph)

        button_test = QAction("&Test", self)
        button_test.triggered.connect(self._testValue)
        help_menu.addAction(button_test)

    def _testValue(self):
        # self.testSuite.append("testvalue")
        self.comm.testDone.emit()
        # print(self.testSuite)

    # Restarts program by setting MainWindow
    @staticmethod
    def restart():
        # os.chdir("..")
        MainWindow.singleton = MainWindow()


# starts PyQt application
def main():
    app = QApplication(sys.argv)
    app.aboutToQuit.connect(reader.kill_reader_thread)
    app.aboutToQuit.connect(generator.kill_generator_thread)
    app.setStyle("fusion")
    MainWindow.restart()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
