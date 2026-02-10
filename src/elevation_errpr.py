from utils import *
import os


from pygeotools.lib import malib

import geopandas as gpd
import rioxarray # used by xarray for some reason, must be first
import rasterio as rs
from rasterio.enums import Resampling
import numpy as np
import pyogrio

from geocube.vector import vectorize
from plotting import Plotting, plt



class ElevationError():

    def __init__(self, REMAfname, sample_size=20, mask_type = 'mask', output_name='output', max_diff = 50):
        default_sample_size = 2
        self.sample_size = sample_size
        sample_factor = default_sample_size/self.sample_size
        

        self.fname = REMAfname
        self.max_diff = max_diff 
        self.output_fname = output_name
        if self.fname == "" or self.fname == None:
            return

        self.date = self.fname.split('_')[-1].split('.')[0]
        self.year = self.date.split('-')[0]
        self.month = self.date.split('-')[1]
        self.day = self.date.split('-')[2]
        self.date = np.datetime64(self.date.split('T')[0])

        cur_year_fname = 'output/reprojected/elevation/' + self.year + "_e.gpkg"
        if os.path.exists(cur_year_fname):
            self.start_file = cur_year_fname 
        else:
            self.start_file = None

        self.start_file = gpd.read_file(self.start_file)

        self.start_file['date'] = self.start_file['date'].dt.round(freq='D')
        testing_spots = self.start_file['date'].unique()

        if self.date in testing_spots:
            self.start_file = self.start_file[self.start_file['date'] == self.date]
        else:
            print("ICESAT match not found")
            self.rema = []
            return # TODO can add support for non-exact days if needed here



        self.plotter = Plotting()

        raw_file = rioxarray.open_rasterio('input/rema/raw/' + self.fname, masked=True)
        
        if mask_type != None:
            mask_file = rioxarray.open_rasterio('input/rema/raw/bitmask/' + self.fname.replace('dem', mask_type))
        
        if sample_size != default_sample_size:
            raw_file = raw_file.rio.reproject(raw_file.rio.crs, shape=(int(raw_file.rio.width * sample_factor), int(raw_file.rio.height * sample_factor)), resampling=Resampling.bilinear).squeeze()
            if mask_type != None:
                mask_file = mask_file.rio.reproject(mask_file.rio.crs, shape=(int(mask_file.rio.width * sample_factor), int(mask_file.rio.height * sample_factor)), resampling=Resampling.bilinear).squeeze()
        else:
            raw_file = raw_file.squeeze()
            if mask_type != None:
                mask_file = mask_file.squeeze()

        if mask_type != None:
            raw_file = raw_file.where(mask_file.values != 1, np.nan)
       

        print('converting to dataframe')
        dataframe = raw_file.to_dataframe(name='elevation').reset_index()
        print('done converting')
        self.rema = gpd.GeoDataFrame(dataframe,
            geometry=gpd.points_from_xy(dataframe['x'], dataframe['y']),
            crs=raw_file.rio.crs)
        print('dataframe made')
        self.rema = self.rema.dropna()


    def reallign(self, reference=None):
        from demcoreg import dem_align

        if reference == None:
            reference = 'output/reprojected/elevation/' + str(self.year)+ "_e.tif"

        dem_align.main([reference, 'input/rema/raw/' + self.fname, '-max_dz', self.max_diff], '-outdir', self.output_fname)

        return self.fname


    def stack(self, location):
        print('geting stuff')
        fn_list = os.listdir(location) 
        for x in range(len(fn_list)-1, -1, -1):
            print(x)
            if fn_list[x].split('.')[-1] != 'tif':
                fn_list.pop(x)
            else:
                fn_list[x] = os.getcwd() + '/' +  location + '/' +  fn_list[x]


        print(fn_list)
        print('making stack')
        s = malib.DEMStack(fn_list, res='min', extent='union', stack_fn=None, outdir=location + '/output/', 
                           srs=None, trend=False, robust=False, med=False, stats=False, save=False, 
                           sort=False, datestack=False, mask_geom=None, min_dt_ptp=np.nan, n_thresh=2)
        #Stack standard deviation
        print(s.compute_stat('mean'))
        #Stack linear trend
        print(s.compute_trend())
        self.write_trend()
        



    def get_error(self):
        try:
            if self.rema == []:
                print('NO ICESAT DATA TO COMPARE')
                return
        except:
            pass
        
        self.start_file.sort_values('date', inplace=True)

        combined = gpd.sjoin_nearest(
            self.rema, self.start_file,
            'inner', self.sample_size,
            'rema', 'icesat2', 'dist'
        )
        #combined.dropna(inplace=True)

        mixed = combined['elevation_icesat2'] - combined['elevation_rema']
        print(mixed)
        combined.insert(0, 'diff', mixed)


        trends = 'input/elevation/ATL11_trends_APS.gpkg'
        trends_df = gpd.read_file(trends)
        combined = gpd.sjoin_nearest(
            combined, trends_df,
            'left', self.sample_size,
            'combined', 'trend'
        )
        print(combined)


        if len(combined) == 0:
            print('No overlapping points.')
            return
        

        


        combined.to_csv('output_.csv')

        fig, ax = self.plotter.error_hist(combined, min_=-5, max_=5, color_col='trend',max_c=1, min_c=-1)
        plt.savefig('output/images/histograms/' + self.output_fname + '.png', dpi=200)
        
        plt.close('all')



