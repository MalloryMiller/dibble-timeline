from utils import *
import os


import geopandas as gpd
import rioxarray # used by xarray for some reason, must be first
import rasterio as rs
import numpy as np

from geocube.vector import vectorize

class ElevationError():

    def __init__(self, REMAfname):
        self.fname = REMAfname
        raw_file = rioxarray.open_rasterio(self.fname, masked=True)
        print(raw_file)
        print('converting to dataframe')
        dataframe = raw_file.to_dataframe(name='elevation').reset_index()
        print('done converting')
        self.rema = gpd.GeoDataFrame(dataframe,
            geometry=gpd.points_from_xy(dataframe['x'], dataframe['y']),
            crs=raw_file.rio.crs)
        print('dataframe made')
        self.rema = self.rema.dropna()
        

        self.date = self.fname.split('_')[-1].split('.')[0]
        self.year = self.date.split('-')[0]
        self.month = self.date.split('-')[1]
        self.day = self.date.split('-')[2]
        #self.date = np.datetime64(self.date)

        cur_year_fname = 'output/reprojected/elevation/' + self.year + "_e.gpkg"
        if os.path.exists(cur_year_fname):
            self.start_file = cur_year_fname 
        else:
            self.start_file = None


    def get_error(self):
        if self.start_file == None:
            print('NO ICESAT DATA TO COMPARE')
            return
        
        closest_point = None

        cur_year = gpd.read_file(self.start_file)
        print(cur_year)

        combined = gpd.sjoin_nearest(
            self.rema, cur_year,
            'inner', 2, 
            'rema', 'icesat2', 'dist'
        )

        '''xs = []
        ys = []
        rema_data = self.rema.sel(
            x=xs,
            y=ys,
            method="nearest",
            tolerance=2 #bc 2 meter dimension? maybe?
        )'''


        
        print(cur_year['date'].dtype)
        print(cur_year['date'].unique())
        print(combined.columns)
        print(combined)
        mixed = combined['elevation_icesat2'] - combined['elevation_rema']
        print(mixed)

        print(np.mean(mixed))



