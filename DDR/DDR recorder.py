import tkinter as tk
import pandas as pd
import time
import json
import numpy as np


class Recorder:
    def __init__(self, bpm=100, divisionsPerBeat=4):
        self.bpm = bpm
        self.dpb = divisionsPerBeat
        self.linetime = 60 * 1000 / self.bpm / self.dpb
        self.looptime = round(self.linetime)
        self.index = -1
        self.channelState = {0: True, 1: True, 2: True, 3: True}
        self.pressedFrames = {0: 0, 1: 0, 2: 0, 3: 0}
        self.root = tk.Tk()
        self.root.bind('<Left>', self.handlePress)
        self.root.bind('<Down>', self.handlePress)
        self.root.bind('<Up>', self.handlePress)
        self.root.bind('<Right>', self.handlePress)
        self.root.bind('<KeyRelease>', self.handleRelease)
        self.root.bind('<Return>', self.exit)
        self.dict = {0: np.array([0]), 1: np.array([0]), 2: np.array([0]), 3: np.array([0])}
        self.df = None
        self.startTime = time.time()
        self.theoreticalTime = 0
        self.root.after(self.looptime, self.newline)
        self.root.mainloop()

    def newline(self):
        self.theoreticalTime += self.linetime
        self.index += 1
        lines = self.index - len(self.dict[0])
        for i in range(4):
            self.dict[i] = np.append(self.dict[i], [0] * lines)
        overshoot = 1000 * (time.time() - self.startTime) - self.theoreticalTime
        self.root.after(int(self.looptime - overshoot), self.newline)

    def handlePress(self, event):
        if (event.keycode < 37) | (event.keycode > 40):
            return
        code = {37: 0, 38: 2, 39: 3, 40: 1}[event.keycode]
        if self.dict[code][-1] == 3:
            return
        if self.channelState[code]:
            self.channelState[code] = False
            self.pressedFrames[code] = self.index
            self.dict[code][-1] = 1

    def handleRelease(self, event):
        if (event.keycode < 37) | (event.keycode > 40):
            return
        code = {37: 0, 38: 2, 39: 3, 40: 1}[event.keycode]
        self.channelState[code] = True
        if self.index == self.pressedFrames[code]:
            pass  # Leave as 1
        else:
            self.dict[code][-1] = 3
            self.dict[code][self.pressedFrames[code] - 1] = 2

    def exit(self, event):
        self.root.destroy()
        self.df = pd.DataFrame(self.dict)

    def process_save(self, filename='Song.txt'):
        df = self.df
        temp = (df == 0).apply(np.all, axis=1)
        # Drop initial rows with all zeros i.e. no notes.
        df = df.iloc[temp[temp == False].index[0]:]
        # Reset index so first is zero
        df.reset_index(drop=True, inplace=True)
        temp = (df == 0).apply(np.all, axis=1)
        # Drop all rows with no notes, but leave the index as it.
        df = df.loc[temp == False]
        with open(filename, 'w') as json_file:
            json.dump(df.to_dict(), json_file)


a = Recorder(bpm=100, divisionsPerBeat=4)
a.process_save()
