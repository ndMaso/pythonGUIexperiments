import math
import numpy as np
import tkinter as tk
import turtle


def get_lagrange(x, y):
    # Returns the coefficients of a degree len(x)-1 polynomial that interpolates the given points
    def take_sums(x, at_a_time):
        if at_a_time == 0:
            return 1
        else:
            return sum([x[ind] * take_sums(x[ind + 1:], at_a_time - 1) for ind in range(len(x) - at_a_time + 1)])

    # force np arrays
    x = np.array(x)
    y = np.array(y)
    n = len(x)
    order = n - 1
    coeffs = np.array([0] * n).astype(np.float64)
    # for each polynomial
    for i in range(n):
        minusx = np.delete(np.copy(x), i) * -1
        # 0th order first
        sums = np.array([1] * n)
        for m in range(order):
            # calculate sums taken m+1 at a time
            sums[-2 - m] = take_sums(minusx, m + 1)
        coeffs += y[i] * sums / np.prod([x[i] + minusx[j] for j in range(order)])
    return coeffs


class Poly:
    def __init__(self, coeffs):
        # coeffs with 0th order first
        self.coeffs = coeffs
        self.degree = len(coeffs) - 1

    def sample(self, t):
        # t should be a np array
        return sum([self.coeffs[n] * t ** n for n in np.arange(self.degree + 1)])

    def diff(self):
        return Poly((self.coeffs * np.arange(self.degree + 1))[1:])

    def get_coeffs(self):
        return self.coeffs


class StraightLine:
    def __init__(self, x1, x2, y1, y2):
        # points is a numpy array shape=(2,n), first row is x's
        self.xs = np.array([x1, x2])
        self.ys = np.arary([y1, y2])

        self.time = 1
        self.xcoeffs = get_lagrange([0, 1], self.xs)
        self.ycoeffs = get_lagrange([0, 1], self.ys)
        self.zcoeffs = self.xcoeffs + 1j * self.ycoeffs
        # quartics parameterizing in t
        self.xP4 = Poly(self.xcoeffs)
        self.yP4 = Poly(self.ycoeffs)
        self.zP4 = Poly(self.zcoeffs)
        # analytic derivative functions
        self.dxP3 = self.xP4.diff()
        self.dyP3 = self.yP4.diff()
        self.dzP3 = self.zP4.diff()

        # self.tSamplesPoints = np.array([[self.xP4.sample(self.tpoints)],
        #                                [self.yP4.sample(self.tpoints)]])
        # self.speeds = (np.array([[self.dxP3.sample(self.tpoints)],
        #                        [self.dyP3.sample(self.tpoints)]])**2).sum(axis=0)**0.5
        # self.curve_length = ((x1-x2)**2+(y1-y2)**2)**0.5

    def get_Cpoly(self):
        return self.zcoeffs

    def get_points(self):
        return self.xs + 1j * self.ys

    def get_time(self):
        return np.array([self.time])


class Curve:
    def __init__(self, points):
        self.set_points(points)

    def set_points(self, points):
        self.xs = points[0, :]
        self.ys = points[1, :]
        self.time = len(self.xs) - 1
        self.xcoeffs = get_lagrange(np.arange(len(self.xs)), self.xs)
        self.ycoeffs = get_lagrange(np.arange(len(self.ys)), self.ys)
        self.zcoeffs = self.xcoeffs + 1j * self.ycoeffs
        # quartics parameterizing in t
        self.xP4 = Poly(self.xcoeffs)
        self.yP4 = Poly(self.ycoeffs)
        self.zP4 = Poly(self.zcoeffs)
        # analytic derivative functions
        self.dxP3 = self.xP4.diff()
        self.dyP3 = self.yP4.diff()
        self.dzP3 = self.zP4.diff()

    def get_Cpoly(self):
        return self.zcoeffs

    def get_points(self):
        return self.xs + 1j * self.ys

    def get_time(self):
        return np.array([self.time])


class Shape:
    def __init__(self, listOfLines, numOrders=50):
        self.list = listOfLines
        self.times = np.array([0])
        for line in self.list[0:-1]:
            # self.times is when each line segment starts in global time
            self.times = np.concatenate([self.times, line.get_time() + self.times[-1]])
        self.T = self.times[-1] + self.list[-1].get_time()
        self.numOrders = numOrders
        self.fourierSeries(self.numOrders)

    def fourierSeries(self, numOrders):
        self.coefficients = (np.ones(numOrders * 2 + 1) / self.T).astype(complex)
        negativeOrders = -np.flip(np.arange(numOrders + 1))
        strictlyPositiveOrders = np.arange(numOrders) + 1
        self.orders = np.concatenate((negativeOrders, strictlyPositiveOrders))
        self.orderIndex = np.arange(len(self.orders))
        for i, order in enumerate(self.orders):
            if not order == 0:
                self.coefficients[i] *= self.integralDotProd(np.array(self.T / (2 * order * np.pi)))
            else:
                # can't use recursive integration for x^nexp(0)
                integral = 0
                for line in self.list:
                    lineEnd = line.get_time()
                    poly = line.get_Cpoly()
                    integratedPoly = np.concatenate([[0], [coeff / (1 + i) for i, coeff in enumerate(poly)]])
                    # since it's a definite integral of a poly and the start of the domain is 0, only evaluate t_f
                    integral += sum([integratedPoly[n] * lineEnd ** n for n in range(len(poly) + 1)])
                self.coefficients[i] *= integral

    def integralDotProd(self, a):
        # a is the reciprocal of the coefficient of x in exp(ix/a)
        # the function being multiplied by z(t) is exp(-ix/a)
        integral = 0
        time = 0
        for i, line in enumerate(self.list):
            # get time limits of integration over this segment
            time = self.times[i]
            lineStart = 0
            lineEnd = line.get_time() + lineStart
            timeStart = time
            timeEnd = line.get_time() + timeStart
            poly = line.get_Cpoly()
            integralPoly = np.zeros(len(poly)).astype(complex)
            for n, coeff in enumerate(poly):
                # n is the order I(n), coeff is the trailing coeff
                for j in np.arange(n + 1):
                    integralPoly[n - j] += np.array(coeff) * (a * 1j) ** (j + 1) * (-1) ** j * math.factorial(
                        n) / math.factorial(n - j)
            I_f = np.exp(timeEnd / (1j * a)) * sum([integralPoly[n] * lineEnd ** n for n in range(len(poly))])
            I_i = np.exp(timeStart / (1j * a)) * sum([integralPoly[n] * lineStart ** n for n in range(len(poly))])
            integral += I_f - I_i
        return integral

    def regeneratePoints(self):
        # samples = np.zeros(200*len(self.list)).astype(complex)
        samples = np.array([sum(
            [self.coefficients[i] * np.exp(1j * order * 2 * np.pi * t / self.T) for i, order in enumerate(self.orders)])
                            for t in np.linspace(0, self.T, 80 * len(self.list))])
        # for k, t in enumerate(np.linspace(0,self.T, 200*len(self.list))):
        #    samples[k] = sum([self.coefficients[i]*np.exp(1j*order*2*np.pi*t/self.T) for i, order in enumerate(self.orders)])
        return np.squeeze(samples)

    def getTransformData(self):
        return self.coefficients, self.T


class DrawScreen:
    def __init__(self):
        print('d: delete last, <Return>: interpolate, n: fourier transform')
        self.root = tk.Tk()
        self.root.geometry('800x800')
        self.root.bind('<Return>', self.draw)
        self.root.bind('<FocusIn>', self.square_window)
        self.root.bind('d', self.deleteLast)
        self.root.bind('n', self.generate)
        self.firstDrawing = False
        self.secondDrawing = False
        self.hasFourier = False
        self.screen = tk.Canvas(master=self.root, height=800, width=800, bg="#a0ebbb")
        self.screen.pack(fill=tk.BOTH, expand=True)
        self.shapelist = []
        tk.Button(master=self.screen, text='+', command=self.addline, borderwidth=10, relief=tk.GROOVE).place(
            rely=0, relheight=0.1, relx=0.9, relwidth=0.1, bordermode='inside')
        tk.Button(master=self.screen, text='+', command=self.addcurve, borderwidth=10, relief=tk.GROOVE).place(
            rely=0.12, relheight=0.1, relx=0.9, relwidth=0.1, bordermode='inside')
        tk.Button(master=self.screen, text='delete', command=self.deleteLast, borderwidth=10, relief=tk.GROOVE).place(
            rely=0.24, relheight=0.1, relx=0.9, relwidth=0.1, bordermode='inside')
        tk.Button(master=self.screen, text='interpolate', command=self.draw, borderwidth=10, relief=tk.GROOVE).place(
            rely=0.36, relheight=0.1, relx=0.9, relwidth=0.1, bordermode='inside')
        tk.Button(master=self.screen, text='fourier', command=self.generate, borderwidth=10, relief=tk.GROOVE).place(
            rely=0.48, relheight=0.1, relx=0.9, relwidth=0.1, bordermode='inside')
        tk.Label(master=self.screen, text='Add Line', font=('', 12)).place(rely=0.0, relwidth=0.1, relx=0.78,
                                                                           relheight=0.1, bordermode='inside')
        tk.Label(master=self.screen, text='Add Curve', font=('', 12)).place(rely=0.12, relwidth=0.1, relx=0.78,
                                                                            relheight=0.1, bordermode='inside')
        self.t = turtle.RawTurtle(self.screen)
        self.t.ht()
        self.root.mainloop()

    def square_window(self, event):
        size = max(self.root.winfo_height(), self.root.winfo_width())
        dims = str(size) + 'x' + str(size)
        self.root.geometry(dims)

    def addline(self):
        if len(self.shapelist) != 0:
            # Force last point of previous shape at same point at first point of current shape
            lp = self.shapelist[-1].last_point()
            self.shapelist.append(GraphicalShape(np.concatenate([[lp], np.random.rand(1, 2) * 0.8]), self.screen))
        else:
            self.shapelist.append(GraphicalShape(np.random.rand(2, 2) * 0.8, self.screen))

    def addcurve(self):
        if len(self.shapelist) != 0:
            lp = self.shapelist[-1].last_point()
            self.shapelist.append(GraphicalShape(np.concatenate([[lp], np.random.rand(4, 2) * 0.8]), self.screen))
        else:
            self.shapelist.append(GraphicalShape(np.random.rand(5, 2) * 0.8, self.screen))

    def draw(self, event=None):
        if self.firstDrawing:
            self.t.clear()
            self.firstDrawing = False
            self.secondDrawing = False
        self.t.screen.setworldcoordinates(0, 1, 1, 0)
        self.t.up()
        self.t.ht()
        self.t.width(5)
        self.t.pencolor("#000000")
        self.t.speed('fastest')
        allPoints = np.empty((0, 2))
        for s in self.shapelist:
            points = s.interpolate()
            allPoints = np.concatenate([allPoints, points])
        self.t.setpos(allPoints[0, 0], allPoints[0, 1])
        self.t.down()
        for slc in allPoints:
            self.t.setpos(slc[0], slc[1])
        self.t.up()
        self.firstDrawing = True

    def deleteLast(self, event=None):
        if len(self.shapelist) is not 0:
            self.shapelist[-1].destroy()
            del self.shapelist[-1]

    def generate(self, event=None):
        linelist = []
        for s in self.shapelist:
            p = np.rollaxis(s.get_points(), 1)
            linelist.append(Curve(p))
        self.totalShape = Shape(linelist, 50)
        zcoords = self.totalShape.regeneratePoints()
        points = np.array([np.real(zcoords), np.imag(zcoords)])
        points = np.rollaxis(points, 1)
        points = points
        if self.secondDrawing:
            self.t.clear()
            self.secondDrawing = False
            self.firstDrawing = False
        self.t.screen.setworldcoordinates(0, 1, 1, 0)
        self.t.up()
        self.t.ht()
        self.t.width(5)
        self.t.pencolor("#00ffff")
        self.t.speed('fastest')
        self.t.setpos(points[0, 0], points[0, 1])
        self.t.down()
        for slc in points:
            self.t.setpos(slc[0], slc[1])
        self.t.up()
        self.secondDrawing = True
        self.hasFourier = True

    def get_coeffs(self):
        if self.hasFourier:
            return self.totalShape.getTransformData()


class GraphicalShape:
    def __init__(self, points, screen):
        self.points = points
        self.nodes = []
        for point in points:
            self.nodes.append(Node(point, screen))

    def interpolate(self):
        # gets coefficients for current points and returns a bunch of points along that polynomial
        t = np.arange(len(self.points))
        xcoeffs = get_lagrange(t, self.points[:, 0])
        ycoeffs = get_lagrange(t, self.points[:, 1])
        interpolatedPoints = np.array([Poly(xcoeffs).sample(np.linspace(t[0], t[-1], 50)),
                                       Poly(ycoeffs).sample(np.linspace(t[0], t[-1], 50))])
        return np.rollaxis(interpolatedPoints, 1)

    def get_points(self):
        return self.points

    def last_point(self):
        return self.points[-1]

    def destroy(self):
        for node in self.nodes:
            node.destroy()


class Node:
    def __init__(self, point, screen):
        # point is a slice of a numpy array which is held by GraphicalShape, any change to self.point through indexing
        # is therefore reflected by a change in GraphicalShape.points
        self.point = point
        self.master = screen
        self.widget = tk.Frame(master=self.master, bg='red')
        self.widget.place(relx=self.point[0], rely=self.point[1], relheight=0.01, relwidth=0.01,
                          bordermode='outside')
        self.widget.bind('<B1-Motion>', self.drag)

    def drag(self, event):
        self.point[0] = (self.widget.winfo_x() + event.x) / self.master.winfo_width()
        self.point[1] = (self.widget.winfo_y() + event.y) / self.master.winfo_height()
        self.widget.place_configure(relx=self.point[0], rely=self.point[1])

    def destroy(self):
        self.widget.destroy()

drawscreen = DrawScreen()