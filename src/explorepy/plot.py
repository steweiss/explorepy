import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
headers = ['TimeStamp', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7', 'ch8']
df = pd.read_csv('/home/lilac/ARMTools/explorepy/src/explorepy/test3_eeg.csv', names=headers)
print(df)

x = df['TimeStamp']
y1 = df['ch1']
y2 = df['ch2']
y3 = df['ch3']
y4 = df['ch4']
y5 = df['ch5']
y6 = df['ch6']
y7 = df['ch7']
y8 = df['ch8']
# plot
plt.figure(1)
plt.plot(x[1000:1500], y4[1000:1500])
plt.show()


"""""

# plot
plt.plot(x,y2)
plt.show()



# plot
plt.plot(x,y3)
plt.show()



# plot
plt.plot(x,y4)
plt.show()



# plot
plt.plot(x,y5)
plt.show()



# plot
plt.plot(x,y6)
plt.show()


# plot
plt.plot(x,y7)
plt.show()


# plot
plt.plot(x,y8)
plt.show()
"""""
