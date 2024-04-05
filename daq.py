import nidaqmx
import threading
from nidaqmx.types import CtrTime
from nidaqmx import stream_readers
from nidaqmx import stream_writers
import numpy as np


# Super class of Reader and Generator
# Stores general information about the DAQs that are connected to the desktop
class Daq:
    def __init__(self):
        self.devices = nidaqmx.system.System.local().devices
        self.deviceNames = list(map(lambda x: x.name, self.devices))
        self.ai_channels = {}  # dictionary of all ai channels (i.e. {Dev1: Dev1/ai0})
        self.ao_channels = {}  # dictionary of all ao channels (i.e. {Dev1: Dev1/ao0})

        # initialize the channels (unpackages the nidaqmx types to just get the names)
        for device in self.devices:
            chanNames = []
            for channel in device.ai_physical_chans:
                chanNames.append(channel.name)
            self.ai_channels[device.name] = chanNames

        for device in self.devices:
            chanNames = []
            for channel in device.ao_physical_chans:
                chanNames.append(channel.name)
            self.ao_channels[device.name] = chanNames


# Class that generates thread that will read in signal on DAQ
class Reader(Daq):
    def __init__(self):
        self.retArray = []
        self.kill = False
        self.sample_rate = 1
        self.ai_chan = "Dev1/ai0"

        Daq.__init__(self)

    # function to read from daq device with a custom sample rate (hz)
    # input: sample_rate - in hz, duration - length of test in seconds
    # output: updated data in retArray
    def read(self, sample_rate, duration):
        self.sample_rate = sample_rate  # sets the sample rate in the class
        with nidaqmx.Task() as task:  # create Task
            task.ai_channels.add_ai_voltage_chan(
                self.ai_chan
            )  # assigns task to analog in channel on daq

            task.timing.cfg_samp_clk_timing(
                sample_rate, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS
            )  # sets the sample rate of DAQ channel

            # Read from DAQ until samples are all collected
            try:
                for _ in range(int(sample_rate * duration)):
                    if self.kill:
                        break
                    data = task.read()
                    self.retArray.append(data)
            except:
                pass

    # returns the length of the current dataSize
    def getCurrDataSize(self):
        return len(self.retArray)

    # returns all of retArray
    def getArray(self):
        return self.retArray

    # return last n samples
    def getEndArray(self, n):
        return self.retArray[-n:]

    # empties retArray
    def clearArray(self):
        self.retArray.clear()

    # Sets the input channel that the thread will read on
    def set_ai_channel(self, chan):
        self.ai_chan = chan

    # spawns a thread for reading on daq
    # input: hz - the sample rate we want the daq to be at (in hz obv)
    # output: a running thread for reading
    def start_reader_thread(self, hz, duration):
        self.kill = False
        reader_thread = threading.Thread(target=self.read, args=[hz, duration])
        reader_thread = threading.Thread(target=self.read, args=[hz, duration])
        reader_thread.start()

    # kills all reader threads
    def kill_reader_thread(self):
        self.kill = True


# Class that generates thread that will produce a signal on DAQ
class Generator(Daq):
    def __init__(self):
        self.ao_chan = "Dev1/ao0"  # default channel to produce signal on
        self.kill = False  # signal to tell the generator thread to stop
        self.signals = {"Sine": self.sine_wave_gen, "Step": self.step_function_gen, "Square": self.square_wave_gen}#["Sine", "Step", "Square"]
        self.currSignal = list(self.signals.keys())[0]
        Daq.__init__(self)

    # function to produce a signal on a daq that looks like a stair case
    # input: none
    # output: Signal being produced on DAQ out channel
    def step_function_gen(self):
        while not self.kill:
            try:
                with nidaqmx.Task() as task:
                    task.ao_channels.add_ao_voltage_chan(
                        self.ao_chan
                    )  # assigns task to analog out channel ao0 on daq
                    task.write([1.1], auto_start=True)  # write out these voltages
                    task.write([2.2], auto_start=True)  # write out these voltages
                    task.write([3.3], auto_start=True)  # write out these voltages
                    task.write([4.4], auto_start=True)  # write out these voltages
            except:
                break

    # function to produce a square wave on DAQ out channel
    # input: none
    # output: Square waves on the analog out channel
    def square_wave_gen(self):
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(self.ao_chan)

            # Set up a stream writer for the task
            stream_writer = nidaqmx.stream_writers.AnalogSingleChannelWriter(
                task.out_stream, auto_start=True
            )

            # Configure the sample rate, frequency, and amplitude of the square wave
            sample_rate = 2000  # 2 kHz sample rate
            square_wave_frequency = 100  # Frequency of the square wave in Hz
            amplitude = 5.0  # Amplitude of the square wave

            # Calculate the number of samples for one cycle of the square wave
            samples_per_cycle = int(sample_rate / square_wave_frequency)

            # Create a square wave waveform
            waveform = np.zeros(samples_per_cycle)
            half_cycle_samples = int(samples_per_cycle / 2)
            waveform[:half_cycle_samples] = amplitude
            waveform[half_cycle_samples:] = -amplitude

            # Write the square wave continuously
            while not self.kill:
                stream_writer.write_many_sample(waveform)

    def sine_wave_gen(self):
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(self.ao_chan)

            # Set up a stream writer for the task
            stream_writer = nidaqmx.stream_writers.AnalogSingleChannelWriter(
                task.out_stream, auto_start=True
            )

            # Configure the sample rate, frequency, and amplitude of the sine wave
            sample_rate = 2000  # 2 kHz sample rate
            sine_wave_frequency = 100  # Frequency of the sine wave in Hz
            amplitude = 5.0  # Amplitude of the sine wave

            # Calculate the number of samples for one cycle of the sine wave
            samples_per_cycle = int(sample_rate / sine_wave_frequency)

            # Create a sine wave waveform
            t = np.arange(samples_per_cycle) / sample_rate
            waveform = amplitude * np.sin(2 * np.pi * sine_wave_frequency * t)

            # Write the sine wave continuously
            while not self.kill:
                stream_writer.write_many_sample(waveform)

    # Sets the output channel that the thread will read on
    def set_ao_channel(self, chan):
        self.ao_chan = chan

    # Returns a list of all available signal functions
    def get_signals(self):
        return self.signals.keys()

    # Sets the signal type to generate
    def set_signal(self, signal):
        self.currSignal = signal

    # spawns a thread for generating on daq
    # output: a running thread for generating a signal
    def start_generator_thread(self):
        self.kill = False
        thread_two = threading.Thread(target=self.signals[self.currSignal])
        thread_two.start()

    # kills all generator threads
    def kill_generator_thread(self):
        self.kill = True
