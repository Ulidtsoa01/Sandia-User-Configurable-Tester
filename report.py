import json
import os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtWebEngineWidgets import QWebEngineView


class ReportPreview(QWidget):
    testDone = False

    # QWebEngineView displays a pdf file on the left (mainGrid).
    # Form to input report parameters on the right (rightPane).
    def __init__(self, parent):
        super(ReportPreview, self).__init__(parent)
        self.testList = self.parent().testList
        self.testSuite = self.parent().testSuite
        self.configuredTests = self.parent().configuredTests
        self.parent().comm.testDone.connect(self._setValues)
        self.webView = self.parent().webView
        self.results = self.parent().results
        self.name = QLineEdit()
        self.custom_field_title = QLineEdit()
        self.custom_field_title.setPlaceholderText("Custom Field Title")
        self.custom_field_text = QLineEdit()
        self.custom_field_text.setPlaceholderText("Custom Field Text")
        custom_field_layout = QHBoxLayout()
        custom_field_layout.addWidget(self.custom_field_title)
        custom_field_layout.addWidget(self.custom_field_text)
        self.passing_threshold = QLineEdit()
        self.generate_json = QPushButton("Generate JSON")
        self.generate_pdf = QPushButton("Generate PDF")
        self.generate_json.pressed.connect(self.generateJSON)
        self.generate_pdf.pressed.connect(self.generatePDF)
        if not self.testDone:
            self.generate_json.setEnabled(False)
            self.generate_pdf.setEnabled(False)

        form = QFormLayout()
        form.addRow("Report Name", self.name)
        form.addRow("Custom Field", custom_field_layout)
        form.addRow("Passing Threshold", self.passing_threshold)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.generate_json)
        button_layout.addWidget(self.generate_pdf)
        form.addRow(button_layout)
        formWidget = QWidget()
        formWidget.setLayout(form)

        self.webView.settings().setAttribute(
            self.webView.settings().WebAttribute.PluginsEnabled, True
        )
        self.webView.settings().setAttribute(
            self.webView.settings().WebAttribute.PdfViewerEnabled, True
        )

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.setMovable(True)
        tabs.addTab(formWidget, "Report Parameters")

        outerLayout = QHBoxLayout()
        mainGrid = QVBoxLayout()  # grey4
        mainGrid.addWidget(self.webView)
        rightPane = QVBoxLayout()  # grey3
        rightPane.addWidget(tabs)
        outerLayout.addLayout(mainGrid, 3.5)
        outerLayout.addLayout(rightPane, 1)
        self.setLayout(outerLayout)

    # Returns dict holding the general report info
    def createHeader(self):
        num_tests_passed = 0
        for dict in self.results:
            if dict["test_passed"]:
                num_tests_passed += 1
        overall_pass = (
            True if num_tests_passed >= int(self.passing_threshold.text()) else False
        )
        header = {
            "report_name": self.name.text(),
            self.custom_field_title.text(): self.custom_field_text.text(),
            "date_and_time": datetime.now().strftime("%m/%d/%Y %H:%M:%S"),
            # "execution_time":
            "tests_passed": str(num_tests_passed) + "/" + str(len(self.results)),
            "passing_threshold": self.passing_threshold.text(),
            "result": overall_pass,
        }
        return header

    # Connected to self.generate_json button. Chooses json file to export report to.
    def generateJSON(self):
        header = self.createHeader()

        data = {"report_header": header, "test_sequence": self.results}
        json_object = json.dumps(data, indent=4)

        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setViewMode(QFileDialog.Detail)
        dialog.setNameFilter("JSON (*.json)")
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        filenames = ""
        if dialog.exec():
            filenames = dialog.selectedFiles()

        with open(filenames[0], "w") as outfile:
            outfile.write(json_object)
        print("JSON exported to ", filenames[0])

    # Return as a string after checking if input is N/A
    def checkNA(self, text):
        text = str(text)
        if text != "N/A":
            return text
        else:
            return ""

    # Connected to self.generate_pdf button. Chooses pdf file to export report to. Sets self.webView to generated pdf.
    def generatePDF(self):
        styles = getSampleStyleSheet()
        # styles.list()
        heading1Style = styles["Heading1"]
        heading1Style.alignment = TA_CENTER
        heading2Style = styles["Heading2"]
        heading2Style.alignment = TA_LEFT
        heading3Style = styles["Heading3"]
        heading3Style.alignment = TA_LEFT
        normalStyle = styles["Normal"]

        # Table for general report info
        header = self.createHeader()
        heading1 = Paragraph(header["report_name"], style=styles["Heading1"])
        # headingTestStatus = Paragraph("Test Status", style=styles["Heading2"])
        headingTestSequence = Paragraph("Test Sequence", style=styles["Heading2"])
        reportData = [
            ["Date and Time", header["date_and_time"]],
            # ["Execution time", ""],
            ["Tests passed", header["tests_passed"]],
            ["Passing threshold", header["passing_threshold"]],
            ["Result", ("Passed" if header["result"] else "Failed")],
        ]
        if self.custom_field_title.text() != "":
            reportData.insert(
                0, [self.custom_field_title.text(), self.custom_field_text.text()]
            )
        reportStyle = TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ]
        )
        cellColor = colors.green if header["result"] else colors.red
        reportStyle.add("BACKGROUND", (1, 3), (1, 3), cellColor)
        reportTable = Table(reportData, style=reportStyle, hAlign="CENTER")
        flowables = []
        flowables.append(heading1)
        flowables.append(reportTable)
        # flowables.append(headingTestStatus)

        testStatusData = [["Test", "Result"]]
        for dict in self.results:
            testStatusData.append(
                [dict["test_name"], ("Passed" if dict["test_passed"] else "Failed")]
            )
        testStatusStyle = TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
            ]
        )
        for row in range(1, len(testStatusData)):
            cellColor = colors.white
            if testStatusData[row][1] == "Passed":
                cellColor = colors.green
            elif testStatusData[row][1] == "Failed":
                cellColor = colors.red
            testStatusStyle.add("BACKGROUND", (1, row), (1, row), cellColor)
        testStatusTable = Table(testStatusData, style=testStatusStyle, hAlign="CENTER")
        flowables.append(testStatusTable)

        flowables.append(headingTestSequence)
        # Makes a table detailing the steps of each test
        for dict in self.results:
            headingText = (
                dict["test_name"]
                + " - "
                + ("Passed" if dict["test_passed"] else "Failed")
            )
            headingTest = Paragraph(headingText, style=styles["Heading3"])
            testData = [
                ["Step", "Status", "Measurement", "Units", "Limits", ""],
                ["", "", "", "", "Low Limit", "High Limit"],
            ]
            for idict in dict["results"]:
                if idict["step_name"] != "find_peaks":
                    testData.append(
                        [
                            idict["step_name"],
                            ("Passed" if idict["status"] else "Failed"),
                            Paragraph(
                                self.checkNA(idict["measurement"]),
                                style=styles["Normal"],
                            ),
                            self.checkNA(idict["units"]),
                            self.checkNA(idict["low_limit"]),
                            self.checkNA(idict["high_limit"]),
                        ]
                    )
            testStyle = TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                    ("SPAN", (-2, 0), (-1, 0)),
                    ("ALIGN", (-2, 0), (-1, 0), "CENTER"),
                ]
            )
            for i in range(0, 4):
                testStyle.add("SPAN", (i, 0), (i, 1))
            for row in range(2, len(testData)):
                cellColor = colors.white
                if testData[row][1] == "Passed":
                    cellColor = colors.green
                elif testData[row][1] == "Failed":
                    cellColor = colors.red
                testStyle.add("BACKGROUND", (1, row), (1, row), cellColor)
            testTable = Table(testData, style=testStyle, hAlign="CENTER")
            flowables.append(headingTest)
            flowables.append(testTable)

        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setViewMode(QFileDialog.Detail)
        dialog.setNameFilter("PDF (*.pdf)")
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        filenames = ""
        if dialog.exec():
            filenames = dialog.selectedFiles()

        margin = 1 * inch
        doc = SimpleDocTemplate(
            filenames[0],
            pagesize=letter,
            rightMargin=margin,
            leftMargin=margin,
            topMargin=margin,
            bottomMargin=margin,
        )
        doc.build(flowables)

        self.webView.load(QUrl(f"file:///{filenames[0]}"))
        print("PDF exported to ", filenames[0])

    # Enables buttons when test suite finishes
    def _setValues(self):
        self.testDone = True
        self.generate_json.setEnabled(True)
        self.generate_pdf.setEnabled(True)
