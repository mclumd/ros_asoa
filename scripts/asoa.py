# -*- coding: utf-8 -*-
"""
Created on Mon Jul 27 07:05:39 2015

@author: justin
"""

import scipy.io.wavfile
import numpy
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import correlate
from numpy.fft import fft
#from Utils import Match
#from scipy.linalg import norm
from matplotlib.backends.backend_pdf import PdfPages
from asoa_io import asoa_io
import time
import sys

tmax = -1
pmax = -1


class MismatchError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class MuteError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class FinishedSpeaking(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


"""

    Returns a number between 0 and 1 indicating the degree of
    correlation.  Right now this works by assuming the frame is short
    and assuming that it's a "speaking" frame if it's maximum value is
    above a given threshold.  A 0 or 1 is returned depending on whether
    or not the frames disagree about whether they're speaking frames.

"""
    
def raw_correlation(tframe, pframe, tthresh=-1, pthresh=-1):
    assert(len(tframe) == len(pframe))
    tf = np.asarray(tframe, dtype='float64')
    pf = np.asarray(pframe, dtype='float64')
    ton = ( np.amax(tf) > tthresh)
    pon = ( np.amax(pf) > pthresh)
    if ( ( ton and pon ) or ( (not ton) and (not pon) ) ):
        return 1.0
    else:
        return 0.0


"""
Say a string and simultaneously record the speech, comparing what's
heard to what you expect to hear in real time.

Parameters:

  string:  the text to say

  delay: an indication of the delay (in seconds) between the start of
  speech and the start of recording.  a delay of 0 indicates that we
  should use the estimate provided by the asoa_io class.

  debug:  0 for no debugging, 1 for debugging messages

"""    

def say(string, delay=0, debug=0, muck_it_up=False):
    speech = asoa_io(string, frame_size=128, muck_it_up=muck_it_up)

    correlation = 1   # We have a high expectation that this will be a match at first
    frame_number = 0
    consecutive_fails = 0
    template_index = 0
    
    speech.generate_speech()
    time.sleep(1)
    template = speech.template_wave
    template_length = len(template)
    frame_length = len(speech.signal[0])
    frame_number=0
    num_frames = template_length / frame_length
    if (delay == 0):
        delay = speech.skip_frames
    if (debug > 0): print "delay is " + repr(delay)
    corr_list = []
    ones = 0
    ones_list = []
    threshold_frame = ((delay)  / frame_length) + 1   # Now we'll have enough info to compute thresholds
    #if threshold_frame < 20: threshold_frame = 20
    #print "Threshold frame is " + repr(threshold_frame)

    T_MOD = 0.5  # How many standard devs for our threshold
    ONES_T = 0.9 # Anything at least this is considered a 1
    t_threshold = 0
    p_threshold = 0
    while ( speech.still_speaking() and (frame_number*frame_length < template_length) ):
        #print( repr(speech.still_speaking()) + "\t" + repr(frame_number*frame_length) + "\t" + repr(template_length ))
        # Get perceived frame.  Since the list is filled dynamically,
        # we may have to wait for it.
        try:
            pframe = speech.signal[frame_number]
        except IndexError:
            pframe = []
            while (pframe == []):
                try:
                    pframe = speech.signal[frame_number]
                except IndexError:
                    pframe=[]
                    time.sleep(0.1)
                    if (debug > 2): print "sleeping; frame number is " + repr(frame_number)
                        
        # Special processing for initial frames
        # Get target frame and make adjustments for the first frame
        if (frame_number == 0):
            tframe = template[:frame_length - delay]
            pframe = pframe[delay:]
        else:
            tframe = template[ frame_length * frame_number - delay  : frame_length * (frame_number + 1) - delay]

        # Once we have enough data, compute the thresholds.  The multiplier for the perceived waves is lower
        # because we expect a higher max in the non-speech due to noise.  The total amplitude for these waves
        # has also been lower in the examples I've been looking at.
        if (frame_number <= threshold_frame):
            if (frame_number == 0):
                full_signal = pframe
            elif (frame_number == threshold_frame):
                # We're going to assume the first 256 signals of the first frame is pre-speech
                t_threshold = 15 * np.amax(template[: threshold_frame*frame_length])
                p_threshold = 2.5 * np.amax(full_signal)
                #print "Thresholds are: " + repr(t_threshold) + "(t) / " + repr(p_threshold) + "(p)"

                full_signal = np.append(full_signal, pframe)  # probably inefficient; hopefully not too much
            else:
                full_signal = np.append(full_signal, pframe)  # probably inefficient; hopefully not too much
                if np.amax(pframe) == 0:
                    raise MuteError("I don't hear myself.  Is my microphone muted?")
            frame_number += 1
            continue

        # if np.amax(pframe) == 0:
        #     raise MuteError("I don't hear myself.  Is my microphone muted?")
        #     speech.stop_speech()

        # Calculate and process the correlation

        c = raw_correlation(tframe, pframe, t_threshold, p_threshold)
        if (debug > 0): corr_list += [c]
        if ( c < 0.5 ):
            consecutive_fails += 1
            if (debug > 0):  print repr(frame_number) + "(" + repr(consecutive_fails) + ") ", 
            if (consecutive_fails > 190):   #change back to 19; 190 is for debugging
                if (debug < 1): raise MismatchError("Frame number " + str(frame_number))
                else:  print "MISMATCH at " + repr(frame_number), 
        else:
            consecutive_fails = 0

        if (c >= ONES_T):  ones += 1
        ones_list += [float(ones) / (frame_number + 1)]
        
            
        if (debug>2):
            #print "Correlation is: " + repr(correlation)
            print repr(c), 
            #print "Weight is: " + repr(w)

        frame_number += 1
#    print( "Finished with: " + repr(speech.still_speaking()) + "\t" + repr(frame_number*frame_length) + "\t" + repr(template_length ))
    while (speech.still_speaking()):
        time.sleep(0.2)
    speech.stop_speech()


    if (debug > 1):
        full_signal = [ x for y in speech.signal for x in y ]
        f, ax = plt.subplots(3 )
        
        plot_len = len(full_signal) - delay
#        print "dim:  "  + repr(plot_len) + " versus " + repr(len(template[frame_length - delay :plot_len + frame_length - delay] ))
#        print "ones_ratios: " + repr(ones_list)
        
        ax[0].plot(range(plot_len), template[:plot_len] )
        ax[1].plot(range(plot_len), full_signal[delay:plot_len + delay] )
        cp = range(2*plot_len)
        for i in range(plot_len - delay):
            if (i / frame_length) < len(corr_list): cp[i] = corr_list[(i / frame_length)]
        ax[2].plot(range(plot_len - delay), cp[:plot_len - delay], marker=',')
        ax[2].set_ylim([-0.2,1.2])
        plt.show()

            
    
def asoa_test():
#    say("A United States airstrike appears to have badly damaged the hospital run by Doctors Without Borders in the Afghan city of Kunduz early Saturday, killing at least nine hospital staff members and wounding dozens, including patients and staff. Accounts differed as to whether there had been fighting around the hospital that might have precipitated the strike. Two hospital employees, an aide who was wounded in the bombing and a nurse who emerged unscathed, said that there had been no active fighting nearby and no Taliban fighters inside the hospital.  But a Kunduz police spokesman, Sayed Sarwar Hussaini, insisted that Taliban fighters had entered the hospital and were using it as a firing position. ", debug=2)
#    say("Hello.", debug=2)
#    say("Hello.", debug=2, muck_it_up=True)
#
    say("Hello human.  It's a great pleasure  to meet you.  I hope that you are well today.", debug=2)
    say("Hello human.  It's a great pleasure  to meet you.  I hope that you are well today.", debug=2, muck_it_up=True)
    sys.stdout.flush()
    time.sleep(10)
    say("I'm having trouble with my vision and I'm not sure that I see Julia.", debug=0)
    say("I'm having trouble with my vision and I'm not sure that I see Julia.", debug=1, muck_it_up=True)
    sys.stdout.flush()
    time.sleep(10)
    say("Julia is over there", debug=0)
    say("Julia is over there", debug=1, muck_it_up=True)
    sys.stdout.flush()
    time.sleep(10)
    say("I see the quad and am pointing to the quad.", debug=0)
    say("I see the quad and am pointing to the quad.", debug=1, muck_it_up=True)

#    Say("I'm having trouble with my vision and I'm not sure that I see Julia.", debug=2)
#    say("I'm having trouble with my vision and I'm not sure that I see Julia.", debug=2, muck_it_up=True)
#   say("A United States airstrike appears to have badly damaged the hospital run by Doctors Without Borders in the Afghan city of Kunduz early Saturday, killing at least nine hospital staff members and wounding dozens, including patients and staff.", debug=2)
#   say("A United States airstrike appears to have badly damaged the hospital run by Doctors Without Borders in the Afghan city of Kunduz early Saturday, killing at least nine hospital staff members and wounding dozens, including patients and staff.", debug=2, muck_it_up=True)

    
#asoa_test()

# try:
#     say("Hello human.  I am very pleased to meet you.")
# except MuteError:
#     print("mute")
