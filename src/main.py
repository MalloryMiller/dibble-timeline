import datetime
import sys
import os
from utils import *


from file_manager import VelocityManager, ElevationManager, GravimetryManager, FirnAirManager,  IPRManager, plt
from timeseries import VelTimeSeries
from elevation_errpr import ElevationError
from pointwise import Pointwize
import matplotlib.pyplot as plt
from plotting import Plotting


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


        self.chart_type = self.flags.chart_type()

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
        


        to_build = self.flags.rebuilding()

        '''t = VelTimeSeries(self.flags, self.xlim, self.ylim, 'vel', years=[2000, 2025])
        t.generate_charts("Velocity Trends")'''

        for x in to_build:
            print(x)
            if x == 'velx':
                print(self.build_files(dim='x'))
            elif x == 'vely':
                print(self.build_files(dim='y'))
            elif x == 'vel':
                print(self.build_files())
            else:
                print(self.build_files(data=x))



        '''t = VelTimeSeries(self.flags, self.xlim, self.ylim, 'vel', years=[2000, 2025])
        t.generate_charts("Velocity Trends")'''

        '''t = Trends(self.flags, self.xlim, self.ylim, 'vel')
        t.plot_trends()'''
        
        '''p = Profile(self.flags, POINT_LISTS[self.title][0]['point'], self.xlim, self.ylim)
        p.plot_profile()'''
        #fm = IPRManager([0,0], [0,0], self.flags, 'elev', 'IPR')
        #p = Plotting()
        #p.plot_IPR_range(fm, GL_IPR_FRAME)


        if self.flags.chart_type() == 'frame':
            p = Plotting()
            p.frame()

        if self.flags.chart_type() == 'points':
            self.point_name = self.title
            points = POINT_LISTS[self.point_name]
            for i in points:
                self.get_points_timeline(i)
            
        if self.flags.chart_type() == 'elev-error':
            self.get_elevation_error()



            #e = ElevationError('2022/SETSM_s2s041_WV01_20220109_10200100BD005100_10200100BD3E7600_2m_lsf_seg1_dem_2022-01-09T00:00:00Z.tif', get_icesat_match=False)
            #e.filter_clouds()
            '''for x in range(self.flags.YEARSTART, self.flags.YEAREND):
                self.coregister_rema(x)'''
            #self.test_coregister_rema()

            
            '''ee = ElevationError(None) #'2022/SETSM_s2s041_WV01_20220109_10200100BD005100_10200100BD3E7600_2m_lsf_seg1_dem_2022-01-09T00:00:00Z.tif')
            ee.stack('test_2022/01')'''
        

    def coregister_rema(self, year, override=False, clean=True):
        dir = 'input/rema/raw/'
        if not os.path.isdir(dir + str(year)):
            return
        
        test_files = os.listdir(dir + str(year))

        for t in test_files:
            if t.split('_')[-1] == 'align' or t.split('.')[-1] != 'tif':
                continue
            print("Proceeding:", t.split('.')[0] + '_dem_align' not in test_files or override)
            if (t.split('.')[0] + '_dem_align' not in test_files or override):
                e1 = ElevationError(str(year) + '/' + t, get_icesat_match=False) # '2021/adjusted/SETSM_s2s041_WV02_20210228_10300100B2087900_10300100B555C000_2m_lsf_seg1_dem_2021-02-28T00:00:00Z.tif',mask_type=None )#
                try:
                    e1.reallign()
                except Exception as e:
                    print('Allignment failed, it looks like this file may be bad.')
                    print(e)

            gend_dir = dir + str(year) + '/' + t.split('.')[0] + '_dem_align'
            if clean and os.path.isdir(gend_dir):
                files = os.listdir(gend_dir)
                for f in files:
                    if f.split('_')[-1] == 'align.tif' or f.split('_')[-1] == 'align.png':
                        continue
                    os.remove(gend_dir + '/' + f)





    def test_coregister_rema(self):
        test_files = [ # exact matches to icesat data to compare
            '2020/SETSM_s2s041_WV03_20200202_1040010057310E00_10400100583F6E00_2m_lsf_seg1_dem_2020-02-02T00:00:00Z.tif',
            '2021/SETSM_s2s041_WV02_20210228_10300100B2087900_10300100B555C000_2m_lsf_seg1_dem_2021-02-28T00:00:00Z.tif', 
            '2019/SETSM_s2s041_WV02_20191211_103001009E169600_10300100A061CF00_2m_lsf_seg1_dem_2019-12-11T00:00:00Z.tif',
            '2022/SETSM_s2s041_WV01_20220109_10200100BD005100_10200100BD3E7600_2m_lsf_seg2_dem_2022-01-09T00:00:00Z.tif',
            '2022/SETSM_s2s041_WV01_20220109_10200100BD005100_10200100BD3E7600_2m_lsf_seg1_dem_2022-01-09T00:00:00Z.tif',
            ]
        
        for t in test_files:
            e1 = ElevationError(t) # '2021/adjusted/SETSM_s2s041_WV02_20210228_10300100B2087900_10300100B555C000_2m_lsf_seg1_dem_2021-02-28T00:00:00Z.tif',mask_type=None )#
            e1.reallign()
            for f in os.listdir('input/rema/raw/' + t.split('.')[0] + "_dem_align"):
                if f.split('_')[-1] == 'align.tif':
                    e1 = ElevationError(t.split('.')[0] + "_dem_align/" + f, mask_type = None, output_name=t.split('/')[-1])
                    e1.get_error()


    def get_title(self, dim=None):
        title = ""
        combo_mode = self.flags.combo_method()
        file_type = self.flags.chart_type()
        sources = self.flags.sources_v()

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

    def get_elevation_error(self):
        for year in range(self.flags.YEARSTART, self.flags.YEAREND):
            
            strips = os.listdir(REMA_RAW_LOCATION + str(year)) 
            for s in strips:
                if s.split('.')[-1] == 'tif':
                    ee = ElevationError(str(year) + '/' + s, output_name=s.split('/')[-1].split('.')[0]) #'2022/SETSM_s2s041_WV01_20220109_10200100BD005100_10200100BD3E7600_2m_lsf_seg1_dem_2022-01-09T00:00:00Z.tif')
                    print('getting error')

    

    def get_points_timeline(self, point, data = ['gl', 'elev', 'vel', 'grav', 'firn'], change = True, rema=False): #['vel', 'elev', 'grav'] #  'vel', 'elev', 'firn'

        labels = {
            'vel': "Velocity Change since 2020 (%)",
            'elev': 'Elevation Change since 2020 (%)',
            'grav': 'Gravimetry Change since 2020 (kg/m²)',
            'gl': 'Grounding Line Change (m)',
            'firn': 'Firn Air Height (m)',
        }


        can_change = {
            'vel': 'interp%',
            'elev': 'interp',
            'grav': True,
            'gl': False,
            'firn': False,
        }

        if not change:
            labels['grav'] = 'Gravimetry Change since 2011 (kg/m²)',
            labels['elev'] = 'Elevation (m)'
            labels['vel'] = 'Velocity (m/y)'
        #elif type(change) == str and '%' not in change:
        #    labels['grav'] = 'Gravimetry Change since 2020 (kg/m²)',
        #    labels['elev'] = 'Elevation Change since 2020 (m)'
        #   labels['vel'] = 'Velocity Change since 2020 (m/y)'


        gl_elevation_width = 0.45

        width_ratios = [1, 0]
        if 'gl' in data:
            width_ratios = [2-gl_elevation_width, gl_elevation_width - .2]
        if len(data) == 1:
            data.append('')

        fig, ax = plt.subplots(len(data), 2, gridspec_kw={'width_ratios': width_ratios})
        fig.set_figheight(3*len(data))

        if width_ratios[1] > 1:
            fig.set_figwidth(8)


        for i, d in enumerate(data):
            if d == '':
                ax[i][0].set_visible(False)
                ax[i][1].set_visible(False)
                continue

            
            f = Flags()
            for fl in self.flags.flags:
                f.add(fl)
            f.add('-2000-2025')
            print(point)
            p = Pointwize(f, self.xlim, self.ylim, 
                        point['point'], data = d, change=change and can_change[d],
                        pt_range = point['point_range'], point_spacing=point['point_spacing'])
            p.plot_time_series(fig, ax[i][0], rema=rema, plot_range=[datetime.datetime(self.flags.YEARSTART, 1, 1), datetime.datetime(self.flags.YEAREND, 1, 1)])
            if i == 0:
                p.save_point_df() # save the points df after first one was made
                plt.close('all')


            ax[i][0].set_ylabel(labels[d])
            ax[i][0].grid()


            
            if i == len(data)-1:
                ax[i][0].set_xlabel('Year')

            if d == 'gl':
                p.plot_elevation_summary(fig, ax[i][1])
                ax[i][0].legend()
            else:
                ax[i][0].legend(loc='lower left')
                ax[i][1].set_visible(False)


        
        print("Saving image...")
        fig.savefig(POINTWISE_OUTPUT_LOCATION + str(int(point['point'][0])) + '_' + str(int(point['point'][1])) + "_plot.png", dpi=200)
        print(POINTWISE_OUTPUT_LOCATION + str(int(point['point'][0])) + '_' + str(int(point['point'][1])) + "_plot.png")
        
        plt.close('all')


    def build_files(self, data='vel', dim=''):
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

        managers = {
            'vel': VelocityManager,
            'elev': ElevationManager,
            'firn': FirnAirManager,
            'grav': GravimetryManager
        }

        sources = self.flags.sources_v()
        fm = managers[data](self.xlim, self.ylim, self.flags,
                        data=data+dim)
        fm.build_files()
        if data == 'elev':
            fm.build_supplementary_files()



    
main()