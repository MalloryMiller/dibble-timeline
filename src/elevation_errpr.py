from utils import *
import os


from pygeotools.lib import malib

import geopandas as gpd
import rioxarray # used by xarray for some reason, must be first
import xarray as xr
import rasterio as rs
from rasterio.enums import Resampling
import numpy as np
import pyogrio
from osgeo import gdal
from geocube.vector import vectorize
from plotting import Plotting, plt
from geocube.api.core import make_geocube

import pandas as pd
from shapely.geometry import Point



class ElevationError():

    def __init__(self, REMAfname, sample_size=20, mask_type = 'mask', output_name='output', max_diff = 50, get_icesat_match=True):
        default_sample_size = 2
        self.sample_size = sample_size
        sample_factor = default_sample_size/self.sample_size
        self.plotter = Plotting()
        

        self.fname = REMAfname
        self.max_diff = max_diff 
        self.output_fname = output_name
        if self.fname == "" or self.fname == None:
            return

        print(self.fname)

        i = -1
        registered = False
        try:
            while len(self.fname.split('_')[i].split('-')) != 3:
                print(self.fname.split('_')[i].split('-'))
                registered = True
                i -= 1
        
            self.date = self.fname.split('_')[i].split('.')[0]
        except:
            print('the provided fname does not contain a dat in YYYY-MM-DD format.')
            return

        self.year = self.date.split('-')[0]
        self.month = self.date.split('-')[1]
        self.day = self.date.split('-')[2].split('T0')[0]
        self.date = np.datetime64(self.date.split('T')[0])


        if get_icesat_match:
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


        raw_file = rioxarray.open_rasterio('input/rema/raw/' + self.fname, masked=True)
        
        try:
            if mask_type != None:
                mask_file = rioxarray.open_rasterio('input/rema/raw/bitmask/' + self.fname.replace('dem', mask_type))
        except:
            mask_type = None
            print('no mask file found for ' + self.fname)
        
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
            year_offset = 1
            year_search_range = 10
            
            reference_post = 'output/reprojected/elevation/' + str(self.year)+ "_e.tif"
            reference_pre = 'output/reprojected/elevation/' + str(int(self.year) - year_offset)+ "_e.tif"
            cur_year = self.year


            ''' Get nearest years around with data'''
            while not os.path.isfile(reference_post) and int(self.year) + year_search_range > cur_year:
                cur_year += 1
                reference_post = 'output/reprojected/elevation/' + str(cur_year)+ "_e.tif"
                year_offset += 1

            cur_year = int(self.year) - year_offset
            while not os.path.isfile(reference_pre) and int(self.year) - year_search_range < cur_year:
                cur_year -= 1
                reference_pre = 'output/reprojected/elevation/' + str(cur_year)+ "_e.tif"
                year_offset += 1

            ''' if edge of range just use the single closest one'''
            if not os.path.isfile(reference_pre):
                reference = reference_post
            if not os.path.isfile(reference_post):
                reference = reference_pre

            '''if not edge of range use both, based on if you linearly plotted each pixel between the two years'''
            if os.path.isfile(reference_pre) and os.path.isfile(reference_post):

                projected_ref = "output/reprojected/elevation/temp.tif"
                date_perc = (float(self.month) / 12 + ((1/12) * (float(self.day) / 30))) + (12 * (year_offset - 1)) # in % of year

                arr1 = rioxarray.open_rasterio(reference_pre)
                arr2 = rioxarray.open_rasterio(reference_post)
                print(arr1)
                print(arr2)
                
                arr = arr1.copy(deep=True)
                arr += (arr2 - arr1) * date_perc # get % change from pre date to post date
                arr.rio.write_crs("EPSG:3031", inplace=True)

                '''
                arr = arr.to_dataframe()
                print(arr)
                arr['geometry'] = arr.apply(lambda row: Point(row['y'],row['x']),  axis=1)
                arr = gpd.GeoDataFrame(arr, geometry='geometry', crs='EPSG:3031')
                print(arr)

                arr = make_geocube(
                    vector_data=arr,
                    measurements=["elevation"],
                    resolution=(-0.001, 0.001), 
                    output_crs="epsg:3031",
                )'''

                arr.rio.to_raster(projected_ref, no_data=np.nan)
                gdal.Warp(projected_ref, projected_ref,
                        dstSRS='EPSG:3031')


                reference = projected_ref

            

        if reference == None:
            print('coregistration failed, no data at relevant years')
            return # there was nothing in the year before or current year
        
        print(reference)
        dem_align.main([reference, 'input/rema/raw/' + self.fname])

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
        plt.savefig('output/images/histograms/' + self.output_fname.split('T0')[0] + '.png', dpi=200)
        
        plt.close('all')



