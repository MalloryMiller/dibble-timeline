import sys
from utils import *


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
    get_files(string, flags:Flags, dim=None)
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

        if len(self.args) == 2:
            if self.args[1] not in list(AREAS.keys()):
                print('Preset area ' + self.args[1] + ' not found.')
                return
            self.xlim = AREAS[self.args[1]][0]
            self.ylim = AREAS[self.args[1]][1]
            self.title = self.args[1]
            print('Preset area "' + self.args[1] + '" being used.')
        elif len(self.args) == 5:
        
            self.xlim = [float(self.args[1]), float(self.args[2])]
            self.ylim = [float(self.args[3]), float(self.args[4])]
            self.title = f'{float(self.args[1])}.{float(self.args[2])}.{float(self.args[3])}.{float(self.args[4])}'

        else:
            self.xlim = AREAS[DEFAULT_AREA][0]
            self.ylim = AREAS[DEFAULT_AREA][1]
            self.title = DEFAULT_AREA
            print('Default location being used: ' + DEFAULT_AREA)
        

        valid = True
        if float(self.xlim[1]) <= float(self.xlim[0]):
            valid = False
            print("Your horizontal limits are invalid. The first should be the smallest and the second the largest.")

        if float(self.ylim[1]) <= float(self.ylim[0]):
            valid = False
            print("Your vertical limits are invalid. The first should be the smallest and the second the largest.")
        if not valid:
            return 
        


        #print(self.get_files(dim='x').file)
        #print(self.get_files(dim='y').file)
        #print(self.get_files().file)
        print(self.get_files(data='elev').file)


        



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
        


    def get_files(self, data='vel', dim=None):
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
        if data == 'vel':
            fm = FileManager(self.xlim[0], self.xlim[1], self.ylim[0], self.ylim[1],
                        sources=sources,combo_mode=combo_mode, 
                        yearEnd=self.flags.YEAREND, yearStart=self.flags.YEARSTART,
                        further_processing=VELOCITY_SPECIAL_PREP[dim], 
                        base_drop_vars = VELOCITY_DROP_VARS[dim], label=VELOCITY_DIM_LABELS[dim])
                
            fm.build_velocity_files()

            return fm
        
        elif data == 'elev':
            
            fm = FileManager(self.xlim[0], self.xlim[1], self.ylim[0], self.ylim[1], 
                        sources=sources,combo_mode=combo_mode, 
                        yearEnd=self.flags.YEAREND, yearStart=self.flags.YEARSTART)
                
            fm.build_elevation_files()

            return fm



    
main()