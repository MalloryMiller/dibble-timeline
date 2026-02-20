from utils import *
from file_manager import FileManager

class Pointwize():
    def __init__(self, yearStart, yearEnd, xlim, ylim, points, data):
        self.yearStart = int(yearStart)
        self.yearEnd = int(yearEnd)
        self.xlim = xlim
        self.ylim = ylim
        self.points = POINT_LISTS[points]
        self.data = data

    def isolate_point(self, index):
        self.points[index]

    
    def plot_time_series(self, fig, ax):
        pass


    def get_data(self):
        
        print()
        print()
        filemanager = FileManager(self.xlim[0], self.xlim[1], self.ylim[0], self.ylim[1],'', 
                                self.yearStart, self.yearEnd, self.data)
        print('geting output')
        out = filemanager.get_ouput_files()
        print(out)