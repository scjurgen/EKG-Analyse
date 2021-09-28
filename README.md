# EKG-Analyse

Analyse EKG recorded with Mkrzero and a SparkFun Single Lead Heart Rate Monitor - AD8232

## Disclaimer

Whatever kind of insights you obtain by using this software: don't rely on it. Go to a Cardiologist!
End of disclaimer.

## ECG

I used an MKRZERO for recording the ECG data. MKRZERO has the advantage of a relative small
footprint, portable because of LIPO powering and it has an SD card reader slot.

The Sparkfun AD8232 is a simple recorder witch can be used with standard ECG pads.

The recording is done with a 500Hz samplerate.

## AnalyseECG.py

This small programm takes a recorded binary file, filters it using a lowpass filter to remove hum (50/60Hz).

It then tries to analyse the PQRST phases of the heartrate signal.
It can output prints of the timeseries and will also show you zone of interests. 

I only had my own recordings, so no idea if the algorithms are ok. There is a ton of literature to analyse ecg 
data but I used a very simple approach based on some heuristics that look like working for me.

You can save wave files and load the files into a wavefile editor (i.e. Audacity) for some visual inspection.

[file://sample.png]