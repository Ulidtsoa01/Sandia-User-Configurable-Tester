import numpy as np 
import matplotlib.pyplot as plt 
import pandas as pd 
from scipy import signal

# Various signal analysis functions
# Each step returns a results dict in the following format
# step_name: the name of the step
# status: boolean value representing if the step passed or not
# measurement: some kind of data structure that contains the measured result of the test.
#              This is often a float value, but sometimes it is an array if multiple data
#              values are necessary
# units: the units of the result of the test
# low_limit: the lowest allowable value for the measurement
# high_limit: the highest allowable value for the measurement               
class Analyzer:

    def __init__(self):
        self.data = [0]*50

    def max_signal(data):
        max = float('-inf')
        for i in data:
            if i > max:
                max = i
        return max

    def min_signal(data):
        min = float('inf')
        for i in data:
            if i < min:
                min = i
        return min
    
    # Test that determines if the signal every passes a minimum and maximum threshold
    # min_tol and  max_tol are the minimum and maximum tolerances for the signal, respectively
    def min_max_signal(self, data, min_tol, max_tol):
        max = Analyzer.max_signal(data)
        min = Analyzer.min_signal(data)
        passes = False
        if (max < max_tol) and (min > min_tol):
            passes = True
        results = {
            "step_name" : "min_max_signal",
            "status" : passes,
            "measurement" : [min, max],
            "units" : "N/A",
            "low_limit" : min_tol,
            "high_limit" : max_tol
        }

        return results

    # Test that finds all the peaks in the signal
    # The measurement is a list of three lists. The first list is the indicies of the left prominences of each peak,
    # the second is the indicies of the peaks themselves, and the third is the indicies of the right prominences of each peak.
    def find_peaks(self, data):
        peaks, _ = signal.find_peaks(data)
        prominences, _, _ = signal.peak_prominences(data, peaks)
        selected = prominences > 0.5 * (np.min(prominences) + np.max(prominences))
        left = peaks[:-1][selected[1:]]
        right = peaks[1:][selected[:-1]]
        top = peaks[selected]
        
        results = {
            "step_name" : "find_peaks",
            "status" : True,
            "measurement" : [left, top, right],
            "units" : "N/A",
            "low limit" : "N/A",
            "high limit" : "N/A"
        }

        return results 

    # Test that checks if the average signal is within a bound
    # min_tol and  max_tol are the minimum and maximum tolerances for the average signal, respectively
    def avg_signal(self, data, min_tol, max_tol):
        sum = 0
        for i in data:
            sum += i
        average = (sum / len(data))
        passes = True
        if average < min_tol or average > max_tol:
            passes = False
        results = {
            "step_name" : "average_signal",
            "status" : passes,
            "measurement" : average,
            "units" : "N/A",
            "low_limit" : min_tol,
            "high_limit" : max_tol
        }

        return results

    # Test that finds the rise time for all peaks.
    # The measurement is a list of the rise times for each peak
    # The step fails if any of the rise times are outside the given bounds
    # The start_percent is the percent of the peak where rise time will start being counted
    # The end_percent is the percent of the peak where rise time will stop being counted
    # min_tol and max_tol are the minimum and maximum tolerances for the rise times, respectively 
    # The sample rate allows us to convert the number of samples (which is how the data arrray is formatted)
    # into time units
    def rise_time_all_peaks(self, data, start_percent, end_percent, min_tol, max_tol, sample_rate):
        peaks, _ = signal.find_peaks(data)
        prominences, _, _ = signal.peak_prominences(data, peaks)
        selected = prominences > 0.5 * (np.min(prominences) + np.max(prominences))
        left = peaks[:-1][selected[1:]]
        rise_times = []
        index = 0
        top = peaks[selected]
        if (len(top) == 0):
            rise_times.append(0)
            for i in range(left[pk], top[pk]):
                if data[i] >= (start_percent * 0.01 * data[top[pk]]):
                    rise_times[index] += ((1 / sample_rate) * 1000)
                if data[i] >= (end_percent * 0.01 * data[top[pk]]):
                    break
            index += 1
        else:
            for pk in range(len(top) - 1):
                rise_times.append(0)
                for i in range(left[pk], top[pk]):
                    if data[i] >= (start_percent * 0.01 * data[top[pk]]):
                        rise_times[index] += ((1 / sample_rate) * 1000)
                    if data[i] >= (end_percent * 0.01 * data[top[pk]]):
                        break
                index += 1
        max_rise_time = max(rise_times)
        min_rise_time = min(rise_times)
        passes = True
        if (max_rise_time > max_tol) or (min_rise_time < min_tol):
            passes = False
        results = {
            "step_name" : "rise_time_peak",
            "status" : passes,
            "measurement" : rise_times,
            "units" : "ms",
            "low_limit" : min_tol,
            "high_limit" : max_tol
        }
        return results

    # Test that finds the fall time for fall peaks.
    # The measurement is a list of the fall times for each peak
    # The step fails if any of the fall times are outside the given bounds
    # The start_percent is the percent of the peak where fall time will start being counted
    # The end_percent is the percent of the peak where fall time will stop being counted
    # min_tol and max_tol are the minimum and maximum tolerances for the fall times, respectively 
    # The sample rate allows us to convert the number of samples (which is how the data arrray is formatted)
    # into time units
    def fall_time_all_peaks(self, data, start_percent, end_percent, min_tol, max_tol, sample_rate):
        peaks, _ = signal.find_peaks(data)
        prominences, _, _ = signal.peak_prominences(data, peaks)
        selected = prominences > 0.5 * (np.min(prominences) + np.max(prominences))
        right = peaks[1:][selected[:-1]]
        fall_times = []
        index = 0
        top = peaks[selected]
        if (len(top) == 0):
            fall_times.append(0)
            for i in range(top[pk], right[pk]):
                if data[i] <= (start_percent * 0.01 * data[top[pk]]):
                    fall_times[index] += ((1 / sample_rate) * 1000)
                if data[i] <= (end_percent * 0.01 * data[top[pk]]):
                    break
            index += 1
        else:
            for pk in range(len(top) - 1):
                fall_times.append(0)
                for i in range(top[pk], right[pk]):
                    if data[i] <= (start_percent * 0.01 * data[top[pk]]):
                        fall_times[index] += ((1 / sample_rate) * 1000)
                    if data[i] <= (end_percent * 0.01 * data[top[pk]]):
                        break
                index += 1
        max_fall_time = max(fall_times)
        min_fall_time = min(fall_times)
        passes = True
        if (max_fall_time > max_tol) or (min_fall_time < min_tol):
            passes = False
        results = {
            "step_name" : "fall_time_peak",
            "status" : passes,
            "measurement" : fall_times,
            "units" : "ms",
            "low_limit" : min_tol,
            "high_limit" : max_tol
        }
        return results
    
    # Test that finds the average rise time
    # The start_percent is the percent of the peak where rise time will start being counted
    # The end_percent is the percent of the peak where rise time will stop being counted
    # min_tol and max_tol are the minimum and maximum tolerances for the rise times, respectively 
    # The sample rate allows us to convert the number of samples (which is how the data arrray is formatted)
    # into time units
    def avg_rise_time(self, data, start_percent, end_percent, min_tol, max_tol, sample_rate):
        prev_results = self.rise_time_all_peaks(data, start_percent, end_percent, min_tol, max_tol, sample_rate)
        rise_times = prev_results["measurement"]
        sum = 0
        for x in rise_times:
            sum += x
        average = sum / len(rise_times)
        passes = True
        if (average > max_tol) or (average < min_tol):
            passes = False
        results = {
            "step_name" : "avg_rise_time",
            "status" : passes,
            "measurement" : average,
            "units" : "ms",
            "low_limit" : min_tol,
            "high_limit" : max_tol
        }
        return results
    
    # Test that finds the average fall time
    # The start_percent is the percent of the peak where fall time will start being counted
    # The end_percent is the percent of the peak where fall time will stop being counted
    # min_tol and max_tol are the minimum and maximum tolerances for the fall times, respectively 
    # The sample rate allows us to convert the number of samples (which is how the data arrray is formatted)
    # into time units
    def avg_fall_time(self, data, start_percent, end_percent, min_tol, max_tol, sample_rate):
        prev_results = self.fall_time_all_peaks(data, start_percent, end_percent, min_tol, max_tol, sample_rate)
        fall_times = prev_results["measurement"]
        sum = 0
        for x in fall_times:
            sum += x
        average = sum / len(fall_times)
        passes = True
        if (average > max_tol) or (average < min_tol):
            passes = False
        results = {
            "step_name" : "avg_fall_time",
            "status" : passes,
            "measurement" : average,
            "units" : "ms",
            "low_limit" : min_tol,
            "high_limit" : max_tol
        }
        return results


