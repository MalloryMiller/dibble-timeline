from utils import *
import os


import geopandas as gpd
import rioxarray # used by xarray for some reason, must be first
import rasterio as rs
import numpy as np
import pyogrio

from geocube.vector import vectorize
from plotting import Plotting, plt



class ElevationError():

    def __init__(self, REMAfname):
        self.fname = REMAfname

        self.date = self.fname.split('_')[-1].split('.')[0]
        self.year = self.date.split('-')[0]
        self.month = self.date.split('-')[1]
        self.day = self.date.split('-')[2]
        self.date = np.datetime64(self.date.split('T')[0])


        self.plotter = Plotting()

        raw_file = rioxarray.open_rasterio('input/rema/raw/' + self.fname, masked=True).squeeze()
        
        mask_file = rioxarray.open_rasterio('input/rema/raw/bitmask/' + self.fname.replace('dem', 'mask')).squeeze()
        #print(mask_file)
        #raw_file.values[mask_file.values != 1] = np.nan
       

        print('converting to dataframe')
        dataframe = raw_file.to_dataframe(name='elevation').reset_index()
        print('done converting')
        self.rema = gpd.GeoDataFrame(dataframe,
            geometry=gpd.points_from_xy(dataframe['x'], dataframe['y']),
            crs=raw_file.rio.crs)
        print('dataframe made')
        self.rema = self.rema.dropna()
        


        cur_year_fname = 'output/reprojected/elevation/' + self.year + "_e.gpkg"
        if os.path.exists(cur_year_fname):
            self.start_file = cur_year_fname 
        else:
            self.start_file = None


    def get_error(self):
        if self.start_file == None:
            print('NO ICESAT DATA TO COMPARE')
            return
        

        cur_year = gpd.read_file(self.start_file)

        cur_year['date'] = cur_year['date'].dt.round(freq='D')
        testing_spots = cur_year['date'].unique()

        if self.date in testing_spots:
            cur_year = cur_year[cur_year['date'] == self.date]

        cur_year.sort_values('date', inplace=True)

        combined = gpd.sjoin_nearest(
            self.rema, cur_year,
            'inner', 2, #bc 2 meter dimension, get pixel you're on
            'rema', 'icesat2', 'dist'
        )
        #combined.dropna(inplace=True)

        '''
        xs = []
        ys = []
        rema_data = self.rema.sel(
            x=xs,
            y=ys,
            method="nearest",
            tolerance=2 
        )'''

        print(combined)
        mixed = combined['elevation_icesat2'] - combined['elevation_rema']
        print(mixed)
        combined.insert(0, 'diff', mixed)

        print(cur_year['date'].unique())
        print(combined.columns)

        fig, ax = self.plotter.error_hist(combined, min_=-5, max_=5)
        plt.savefig('test_histogram.png', dpi=200)
        
        plt.close('all')



