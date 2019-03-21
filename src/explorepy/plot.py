import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
headers = ['TimeStamp', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6', 'ch7', 'ch8']
df = pd.read_csv('/home/lilac/ARMTools/explorepy/src/explorepy/test9_eeg.csv', names=headers)
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
plt.subplot(421)
plt.plot(x[2000:2500], y1[2000:2500])
plt.subplot(422)
plt.plot(x[2000:2500], y2[2000:2500])
plt.subplot(423)
plt.plot(x[2000:2500], y3[2000:2500])
plt.subplot(424)
plt.plot(x[2000:2500], y4[2000:2500])
plt.subplot(425)
plt.plot(x[2000:2500], y5[2000:2500])
plt.subplot(426)
plt.plot(x[2000:2500], y6[2000:2500])
plt.subplot(427)
plt.plot(x[2000:2500], y7[2000:2500])
plt.subplot(428)
plt.plot(x[2000:2500], y8[2000:2500])
plt.show()


