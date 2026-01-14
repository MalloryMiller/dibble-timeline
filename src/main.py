import sys
from utils import *

from plotting import VelocityPlot, StreamPlot, DiffPlot
from file_manager import FileManager


class main():
    '''
    Reads from sys.argv and generates any file(s) that are requested.


    Attributes
    ----------
    args : List[String]
        The arguments used when the program is run from command line, flags removed
    flags : Flags
        a Flags object with any relevant args added to it
    title : String
        The basic title that will be used for any files generated, not including file extension
    xlim : List[Integer]
        a pair of values in ascending order that reflect the limits of the x axis
    ylim : List[Integer]
        a pair of values in ascending order that reflect the limits of the y axis

    Methods
    -------
    generate_item(string, flags:Flags, dim=None)
        Generates a single file of the type specified by the flags and dim.
        
    '''


    def __init__(self):
        self.args = sys.argv
        self.title = ""
        self.point_name = None

        

        to_flag = []

        for x in range(len(self.args)):
            if self.args[x][0] == '-':
                to_flag.append(x)
        to_flag.reverse()
        self.flags = Flags()
        for x in to_flag:
            self.flags.add(self.args.pop(x))


        if len(self.args) == 1:
            self.xlim = AREAS[DEFAULT_AREA][0]
            self.ylim = AREAS[DEFAULT_AREA][1]
            self.title = DEFAULT_AREA
            print('Default location: Dibble')

        if len(self.args) == 2:
            if self.args[1] not in list(AREAS.keys()) and self.args[1] not in list(STREAM_POINTS.keys()):
                print("That preset area does not exist yet.")
                print("The preset areas available are: ")
                print(", ".join(AREAS.keys()))
                return 
            
            elif self.args[1] in list(STREAM_POINTS.keys()):

                self.flags.add('-stream') # must be a stream with this input
                self.point_name = self.args[1]
                self.args[1] = STREAM_POINTS[self.args[1]][2]
                self.title = self.args[1]

            
            self.xlim = AREAS[self.args[1]][0]
            self.ylim = AREAS[self.args[1]][1]
            self.title = self.args[1]

        elif len(self.args) == 5:
            
            self.xlim = [float(self.args[1]), float(self.args[2])]
            self.ylim = [float(self.args[3]), float(self.args[4])]
            self.title = f'{float(self.args[1])}.{float(self.args[2])}.{float(self.args[3])}.{float(self.args[4])}'

        else:
            print("Please include the area or coordinates for the area you would like to analize.")
            print("The preset areas available are: ")
            print(", ".join(AREAS.keys()))
            return 
        

        valid = True
        if float(self.xlim[1]) <= float(self.xlim[0]):
            valid = False
            print("Your horizontal limits are invalid. The first should be the smallest and the second the largest.")

        if float(self.ylim[1]) <= float(self.ylim[0]):
            valid = False
            print("Your vertical limits are invalid. The first should be the smallest and the second the largest.")
        if not valid:
            return 
        


        file_type = self.flags.chart_type()

        print("Generating " + file_type + " Plot(s).")

        if file_type == 'splitnc':
            self.generate_item(dim='x')
            self.generate_item(dim='y')

        elif file_type == 'stream':
            vx = self.generate_item(dim='x')
            vy = self.generate_item(dim='y')

            plot = StreamPlot(vx, vy, 
                              starting_pos=STREAM_POINTS[self.point_name],
                              starting_year=self.flags.YEARSTART, ending_year=self.flags.YEAREND, 
                              flags=self.flags)
            plot.generate_all(self.get_title())

        elif file_type == 'sourcediff':
            print(self.flags.sources())
            fm1 = FileManager(self.xlim[0], self.xlim[1], self.ylim[0], self.ylim[1],
                        sources=[self.flags.sources()[0]], combo_mode=self.flags.combo_method(),
                        yearEnd=self.flags.YEAREND, yearStart=self.flags.YEARSTART)
            fm1.open()
            fm2 = FileManager(self.xlim[0], self.xlim[1], self.ylim[0], self.ylim[1],
                        sources=[self.flags.sources()[1]], combo_mode=self.flags.combo_method(),
                        yearEnd=self.flags.YEAREND, yearStart=self.flags.YEARSTART, source_override=fm1)
            fm2.open()
            
            plot = DiffPlot(fm1, fm2)
            plot.generate_charts(self.get_title())


        else:
            self.generate_item()



    def get_title(self, dim=None):
        title = ""
        combo_mode = self.flags.combo_method()
        file_type = self.flags.chart_type()
        sources = self.flags.sources()

        if combo_mode != "weighted":
            title += combo_mode + "_"
        title += "_".join(sources) + "/"

        if file_type == 'splitnc':
            title += dim + "_"

        elif file_type == 'sourcediff':
            title += "SourceDiff"

        if self.point_name:
            title += self.point_name
        else:
            title += self.title

            
        return title
        


    def get_files(self, dim=None):
        '''
        Generates a single file of the type specified by the dimension if any.


        Parameters
        ----------
        dim : String, optional
            Dimension, 'x' or 'y', if any.

        Returns
        -------
        None
        '''

        sources = self.flags.sources()
        combo_mode = self.flags.combo_method()
        file_type = self.flags.chart_type()

        if dim == 'x':
            fm = FileManager(self.xlim[0], self.xlim[1], self.ylim[0], self.ylim[1],
                        sources=sources,combo_mode=combo_mode, 
                        yearEnd=self.flags.YEAREND, yearStart=self.flags.YEARSTART,
                        further_processing=x_only_parse, 
                        base_drop_vars = ['STDX', 'STDY', #'ERRY', 'ERRX', 
                                    'mapping', 'landice', 
                                    'vy_error', 'v_error',
                                    'coord_system', 'velocity'])
        elif dim == 'y':
            fm = FileManager(self.xlim[0], self.xlim[1], self.ylim[0], self.ylim[1],
                        sources=sources,combo_mode=combo_mode, 
                        yearEnd=self.flags.YEAREND, yearStart=self.flags.YEARSTART,
                        further_processing=y_only_parse, 
                        base_drop_vars = ['STDX', 'STDY', #'ERRX', #'ERRY', 
                                    'mapping', 'landice', 
                                    'vx_error', 'v_error',
                                    'coord_system', 'velocity'])
            
        else:
            fm = FileManager(self.xlim[0], self.xlim[1], self.ylim[0], self.ylim[1],
                        sources=sources,combo_mode=combo_mode, 
                        yearEnd=self.flags.YEAREND, yearStart=self.flags.YEARSTART)
            
        fm.open()

        return fm


    
main()