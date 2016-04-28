import scipy.io.wavfile
import numpy as np
import pyaudio
import wave
import time
import sys
import tempfile
import subprocess

PATH_TO_TEXT2WAVE="/usr/bin/text2wave"
# text_to_synth = ""
# template_file = ""
# template_wave = []
# template_rate = 0
# template_length = 0
# template_idx = 0
# template_framesize = 0

# signal_wave = []




class asoa_io:
    def read_callback(self, in_data, frame_count, time_info, status):
        if (not self.read_called):
            #print "In read at time " + repr(time.clock())
            self.read_called = True;
            self.first_read = time.clock()
            if (self.write_called):
                #print "Secondary time differential is " + repr(self.first_read - self.first_write)
                self.skip_frames = int(self.template_rate * (self.first_read - self.first_write))
        num_frames = len(in_data) / self.frame_size
        assert(len(in_data) % self.frame_size == 0)
        for i in range(num_frames):
            my_data = np.fromstring(in_data[i*self.frame_size : (i+1)*self.frame_size], dtype='int16')
            self.signal += [my_data]  # This has the incoming signal as a list of frames.
        return (in_data, pyaudio.paContinue)

    def write_callback(self,in_data, frame_count, time_info, status):
        if (not self.write_called):
            #print "In write at time " + repr(time.clock())
            self.write_called = True;
            self.first_write = time.clock()
            if (self.read_called):
                #print "Secondary time differential is " + repr(self.first_write - self.first_read)
                self.skip_frames = int(self.template_rate * (self.first_read - self.first_write))
        data = self.wf.readframes(frame_count)
        return (data, pyaudio.paContinue)


    """ Synthesize the speech and do any preprocessing.
    Note that we want to use the kal_diphone voice for synthesis.
    """
    def __init__(self, text_string, frame_size=128, muck_it_up=False):
        temp_fd, template_file = tempfile.mkstemp()
        string_file = tempfile.NamedTemporaryFile()

        self.write_called = False
        self.read_called = False
        self.skip_frames = -1
        self.frame_size = frame_size
    
        string_file.write(text_string)
        string_file.flush()
        

        if (subprocess.call([PATH_TO_TEXT2WAVE, string_file.name, "-o", template_file]) > 0):
            print "Error running text2wave"

        string_file.close()

        self.wf = wave.open(template_file, 'rb')
        self.template_rate = self.wf.getframerate()
        tw = self.wf.readframes(self.wf.getnframes())
        self.template_wave = np.fromstring(tw, dtype='int16')

        
        self.pa = pyaudio.PyAudio()
        self.muck_up = muck_it_up

    def generate_speech(self):
        self.wf.rewind()
        self.input_stream = self.pa.open(format=pyaudio.get_format_from_width(self.wf.getsampwidth()),
                                    channels=1, rate = self.template_rate, input=True,
                                    stream_callback = self.read_callback)
        if (self.muck_up):
            self.wf.close()
            self.wf = wave.open('/home/justin/auditory-soa/sample-completely-different.wav', 'rb')


        self.output_stream = self.pa.open(format=pyaudio.get_format_from_width(self.wf.getsampwidth()),
                                channels=1, rate = self.template_rate,
                                output=True, stream_callback =
                                self.write_callback)
            
        self.template_idx = 0
        self.signal = []

    def still_speaking(self):
        return self.output_stream.is_active()

    def stop_speech(self):
        self.output_stream.stop_stream()
        self.output_stream.close()
        self.wf.close()
        self.pa.terminate()





# testing
# A = asoa_io("hello human.  i'm very pleased to meet you.  really i am!")
# print "Done init"
# A.start_speech()    
# A.stop()

# write_data = np.asarray(A.signal).tobytes()
# outw = wave.open('/tmp/out.wav', 'wb')
# outw.setnchannels(1)
# outw.setsampwidth(2)
# outw.setframerate(A.template_rate)
# outw.writeframes(write_data)
# outw.close()

# new testing.
#C = asoa_io("Taking a rostrum never before occupied by the bishop of Rome, the pontiff issued a vigorous call to action on issues largely favored by liberals, including a powerful defense of immigration, an endorsement of environmental legislation, a blistering condemnation of the arms trade and a plea to abolish the death penalty.  Francis became the first pope ever to address a joint meeting of Congress, a milestone in the journey of the Catholic Church in the United States, and it generated enormous interest. Lawmakers, aides and invited guests jammed the historic chamber of the House of Representatives, while tens of thousands more people were invited to watch on jumbo screens on the West Lawn of the Capitol.His high-profile address came at a time of deep partisan and ideological ferment over divisive policy questions that have so fractured the Congress that it is just days away from a government shutdown. Both sides were looking to his words for moral support for their arguments from a figure deliberately resistant to clean political definitions.  ")

# C.generate_speech()
# tidx = 0
# template = C.template_wave
# while (C.still_speaking()):
#     for frame in C.signal:
#         tframe = template[128*tidx: 128*(tidx + 1) - 1]
#         tidx += 1
#         print "Frame head is " + repr(frame[:10]) + " / length = " + repr(len(frame))
#         print "Template head is " + repr(tframe[:10])  + " / length = " + repr(len(tframe))
# C.stop_speech
        
