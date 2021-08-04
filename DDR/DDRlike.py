import tkinter as tk
import numpy as np
import time
import pandas as pd
import json


class DdrFile:
    # holds the notes in sequence with uldr = 1234, and indexed with subdivision number
    # has methods used to set/create a ddrfile and can be saved.
    def __init__(self, transcript, bpm=100, divisions_per_beat=4, beats_before_note=2):
        if isinstance(transcript, pd.DataFrame):
            self.transcript = transcript.dropna(how='all').fillna(0)
            self.transcript.index += divisions_per_beat * beats_before_note * 2
        self.bpm = bpm
        self.divisions = divisions_per_beat
        self.beatsBeforeNote = beats_before_note

    def get_note_lifetime_div(self):
        return self.divisions * self.beatsBeforeNote

    def get_note_lifetime(self):
        return round(self.beatsBeforeNote * 1000 * 60 / self.bpm)

    def get_division_length(self):
        return round(1000 * 60 / self.bpm / self.divisions)

    def get_transcript(self):
        return self.transcript

    def set_bpm(self, bpm):
        self.bpm = bpm

    def set_beats_before(self, bbn):
        self.beatsBeforeNote = bbn


class Reader:
    # holds info taken from the DDR file
    def __init__(self, ddr_file):
        self.currentTime = 0
        self.futureTime = 1
        self.currentLine = 0
        self.transcript = ddr_file.get_transcript()
        self.final_division = self.transcript.index[-1]
        self.noteTtl = ddr_file.get_note_lifetime()
        self.timeStepLag = ddr_file.get_note_lifetime_div()
        self.divisionLength = ddr_file.get_division_length()

    def get_next(self):
        if self.futureTime == self.final_division:
            # exit condition
            return self.noteTtl * 2, False
        # extract all the beats with the next lowest division number,
        self.futureTime = self.transcript.index[self.currentLine]
        nextNoteHit = (self.futureTime - self.currentTime) * self.divisionLength
        nextNoteDraw = nextNoteHit - self.noteTtl
        slc = self.transcript.iloc[self.currentLine]
        codeDict = dict()
        for i in slc[slc == 2].index:
            temp = self.transcript[i].loc[self.futureTime:]
            releaseDivision = temp[temp == 3].index[0]
            releaseTimer = (releaseDivision - self.futureTime) * self.divisionLength
            codeDict[i] = releaseTimer
        for i in slc[slc == 1].index:
            codeDict[i] = False
        if codeDict:
            self.currentTime = self.futureTime - self.timeStepLag
            self.currentLine += 1
        else:
            self.currentLine += 1
            nextNoteDraw, codeDict = self.get_next()
        return nextNoteDraw, codeDict

    def get_ttl(self):
        return self.noteTtl


class DDR:
    # holds a reader and a window and a list of currently drawn notes
    # has an update method that updates graphical elements, iterating through the Notes
    # has a queery method that asks for the next notes from the reader
    # (potentially multiple at same time) as well as the time until they should be made
    # then calls after(given time, root, draw()), then calls itself queery()
    # has a draw method that makes a new Note and adds it to the list of drawn notes
    noteDest = 0.15
    tolerance = 0.02

    def __init__(self, file, framerate=60):
        self.framerate = framerate
        # framelength in milliseconds
        self.framelength = round(1000 / framerate)
        self.reader = Reader(file)
        self.noteLifetime = self.reader.get_ttl()
        self.currentNotes = list()
        self.currentlyHeldNotes = list()
        self.channelOpen = {0: True, 1: True, 2: True, 3: True}
        self.root = tk.Tk()
        self.root.bind('<FocusIn>', self.squareWindow)
        self.root.bind('<Left>', self.handlePress)
        self.root.bind('<Down>', self.handlePress)
        self.root.bind('<Up>', self.handlePress)
        self.root.bind('<Right>', self.handlePress)
        self.root.bind('<KeyRelease>', self.handleRelease)
        tk.Frame(master=self.root, bg='#7daad6').place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Frame(master=self.root, bg='black').place(relx=0, relwidth=1,
                                                     rely=self.noteDest - self.tolerance / 2, relheight=self.tolerance)
        self.slider = Slider(self.root)
        self.dancer = DancingFella(self.root)
        self.scorer = Scorer(self.root)
        self.nextDrawTimer, self.nextNotes = self.reader.get_next()
        self.time = time.time()
        self.theoreticalTime = 0
        self.root.after(self.nextDrawTimer, self.updateLoop)
        self.root.mainloop()

    def updateLoop(self):
        self.theoreticalTime += self.nextDrawTimer
        if not isinstance(self.nextNotes, dict):
            self.dancer.end()
            return
        self.draw(self.nextNotes)
        # overshoot is how far behind the drawing is from the original recording.
        self.nextDrawTimer, self.nextNotes = self.reader.get_next()
        overshoot = int(1000 * (time.time() - self.time) - self.theoreticalTime)
        # after an amount of time
        self.root.after(self.nextDrawTimer - overshoot, self.updateLoop)

    def draw(self, codeDict):
        # each time draw, check for notes to delete
        for note in self.currentNotes:
            if note.off_screen():
                self.currentNotes.remove(note)
                # WORK OUT IF TO DEDUCT POINTS
        for code, timer in codeDict.items():
            if not timer:
                self.currentNotes.append(Note(self.root, code, self.noteLifetime, self.noteDest,
                                              self.tolerance, self.framelength))
            else:
                self.currentNotes.append(HeldNote(self.root, code, self.noteLifetime, self.noteDest,
                                                  self.tolerance, self.framelength,
                                                  timer, self.scorer))

    def handlePress(self, event):
        code = {37: 0, 38: 2, 39: 3, 40: 1}[event.keycode]
        if self.channelOpen[code]:
            self.channelOpen[code] = False
            goodEntry = False
            for note in self.currentNotes:
                if note.at_end(code):
                    # remove note as no longer can it be clicked, it will delete itself when off screen
                    self.currentNotes.remove(note)
                    if isinstance(note, HeldNote):
                        # add to different list which is checked when button is released
                        self.currentlyHeldNotes.append(note)
                    goodEntry = True
                    # break loop because the nature of the transcript does not all for multiple notes hit with one press
                    break
            if goodEntry:
                self.scorer.points(100)
                self.slider.shift(-0.01)
                self.dancer.swap()
            else:
                self.slider.shift(0.01)
        else:
            return

    def handleRelease(self, event):
        # triggered by any release, check for appropriate keys
        # event.keycode = 37:40 for left, up, right, down
        if (event.keycode < 37) | (event.keycode > 40):
            return
        code = {37: 0, 38: 2, 39: 3, 40: 1}[event.keycode]
        if not self.channelOpen[code]:
            self.channelOpen[code] = True
            goodRelease = False
            for note in self.currentlyHeldNotes:
                if not note.off_screen():
                    if note.matches(code):
                        goodRelease = note.setButtonRelease()
                        self.currentlyHeldNotes.remove(note)
                        break
                else:
                    self.currentlyHeldNotes.remove(note)
            if goodRelease:
                self.slider.shift(-0.01)
                # Do not deduct points for bad release
                # Do not dance for good release
        else:
            return

    @staticmethod
    def squareWindow(event):
        event.widget.geometry('800x800')


class Slider:
    def __init__(self, root):
        self.sliderPos = 0.5
        self.frame = tk.Frame(master=root)
        self.frame.place(relx=0.27, relwidth=0.46, rely=0.93, relheight=0.04)
        self.subslider1 = tk.Frame(master=self.frame, bg='red')
        self.subslider1.place(relx=0, rely=0, relheight=1, relwidth=self.sliderPos)
        self.subslider2 = tk.Frame(master=self.frame, bg='green')
        self.subslider2.place(relx=self.sliderPos, rely=0, relheight=1, relwidth=1 - self.sliderPos)

    def shift(self, amount):
        self.sliderPos = max(min(self.sliderPos + amount, 1), 0)
        self.subslider1.place_configure(relwidth=self.sliderPos)
        self.subslider2.place_configure(relx=self.sliderPos, relwidth=1 - self.sliderPos)


class DancingFella:
    texts = ['ლ(▀̿̿Ĺ̯̿̿▀̿ლ)', '(☞⌐▀͡ ͜ʖ͡▀ )☞']

    def __init__(self, root):
        self.state = 0
        self.lbl = tk.Label(master=root, text=self.texts[0], bg='#7daad6', fg='orange', font=('', 40))
        self.lbl.place(relx=0, relwidth=1, rely=0.05, relheight=0.06)

    def swap(self):
        self.state = (self.state + 1) % 2
        self.lbl['text'] = self.texts[self.state]

    def end(self):
        self.lbl['text'] = 'ヽ༼ ຈل͜ຈ༼ ▀̿̿Ĺ̯̿̿▀̿ ̿༽Ɵ͆ل͜Ɵ͆ ༽ﾉ'


class Scorer:
    def __init__(self, root):
        self.score = 0
        frm = tk.Frame(master=root, bg='#7daad6')
        frm.place(relx=0.77, relwidth=0.33, rely=0.93, relheight=0.04)
        self.lbl = tk.Label(master=frm, text='0', bg='#7daad6', fg='white', font=("", 15))
        self.lbl.grid(column=0, row=0, sticky='w')

    def points(self, points=0):
        self.score += points
        self.lbl['text'] = str(self.score)


class Note:
    # holds a graphical note that it makes
    # holds a time-to-live giving to it by ddr.draw
    # has a setPost method that takes a framelength and takes it off the time to live, moving the position of the
    # widget proporitionally closer to the destination. Returns whether or not DDR should remove this note from the
    # list, DDR then uses notelist.pop(this).destroy(), triggering the notes destory method.
    # contains a destroy method that runs an animation and deletes the graphical element
    animationLength = 200
    noteBaseSize = 0.1
    labelCode = {0: '<', 1: 'v', 2: '^', 3: '>'}
    colourCode = {0: 'purple', 1: 'blue', 2: 'green', 3: 'red'}

    def __init__(self, root, direction, lt, destination, tolerance, framelength):
        # convert to millisecond on use, not here.
        self.realtime = time.time()
        self.lifetime = lt
        # set here to vestigial values to avoid error in at_end due to move not having been called on the object yet
        # to set ttl to a practical value.
        self.ttl = lt
        self.framelength = framelength
        self.noteSize = self.noteBaseSize
        self.animationState = 0
        self.dest = destination - self.noteSize / 2
        self.ycoord = 0.9 - self.noteSize
        self.speed = (self.ycoord - self.dest) / self.lifetime
        self.timetolerance = (self.noteBaseSize + tolerance / 2) / self.speed
        self.widget = tk.Frame(master=root, bg=self.colourCode[direction])
        self.direction = direction
        tk.Label(master=self.widget, bg=self.colourCode[direction], fg='black',
                 text=self.labelCode[direction], font=('', 26)).pack(fill=tk.BOTH, expand=True)
        placeCode = {i: 0.1 + (0.8 - self.noteBaseSize) * i / 3 for i in range(4)}
        self.xcoord = placeCode[direction] + self.noteSize / 2
        self.widget.place(relx=placeCode[direction], relwidth=self.noteSize, rely=self.ycoord, relheight=self.noteSize)
        self.widget.after(self.framelength, self.move)

    def move(self):
        # after hit, animationState is set to 1:
        if self.animationState == 1:
            self.widget.after(self.framelength, self.onHitAnimation)
            # abort loop
            return
        self.ttl = self.lifetime - 1000 * (time.time() - self.realtime)
        self.ycoord = self.dest + self.ttl * self.speed
        self.widget.place_configure(rely=self.ycoord)
        if self.ycoord < -self.noteSize:
            # return a signal to stop trying to update
            self.widget.destroy()
            # abort loop
            return
        # only reach next update if widget exists
        self.widget.after(self.framelength, self.move)

    def at_end(self, code):
        if self.direction == code:
            if abs(self.ttl) < self.timetolerance / 2:
                self.animationState = 1
                # realtime now becomes time of animation start
                self.realtime = time.time()
                return True
            else:
                return False
        else:
            return False

    def off_screen(self):
        return self.ycoord < -self.noteSize

    def onHitAnimation(self):
        self.animationTime = self.animationLength - 1000 * (time.time() - self.realtime)
        if self.animationTime < 0:
            self.widget.destroy()
            return
        self.noteSize = (self.noteBaseSize +
                         0.3 * (self.noteBaseSize) * (self.animationLength - self.animationTime) / self.animationLength)
        self.widget.place_configure(relwidth=self.noteSize, relheight=self.noteSize,
                                    relx=self.xcoord - self.noteSize / 2)
        self.widget.after(self.framelength, self.onHitAnimation)


class HeldNote(Note):
    rectangleThickness = 0.01

    def __init__(self, root, direction, lt, destination, tolerance, framelength, rectangleTtl, scorer):
        Note.__init__(self, root, direction, lt, destination, tolerance, framelength)
        self.rectangledest = destination
        # rrt set on animation start
        self.rectangleRealTime = 0
        self.scorer = scorer
        # rectanglTtl used only for cutting off held note
        self.rectangleLT = rectangleTtl
        self.rectangleTtl = rectangleTtl
        self.rectangleTimeTol = Note.noteBaseSize / self.speed
        self.rectangleLen = rectangleTtl * self.speed
        self.rectangle = tk.Frame(master=root, bg='yellow')
        self.rectangleTop = 1 - Note.noteBaseSize / 2,
        self.rectangle.place(relx=self.xcoord - self.rectangleThickness / 2,
                             rely=self.rectangleTop,
                             relwidth=self.rectangleThickness,
                             relheight=self.rectangleLen)
        self.timeSinceAnimation2 = 0
        self.ycoordOnRelease = 0

    def move(self):
        if self.animationState == 1:
            self.widget.after(self.framelength, self.onHitAnimation)
            return
        self.ttl = self.lifetime - 1000 * (time.time() - self.realtime)
        self.rectangleTop = self.rectangledest + self.speed * self.ttl
        self.rectangle.place_configure(rely=self.rectangleTop)
        self.ycoord = self.dest + self.ttl * self.speed
        self.widget.place_configure(rely=self.ycoord)
        # wait till both widgets totally off screen before destroying and ceasing updates.
        if self.rectangleTop < -self.rectangleLen:
            self.widget.destroy()
            self.rectangle.destroy()
            return
        self.widget.after(self.framelength, self.move)

    def matches(self, code):
        return self.direction == code

    def setButtonRelease(self):
        self.ycoordOnRelease = self.ycoord
        self.animationState = 2
        self.animation2RealTime = time.time()
        self.widget.after(self.framelength, self.on_release_animation)
        if abs(self.rectangleTtl) < self.rectangleTimeTol:
            # appropriately timed release gives more points
            return True

    def at_end(self, code):
        if self.direction == code:
            if abs(self.ttl) < self.timetolerance / 2:
                self.animationState = 1
                self.rectangleRealTime = time.time()
                return True
            else:
                return False
        else:
            return False

    def is_state_one(self):
        # allows DDR to check if held note is available to be pressed or if it has already been pressed
        return self.animationState == 0

    def off_screen(self):
        return self.rectangleTop < -self.rectangleLen - self.noteSize

    def onHitAnimation(self):
        # so long as button is held and rectangleTTL>0 hold the button
        # where it is and grow and shrink it sinusoidally
        # the rectangle continues to drop
        # rectangleTtl effectively replaces Note.animationTime
        self.scorer.points(round(0.2 * self.framelength))
        if self.animationState == 1:
            self.rectangleTtl = self.rectangleLT - 1000 * (time.time() - self.rectangleRealTime)
            self.ttl = self.lifetime - 1000 * (time.time() - self.realtime)
            if self.rectangleTtl > -self.noteSize / self.speed / 2:
                self.noteSize = Note.noteBaseSize * (1 + 0.2 * np.sin(self.rectangleTtl * 2 * np.pi / 1000))
                self.widget.place_configure(relwidth=self.noteSize, relheight=self.noteSize,
                                            relx=self.xcoord - self.noteSize / 2)
                self.rectangleTop = self.rectangledest + self.speed * self.ttl
                self.rectangle.place_configure(rely=self.rectangleTop)
                self.widget.after(self.framelength, self.onHitAnimation)
                return
            else:
                # phase two of animation starting because rectangle ran out
                # after triggering, proceed to first phase 2 animation
                self.setButtonRelease()

    def on_release_animation(self):
        # in phase 2 of animation, either because rectangle ran out or click was released
        self.ttl = self.lifetime - 1000 * (time.time() - self.realtime)
        self.rectangleTop = self.rectangledest + self.speed * self.ttl
        self.timeSinceAnimation2 = - 1000 * (time.time() - self.animation2RealTime)
        self.ycoord = self.ycoordOnRelease + self.speed * self.timeSinceAnimation2
        self.rectangle.place_configure(rely=self.rectangleTop)
        self.widget.place_configure(rely=self.ycoord)
        if self.rectangleTop < -self.rectangleLen - self.noteSize:
            self.widget.destroy()
            self.rectangle.destroy()
            # abort loop
            return
        self.widget.after(self.framelength, self.on_release_animation)

df = pd.DataFrame(json.load(open("Song.txt")))
df.index = df.index.astype(int)
df.columns = df.columns.astype(int)
play = DdrFile(df, bpm=100, divisions_per_beat=4)
DDR(play, framerate=60)