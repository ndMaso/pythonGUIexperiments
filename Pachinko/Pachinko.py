import tkinter as tk
import random as r
import numpy as np
from enum import Enum


class Physics(Enum):
    FREEFALL = 1
    FRICTION = 2


class Ball:
    ball_size = 0.01
    mu = 1.15e-3

    def __init__(self, topcoord, accel, window, physics):
        self.accel = accel
        self.widget = tk.Frame(master=window, bg='orange')
        self.vx = r.normalvariate(0, 0.00001)
        self.x = topcoord - self.ball_size / 2
        self.y = 0
        self.vy = 0
        self.widget.place(relx=self.x, rely=self.y, relheight=self.ball_size, relwidth=self.ball_size)
        physicsSwitch = {Physics.FREEFALL: self.update_freefall, Physics.FRICTION: self.update_friction}
        self.physics = physicsSwitch[physics]

    def step_forward(self, timestep):
        self.physics(timestep)

        if self.y > 1:
            position = self.x
            payout = round((position - 0.5) ** 4 * 40000)
            self.widget.destroy()
            return [payout, self.x]
        if abs(self.x - 0.5 + self.ball_size / 2) > 0.40 - self.ball_size / 2:
            self.vx *= - np.sign(self.vx) * np.sign(self.x - 0.5 + self.ball_size / 2)

        self.widget.place_configure(relx=self.x, rely=self.y)
        return False

    def update_friction(self, timestep):
        self.y = (self.accel / self.mu * timestep - (self.vy - self.accel / self.mu) / self.mu * np.exp(
            -self.mu * timestep) +
                  (+self.vy - self.accel / self.mu) / self.mu + self.y)
        self.x = -self.vx / self.mu * np.exp(-self.mu * timestep) + self.x + self.vx / self.mu

        self.vy = self.accel / self.mu + (self.vy - self.accel / self.mu) * np.exp(-self.mu * timestep)
        self.vx = self.vx * np.exp(-self.mu * timestep)

    def update_freefall(self, timestep):
        self.x += self.vx * timestep
        self.y += self.vy * timestep + self.accel * 0.5 * timestep ** 2

        self.vy = self.vy + self.accel * timestep

    def check_collisions(self, pin_corners, pin_size):
        ball_corner = [self.x, self.y]
        ball_v = [self.vx, self.vy]
        bigboxlen = pin_size + self.ball_size
        bigboxcenters = pin_corners - [self.ball_size, self.ball_size] + bigboxlen / 2
        # centers of pins which intersect with ball
        logind = np.all(abs(ball_corner - bigboxcenters) < bigboxlen / 2, axis=1)
        if not any(logind):
            return
        subset_pin_centers = (pin_corners[logind] + [pin_size / 2, pin_size / 2])
        center_vectors = ball_corner + np.array([self.ball_size / 2, self.ball_size / 2]) - subset_pin_centers
        # reflect the component of the balls velocity that lies along ball to pin, but only
        # if it is actually towards the pin
        # dv = sum_over_pins{2 * ^a_[p->b] * (v_b . ^a_[p->b] if <0 else 0)}
        scales = np.sum(ball_v * center_vectors, axis=1, keepdims=True) / np.sum(center_vectors ** 2, axis=1,
                                                                                 keepdims=True)
        scales = scales * (scales < 0)
        dv = -np.mean(1.5 * center_vectors * scales, axis=0)
        self.vx, self.vy = self.vx + dv[0], self.vy + dv[1]


class Dropper:
    def __init__(self, root):
        self.widget = tk.Label(master=root, text='V', fg='orange', bg='blue', font=('', 20, 'bold'))
        self.widget.place(relx=0.45, rely=0, relwidth=0.1, relheight=0.03)
        self.time = 0.0
        self.position = 0.5

    def update(self, framelength):
        self.time = (self.time + framelength / 500) % (2 * np.pi)
        self.position = 0.45 + 0.05 * np.sin(self.time)
        self.widget.place_configure(relx=self.position)

    def get_pos(self):
        return self.position


class Pachinko:
    pin_size = 0.008

    def __init__(self, framerate=60, acceleration=5e-7, physics=Physics.FREEFALL):
        self.framelength = round(1000 / framerate)
        self.allBalls = []
        self.root = tk.Tk()
        self.root.title('Pachinko')
        self.pins = []
        self.physics = physics
        self.counter = tk.Label(master=self.root, text=str(100), foreground="#BA2121",
                                background="#F7F7F7", font=('Times New Roman', 20))
        self.counter.place(relx=0.92, rely=0, relwidth=0.08, relheight=0.05)
        border1 = tk.Frame(master=self.root, bg='black')
        border2 = tk.Frame(master=self.root, bg='black')
        borderwidth = 0.02
        border1.place(relx=0.1 - borderwidth, rely=0, relwidth=borderwidth, relheight=1)
        border2.place(relx=0.9, rely=0, relwidth=borderwidth, relheight=1)
        tk.Frame(master=self.root, bg='blue').place(relx=0.1, rely=0, relwidth=0.8, relheight=1)
        self.dropper = Dropper(self.root)
        self.root.geometry('800x800')
        self.accel = acceleration
        self.root.bind('<ButtonRelease-1>', self.handle_click)
        self.root.bind('<FocusIn>', Pachinko.square_window)
        self.root.bind('n', self.new_board)
        self.new_board()
        self.update_loop()
        self.root.mainloop()

    def new_board(self, event=None):
        for pin in self.pins:
            pin.destroy()
        xcoords = np.array([r.random() * 0.78 - 0.78 / 2 for i in range(200)])
        ycoords = np.array([r.random() * 0.91 + 0.05 for i in range(200)])
        xcoords = xcoords * ycoords ** 0.33 + 0.1 + 0.78 / 2
        ydiffs = (np.diff(np.sort(ycoords)))
        yloc = ydiffs < self.pin_size
        argind = np.argsort(ycoords)
        orderedx = xcoords[argind]
        xdiffs = np.diff(orderedx)
        xloc = [False] * len(orderedx)
        accruedDistances = np.array([0.0] * len(orderedx))
        for i in range(len(xloc) - 1):
            subsetLocs = np.copy(yloc[:i + 1])
            ind = np.array(subsetLocs).tostring().rfind(b'\x00')
            if ind == -1: ind = 0
            subsetLocs[:ind] = [False] * ind
            accruedDistances[:i + 1] = accruedDistances[:i + 1] - xdiffs[i]
            if np.any(abs(accruedDistances[:i + 1][subsetLocs]) < self.pin_size):
                xloc[i + 1] = True
        yloc = np.insert(yloc, 0, False)
        # xloc = np.insert(abs(np.diff(xloc)<self.pin_size), 0, False)
        ycoords = ycoords[argind][~(yloc & xloc)]
        xcoords = xcoords[argind][~(xloc & yloc)]
        self.pin_corners = np.transpose(np.concatenate(([xcoords], [ycoords])))
        for i in range(len(ycoords)):
            self.pins.append(tk.Frame(master=self.root, bg='red'))
            self.pins[-1].place(relx=xcoords[i], rely=ycoords[i],
                                relwidth=self.pin_size, relheight=self.pin_size)

    def handle_click(self, event):
        self.counter['text'] = str(int(int(self.counter['text']) - 100))
        relxClick = self.dropper.get_pos() + 0.05
        # windowWidth=event.widget.winfo_toplevel().winfo_width()
        # windowHeight=event.widget.winfo_toplevel().winfo_height()
        # pos=event.x
        # if event.widget is not self.root:
        #    pos += event.widget.winfo_x()
        # relxClick=pos/windowWidth
        self.allBalls.append(Ball(relxClick, self.accel, self.root, self.physics))

    @staticmethod
    def square_window(event):
        event.widget.geometry('800x800')

    def update_loop(self):
        self.dropper.update(self.framelength)
        for ball in self.allBalls:
            payout = ball.step_forward(self.framelength)
            if payout:
                lbl = tk.Label(master=self.root, text=str(payout[0]))
                lbl.place(relx=payout[1] - 0.02, rely=1 - 0.04, relheight=0.04, relwidth=0.04)
                lbl.after(1000, lbl.destroy)
                # Signal received from ball that it is out of frame and the widget has
                # been destroyed, now must remove the ball object from the game.
                self.allBalls.remove(ball)
                self.counter['text'] = str(int(int(self.counter['text']) + payout[0]))
            ball.check_collisions(self.pin_corners, self.pin_size)
        self.root.after(self.framelength, self.update_loop)


game = Pachinko(acceleration=6e-7, physics=Physics.FRICTION)
