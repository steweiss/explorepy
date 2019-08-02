from explorepy.explore import Explore
import os.path
import csv
from explorepy import tools
filename = "test13"
filename2 = "test13_calibre_coef.csv"
filename3 = "/home/lilac/Desktop/301/DATA056.BIN"
myexplore = Explore()
myexplore.connect(device_name="Explore_143B")
#myexplore.pass_parameters()
#myexplore.acquire()
#myexplore.record_data(filename, do_overwrite=False)
#myexplore.push2lsl(n_chan=2)
#myexplore.calibrate(file_name= filename)
myexplore.visualize(n_chan = 8, notch_freq=50, bp_freq=(1,30), calibre_file=filename2)  # Give number of channels (4 or 8)
#tools.bin2csv(filename3)
