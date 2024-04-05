# README

## Introduction

Our team created a software solution to control a reconfigurable electronics product tester. This tester can control and automate data acquisition and test sequencing using DAQ sensors, while the GUI allows users to configure sensors and initiate testing. The user can generate a report after running a test suite of configured tests.

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
