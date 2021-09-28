#!/usr/bin/env python3
"""
P = small wave before RS (PR Interval)
Q =  before big pos pulse
R =  full pos pulse
S = negative pulse
T wave bump after S
RR interval
QRS amplitudes
"""
import numpy

from scipy import signal
import matplotlib.pyplot as plt
import os
import soundfile
import struct
import sys

sampleRate = 500

def plot_single_segment(data: list[float], sampleShowSize: int, sampleShowStart: int):
    if sampleShowStart < 0:
        sampleShowStart = 0
    if sampleShowStart+sampleShowSize >= len(data):
        sampleShowStart = len(data)-sampleShowSize-1

    t = numpy.linspace(0, sampleShowSize/sampleRate, sampleShowSize, False)
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
    fig.set_size_inches(12, 5)
    ax1.plot(t, data[sampleShowStart:sampleShowStart + sampleShowSize])
    ax1.set_title(sampleShowStart)
    ax1.axis([0, sampleShowSize/sampleRate, -0.5, 1])
    derivative = numpy.gradient(data[sampleShowStart:sampleShowStart + sampleShowSize])
    ax2.plot(t, derivative)
    ax2.set_title('1st derivative')
    ax2.axis([0, sampleShowSize/sampleRate, -0.15, 0.15])
    ax2.set_xlabel('t')
    plt.tight_layout()
    try:
        os.mkdir("images")
    except:
        pass
    plt.savefig(f"images/{sampleShowStart}.png")


def plot_beat_segment(data, filtered, sampleShowSize, sampleShowStart):
    t = numpy.linspace(0, sampleShowSize / sampleRate, sampleShowSize, False)
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, sharex=True)
    fig.set_size_inches(16, 10)
    ax1.grid(which='both', axis='both')
    ax2.grid(which='both', axis='both')
    ax3.grid(which='both', axis='both')
    ax1.plot(t, data[sampleShowStart:sampleShowStart + sampleShowSize])
    ax1.set_title('Original')
    ax1.axis([0, sampleShowSize/sampleRate, -0.5, 1])
    ax2.plot(t, filtered[sampleShowStart:sampleShowStart + sampleShowSize])
    ax2.set_title('Filtered')
    ax2.axis([0, sampleShowSize/sampleRate, -0.5, 1])
    ax2.set_xlabel('Time [seconds]')
    derivative = numpy.gradient(filtered)
    ax3.plot(t, derivative[sampleShowStart:sampleShowStart + sampleShowSize])
    ax3.set_title('1st derivative')
    ax3.axis([0, sampleShowSize/sampleRate, -0.25, 0.15])
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
        self.sample_frequency = sampleRate
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

        sos = signal.butter(6, self.hum_hertz / self.sample_frequency, 'low', analog=False, output='sos')
        self.filtered = signal.sosfilt(sos, self.data)
        sampleShowSize = 1400
        sampleShowStart = 4950
        plot_beat_segment(self.data, self.filtered, sampleShowSize, sampleShowStart)

    def local_min_max(self, start_position: int, length: int) -> list[int]:
        current_min = self.filtered[start_position]
        current_max = current_min
        for i in range(start_position, start_position+length):
            if i >= len(self.filtered):
                break
            if self.filtered[i] > current_max:
                current_max = self.filtered[i]
            if self.filtered[i] < current_min:
                current_min = self.filtered[i]
        return [current_min, current_max]

    def kernel_correlation(self, position: int, kernel:list[int]):
        pass

    def best_correlation(self, positionA: int, positionB: int, size: int):
        pass

    def best_correlation(self, fix_position: int, move_position: int, size: int):
        pass

    def find_R_2_R_Peaks(self):
        r_peaks_count = 0
        r_phase = PhaseData()
        s_phase = PhaseData()
        current_phase = 'P'
        last_plot_pos = 0
        pos = 0
        last_i = 0
        cnt = 0
        for i in self.filtered:
            cnt -= 1
            if cnt < 0:
                min, max = self.local_min_max(pos, sampleRate*2)
                print(f"minmax [{pos}]: {min} {max}")
                cnt = sampleRate
            derived = i - last_i
            last_i = i
            pos += 1
            if current_phase == 'P':
                current_phase = 'Q'
            elif current_phase == 'Q':
                if i > max*2/3:
                    current_phase = 'R'
                    r_phase.seed_min_max(i, pos)
                    rr = r_phase.max_pos - r_phase.prev_max_pos
                    rs_ptp = r_phase.prev_max - s_phase.min
                    rs = s_phase.max_pos - r_phase.prev_max_pos
                    bpm = int(60 * sampleRate / rr)
                    if bpm < 50 or bpm > 150:
                        if last_plot_pos < r_phase.prev_max_pos - sampleRate*2:
                            last_plot_pos = r_phase.prev_max_pos+sampleRate*4
                            plot_single_segment(self.filtered, sampleRate*6, r_phase.prev_max_pos - sampleRate*3)
                            print(f"* {r_phase.prev_max_pos} bpm={bpm} rs={rs} peak to peak:{rs_ptp}")

                    if r_peaks_count < 100:
                        print(f"{r_phase.prev_max_pos} bpm={bpm} rs={rs} peak to peak:{rs_ptp}")
            elif current_phase == 'R':
                if i < min*2/3:
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
ekg.find_R_2_R_Peaks()

