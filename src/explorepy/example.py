from explorepy.explore import Explore
import os.path
import csv

myexplore = Explore()
myexplore.connect()
myexplore.passParameters()
#myexplore.acquire()
#myexplore.record_data(file_name="test9")

"""
bin_file = "/home/lilac/Documents/DATA101.BIN"

with open(bin_file, "rb") as f_bin:
    data = f_bin.read(100)
    print(data)
"""
