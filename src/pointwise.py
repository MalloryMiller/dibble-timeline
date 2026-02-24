import datetime
from utils import *
from file_manager import GravimetryManager, ElevationManager, VelocityManager

import geopandas as gpd
import rioxarray # used by xarray for some reason, must be first
import xarray as xr
from shapely.geometry import Point
import pandas as pd
import numpy as np

from plotting import Plotting

class Pointwize():
    def __init__(self, flags, xlim, ylim, points, data, change=True):
        self.flags = flags
        self.yearStart = int(self.flags.YEARSTART)
        self.yearEnd = int(self.flags.YEAREND)
        self.xlim = xlim
        self.ylim = ylim
        self.points = POINT_LISTS[points]
        self.data = data
        self.change = change

        self.point_df = None
        self.results = {}

    def create_point_df(self, pointls=None):
        if pointls == None:
            pointls = self.points

        point_geom = []
        for p in pointls:
            point_geom.append(Point(p[1], p[0]))

        df_ref = pd.DataFrame({'geometry':point_geom})
        df_ref = gpd.GeoDataFrame(df_ref, geometry=point_geom, crs='EPSG:3031')
        return df_ref
    
    def get_label(self, index):
        return str(chr(index + 65))


    def save_point_df(self):
        p = Plotting()
        df = self.create_point_df()
        labels = []
        for x in range(len(self.points)):
            labels.append(self.get_label(x))
        df['labels'] = labels
        p.plot_df_on_borders(df)

    def gpd_geom_match(self, out, index, column_of_interest = 'elevation'):
        p = self.points[index]
        df_ref = self.create_point_df([p])

        #df_ref = gpd.sjoin_nearest(df_ref, out)
        df_ref = gpd.sjoin(df_ref, out, distance=100,predicate='dwithin')
        print(df_ref)

        time = []
        data = []

        for x in df_ref['date'].unique():
            time.append(x)
            print(df_ref[df_ref['date'] == x][column_of_interest])
            data.append(df_ref[df_ref['date'] == x][column_of_interest].mean())

        time = np.array(time)
        data = np.array(data)
        print(data)
        print(time)
        if len(data) == 0:
            return

        if self.change:
            print(self.change)
            ref_time = time.min()
            data = data - data[time == ref_time]
        self.results[index] = pd.DataFrame({'time': time,
                                        self.data: data})

    
    def geotiff_geom_match(self, out, index, column_of_interest = 'band_data'):
        p = self.points[index]

        df = out.sel(x=p[1], y=p[0], method='nearest')


        if 'time' not in df.variables and 'year' in df.variables:
            t = df['year'].values
            new_dates = []
            for x in range(len(t)):
                new_dates.append(datetime.datetime(t[x], 1, 1))
            time_dim = 'year'
        else:
            time_dim = 'time'
            if df['time'].dtype != np.datetime64:
                new_dates = []
                t = df['time'].values
                for x in range(len(t)):
                    new_dates.append(np.datetime64(t[x]))
            else:
                new_dates = df['time'].values

        df[time_dim] = new_dates
        '''if self.change:
            ref_time = df[time_dim].min()
            data = df.copy(deep=True)
            print(df)
            print(df[column_of_interest][df[time_dim] == ref_time])
            df[column_of_interest] = df[column_of_interest] - data[column_of_interest][data[time_dim] == ref_time]'''
        
        self.results[index] = pd.DataFrame({'time': new_dates,
                                            self.data: df[column_of_interest]})


    def plot_time_series(self, fig, ax):
        if not self.results:
            self.get_data()
        
        for p in self.results.keys():
            ax.plot(self.results[p]['time'], self.results[p][self.data].values, label = self.get_label(p))


    def get_data(self):

        type_info = {
            'vel': 'band_data',
            'grav': 'dm',
            'elev': 'elevation'
        }
        
        fms = {
            'vel': VelocityManager,
            'grav': GravimetryManager,
            'elev': ElevationManager
        }

        print()
        print()
        filemanager = fms[self.data](self.xlim, self.ylim, self.flags, self.data)
        print('getting output')
        out = filemanager.get_ouput_files()
        print('comparing points')
        for p in range(len(self.points)):
            if type(out) == gpd.geodataframe.GeoDataFrame:
                self.gpd_geom_match(out, p, column_of_interest=type_info[self.data])
            elif type(out) == xr.core.dataset.Dataset:
                self.geotiff_geom_match(out, p, column_of_interest=type_info[self.data])
            self.results[p] = self.results[p].sort_values('time')
