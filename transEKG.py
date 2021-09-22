#!/usr/bin/env python3
"""
P = small wave before RS (PR Interval)
Q =  before big pos pulse
R =  full pos pulse
S = negative pulse
T wave bump after S
RR interval
QRS amplitude
"""
import numpy

from scipy import signal
import matplotlib.pyplot as plt

import soundfile
import struct
import sys


def plot_single_segment(data, sampleShowSize, sampleShowStart):
    if sampleShowStart < 0:
        sampleShowStart = 0

    t = numpy.linspace(0, sampleShowSize/250, sampleShowSize, False)
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
    fig.set_size_inches(12, 5)
    ax1.plot(t, data[sampleShowStart:sampleShowStart + sampleShowSize])
    ax1.set_title(sampleShowStart)
    ax1.axis([0, sampleShowSize/250, -0.5, 1])
    derivative = numpy.gradient(data[sampleShowStart:sampleShowStart + sampleShowSize])
    ax2.plot(t, derivative)
    ax2.set_title('1st derivative')
    ax2.axis([0, sampleShowSize/250, -0.5, 1])
    ax2.set_xlabel('t')
    plt.tight_layout()
    plt.savefig(f"{sampleShowStart}.png")


def plot_beat_segment(data, filtered, sampleShowSize, sampleShowStart):
    t = numpy.linspace(0, sampleShowSize / 250, sampleShowSize, False)
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, sharex=True)
    fig.set_size_inches(16, 10)
    ax1.grid(which='both', axis='both')
    ax2.grid(which='both', axis='both')
    ax3.grid(which='both', axis='both')
    ax1.plot(t, data[sampleShowStart:sampleShowStart + sampleShowSize])
    ax1.set_title('Original')
    ax1.axis([0, sampleShowSize/250, -0.5, 1])
    ax2.plot(t, filtered[sampleShowStart:sampleShowStart + sampleShowSize])
    ax2.set_title('Filtered')
    ax2.axis([0, sampleShowSize/250, -0.5, 1])
    ax2.set_xlabel('Time [seconds]')
    derivative = numpy.gradient(filtered)
    ax3.plot(t, derivative[sampleShowStart:sampleShowStart + sampleShowSize])
    ax3.set_title('1st derivative')
    ax3.axis([0, sampleShowSize/250, -0.25, 0.15])
    ax3.set_xlabel('Time [seconds]')
    plt.tight_layout()
    #plt.show()
    plt.savefig(f"sample.png")


class PhaseData:
    def __init__(self):
        self.max = 0
        self.min = 0
        self.min_pos = 0
        self.max_pos = 0
        self.prev_min_pos = 0
        self.prev_max_pos = 0
        self.prev_min = 0
        self.prev_max = 0

    def get_delta_min_pos(self):
        return self.min_pos - self.prev_min_pos

    def seed_min_max(self, seed: float, pos: int):
        self.prev_min = self.min
        self.prev_max = self.max
        self.prev_min_pos = self.min_pos
        self.prev_max_pos = self.max_pos
        self.min_pos = pos
        self.max_pos = pos
        self.min = seed
        self.max = seed

    def set_new_value(self, value: float, pos: int):
        if value < self.min:
            self.min = value
            self.min_pos = pos
        if value > self.max:
            self.max = value
            self.max_pos = pos


class EkgAnalysis:

    def __init__(self):
        self.hum_hertz = 50
        self.sample_frequency = 250
        self.filtered = None
        self.data = None

    def load_raw_data(self, raw_file: str):
        cnt = 0
        self.data = []
        with open(raw_file, "rb") as f:
            while True:
                cnt += 1
                value = f.read(2)
                if not value:
                    break
                value_f32 = self.getValue(value)
                self.data.append(value_f32)

        sos = signal.butter(4, self.hum_hertz / self.sample_frequency, 'low', analog=False, output='sos')
        self.filtered = signal.sosfilt(sos, self.data)
        sampleShowSize = 700
        sampleShowStart = 4950
        plot_beat_segment(self.data, self.filtered, sampleShowSize, sampleShowStart)

    def find_R_2_R_Peaks(self):
        r_peaks_count = 0
        r_phase = PhaseData()
        s_phase = PhaseData()
        current_phase = 'P'
        last_plot_pos = 0
        pos = 0
        last_i = 0
        for i in self.data:
            derived = i - last_i
            last_i = i
            pos += 1
            if current_phase == 'P':
                current_phase = 'Q'
            elif current_phase == 'Q':
                if i > 0.4:
                    current_phase = 'R'
                    r_phase.seed_min_max(i, pos)
                    rr = r_phase.prev_max_pos - r_phase.max_pos
                    rs_ptp = r_phase.prev_max - s_phase.min
                    rs = s_phase.max_pos - r_phase.prev_max_pos
                    bpm = int(60 * 250 / rr)
                    if bpm < 50 or bpm > 150:
                        if last_plot_pos < r_phase.prev_max_pos - 500:
                            last_plot_pos = r_phase.prev_max_pos+1000
                            plot_single_segment(self.data, 1600, r_phase.prev_max_pos - 900)
                            print(f"* {r_phase.prev_max_pos} bpm={bpm} rs={rs} peak to peak:{rs_ptp}")

                    if r_peaks_count < 100:
                        print(f"{r_phase.prev_max_pos} bpm={bpm} rs={rs} peak to peak:{rs_ptp}")
            elif current_phase == 'R':
                if i < 0.2:
                    r_peaks_count += 1
                    current_phase = 'S'
                    s_phase.seed_min_max(i, i)
            elif current_phase == 'S':
                if derived > 0:
                    current_phase = 'T'
            elif current_phase == 'T':
                    if derived < 0:
                        current_phase = 'Q'

        print(f"peaks found: {r_peaks_count}")

    @staticmethod
    def getValue(byteValue: bytearray) -> numpy.float32:
        return numpy.float32((int.from_bytes(byteValue, 'little')-512.0)/512.0)

    @staticmethod
    def getInt(intValue: int):
        return struct.pack("<h", intValue)

    def save_as_wave(self, wave_file: str, sample_rate: int = 8000):
        try:
            sample_count = len(self.filtered)
            print(f"Writing soundfile '{wave_file}' with {sample_count}")
            soundfile.write(wave_file, self.filtered, sample_rate)
        except IOError:
            print(f"Error while creating soundfile '{wave_file}'!")

ekg = EkgAnalysis()
ekg.load_raw_data(sys.argv[1])
ekg.save_as_wave(sys.argv[2])
#ekg.find_R_2_R_Peaks()

