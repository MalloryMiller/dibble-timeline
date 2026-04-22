from utils import *

from file_manager import VelocityManager, ElevationManager, GravimetryManager, FirnAirManager,  plt

class ComparisonPlot():
    def __init__(self, flags, x, y):
        self.x_data = x
        self.y_data = y

    def get_file_manager(self, data):
    def get_data(self, rema=False, firn_source=-1):

        type_info = {
            'vel': 'band_data',
            'grav': 'dm',
            'elev': 'elevation',
            'firn': 'band_data',
        }
        
        fms = {
            'vel': VelocityManager,
            'grav': GravimetryManager,
            'elev': ElevationManager,
            'firn': FirnAirManager,
        }

        if self.data == 'gl':
            self.get_gl_set()
            self.get_gl_set(GL_GPKG_radar, ['date'], 'Open Polar Radar, 2024')
            return 

        if self.data == 'firn' and firn_source == -1:
            self.get_data(firn_source=0)
            self.get_data(firn_source=1)
            self.get_data(firn_source=2)
            return
        elif self.data == 'firn':
            filemanager = fms[self.data](self.xlim, self.ylim, self.flags, self.data, source=firn_source)
        else:
            filemanager = fms[self.data](self.xlim, self.ylim, self.flags, self.data)

        print('getting output')
        out = filemanager.get_ouput_files()
        print('comparing points')
        for p in range(len(self.points)):
            if type(out) == gpd.geodataframe.GeoDataFrame:
                self.gpd_geom_match(out, p, column_of_interest=type_info[self.data])
            elif type(out) == xr.core.dataset.Dataset:
                self.geotiff_geom_match(out, p, column_of_interest=type_info[self.data])

            if self.get_label(p) not in self.results.keys():
                return
            
            self.results[self.get_label(p)] = self.results[self.get_label(p)].sort_values('time')

        if rema and self.data == 'elev':
            return self.get_data_rema()

