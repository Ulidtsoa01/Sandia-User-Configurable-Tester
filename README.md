# README

## Introduction

Our team is creating a software solution to control a reconfigurable electronics product tester. This tester can control and automate data acquisition and test sequencing using DAQ sensors, while the GUI allows users to configure sensors and initiate testing. The user can generate a report after running a test suite of configured tests.

## Requirements

This code has been run and tested on:

- Python - 3.9.5

## External Deps

- Git - Downloat latest version at https://git-scm.com/book/en/v2/Getting-Started-Installing-Git

## Installation

Download this code repository by using git:

`https://github.com/FA23-CSCE482-capstone-classroom/capstone-sandia-user-configurable-tester.git`

## Execute Code

If using Windows, use the following commands to download these library dependencies.

1. `pip install PySide6`
2. `pip install matplotlib`
3. `pip install pandas`
4. `pip install nidaqmx`
5. `pip install keyboard`
6. `pip install profig`
7. `pip install reportlab`

Run the app

`python app.py`

1. Plug in USB DAQ device and install DAQ drivers
2. Run the application (from VS code or terminal)
3. Configure your DAQ device and channels
4. Configure your test steps
5. Configure your test suite
6. Click “Start Test Suite”
7. After tests finish running, go to the Analysis Tab
8. Click through steps for each test in the test suite
9. Go to the Report Preview
10. Fill out report fields (Custom Field allows you to populate a row in the report header with a custom title and text)
11. Click report type you want to generate (JSON or PDF)

## Support

The support of this app has been closed due to having zero customers.

## Contributing

[Contribution guidelines for this project](.github/CONTRIBUTING.md)

## File Structure

- app.py imports from daq.py, signal_analysis.py, report.py
- Config files: app.py reads from init.cfg and a user-named config file (default.cfg by default). app.py can also create multiple config files.
- Report files: report.py creates user-named report files in the .json and .pdf format

## Available Functions

### app.py functions
void main(): starts PyQt application
class MainWindow(QMainWindow)
- void __init__(self): Holds important variables used by child classes. Creates the main tabs as well as a file menu.
- void _config(self): At the start of the program, load the last used config file using the profig library
- void _new(self): Connected to button_new; restart window with "___.cfg" set as the current config file.
- void _open(self): Connected to button_open; choose file, then restart window
- void _save(self): Connected to button_save; save values to config file
- void _saveas(self): Connected to button_save_as; choose file, then save values to config file
- void _createMenu(self): Creates the file menus, "File" and "Help"
- static void restart(): Restarts program by setting MainWindow

class TestRunner(QWidget)
- void __init__(self, parent): Graph controls, graph, and device controls on the left (mainGrid). QTabWidget holding tabs for TestSuite and TestConfig on the right (rightPane).
- void update_plot(self): Does the computation to graph incoming signal
- void run_test(self): is called when play button is clicked, runs all of the test in the test suite
- void pause_live_graph(self): Handles pausing the live graph, is tied to the pause button
- void recordData(self): Performs data collection and pulls data from the reader into app. Will also start the next test in the test suite.
- stopTest(self): Stops a running test suite and resets all the values for testing

class DeviceSelect(QWidget)
- void __init__(self, parent, io): io determines the type, which is either "input" or "output"
- void comboIndexChanged(self): connected to self.deviceCombo.currentIndexChanged
- void changeChannel(self): connected to self.listWidget.itemSelectionChanged
- void signalComboIndexChanged(self): Choose between different types of simulated signals

class TestSuite(QWidget)
- void __init__(self, parent): drag-and-drop list that determines the run order of the tests
- void comboChange(self): connected to self.comm.testListChanged
- void listChange(self): connected to self.list_widget.model().rowsMoved
- void addTest(self): connected to self.add_test button
- void deleteTest(self): connected to self.delete_test button

class TestConfig(QWidget)
- void __init__(self, parent): form to input test configuration parameters
- string checkNA(self, lineEdit, i, name): return as a string after checking if input is N/A
- void comboIndexChanged(self, i): set the QLabels to the parameters of the selected test when the combo selection changes
- void clearTest(self): Connected to self.clear_test button; clears text from the QLabels
- validateInt(self, text): returns an int or "N/A"
- validateFloat(self, text): returns a float or "N/A"
- void saveTest(self): Connected to self.save_test button; if the Qlabel is empty, the parameter is saved as "N/A"
- void deleteTest(self): Connected to self.delete_test button

class Analysis(QWidget)
- void __init__(self, parent): The purpose of this class is to handle the analysis of the signal once the data collection is complete. Any tests that are in the test suite will be run, and the results panel will be updated accordingly
- void step_right(self): Function to increment the current step. Includes bounds checking which prevents incrementing past the size of the step list
- void step_left(self): Function to decrement the current step. Includes bounds checking which prevents decrementing below zero.
- void listChange(self): Updates the list of tests in the analysis tab whenever the testSuite is changed. Should be attached to the testSuiteChanged signal in the comm class
 - dict getTestParams(self, test_name):  Gets the parameters of a specified test in configuredTests
- list getStepList(self, data, params): Returns a list of dicts where each dict is the results of a step in a test. The steps in the test are determined by which fields in the test configuration. are not set to "N/A"
- void updateResults(self): Updates self.results with the results from the running of the testSuite. self.results consists of a list of dicts where each dict represents a test. Each test dict contains the following keys:
test_name: the name of the test
	test_passed: a boolean showing if the test passed or not. A test fails if any step within that test fails
	results: a list of dicts where each dict is the results of an individual step. Refer to signal_analysis.py for the structure of the step results dict
- void updateResultsGraph(self): Updates the graph in the results pane with the data for the test that is currently clicked on. Depending on what step is currently selected, different markings are put on the graph to better display the results
- void list_click_helper(self): Updates the graph with the test which is currently selected. Resets step_index to 0 and enables/re-enables step buttons accordingly.

### other app.py classes
class Communicate(QObject): holds signal
class QHLine(QFrame): horizontal divider
class ListWidgetItem(QListWidgetItem): overrides QListWidgetItem
class ListWidgetItemB(QListWidgetItem): overrides QListWidgetItem

### report.py functions
class ReportPreview(QWidget)
- void __init__(self, parent): QWebEngineView displays a pdf file on the left (mainGrid). Form to input report parameters on the right (rightPane).
- dict createHeader(self): Returns dict holding the general report info
- void generateJSON(self): Connected to self.generate_json button. Chooses json file to export report to.
- string checkNA(self, text): Return as a string after checking if input is N/A
- void generatePDF(self): Connected to self.generate_pdf button. Chooses pdf file to export report to. Sets self.webView to generated pdf.
- void _setValues(self): Enables buttons when test suite finishes
