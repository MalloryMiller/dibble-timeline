import glob
from utils import *
from pathlib import Path
import os
import numpy as np

from plotting import plot_geotiff

from scipy.interpolate import RegularGridInterpolator
import rioxarray # used by xarray for some reason, must be first
import xarray as xr
import matplotlib.pyplot as plt

from shapely.geometry import Point
import pandas as pd
import geopandas as gpd
from geocube.api.core import make_geocube

import h5py


class FileManager:
    def __init__(self, minlat, maxlat, minlon, maxlon, sources, combo_mode,
                 yearStart, yearEnd, 
                 fname_formats = VEL_FILE_FORMATS, h5_location = ELEVATION_H5_LOCATION,
                 further_processing = VELOCITY_SPECIAL_PREP[None],
                 base_drop_vars = None, source_override = False, label=''):
        
        self.minlat =  minlat
        self.maxlat =  maxlat
        self.minlon =  minlon
        self.maxlon =  maxlon

        self.label = label

        self.fname_format = fname_formats
        self.h5_location = h5_location
        self.sources = sources
        self.combo_mode = combo_mode

        self.yearStart = yearStart
        self.yearEnd = yearEnd
        if base_drop_vars == None:
            self.drop_variables = ['STDX', 'STDY', #'ERRX', 'ERRY',
                                    'mapping', 'landice', 
                                    'vx_error', 'vy_error', #'v_error',
                                    'coord_system']
        else:
            self.drop_variables = base_drop_vars

        self.special_prep = further_processing


        self.source_override = source_override


        if self.source_override:
            self.sample_source = self.source_override.sample_source
            self.sample_file = self.source_override.sample_file

        else:
            self.sample_source = self.sources[0]
            self.sample_file = SOURCE_SAMPLE_FILES[self.sample_source]

        
        

        self.file = {}


    def generate_image(self, data, name):
        data.rio.to_raster(name)
                    

        fig, ax = plt.subplots()
        plot_geotiff(name, fig, ax)
        print("Saving image...")
        plt.savefig("test.png", dpi=200)
        
        plt.close('all')


    def get_data(self, fname=None, source=None, base=False):
        '''
        Returns an opened file cut to the size that this filemanager has as the min and max lat and long.
        Drops all variable not relevant to the actual calculated velocity.


        Parameters
        ----------
        fname : String, optional
            The name of the file that will be read
        source : String, optional
            The source of the file used to determine how it should be processed
        base : Boolean, optional
            If set to true will set the bounds to the potentially smaller range of the found area

        Returns
        -------
        xarray.Dataset
            Processed dataset with TODO
        '''

        if fname == None:
            fname = self.sample_file
        if source == None:
            source = self.sample_source

        sample_file = xr.open_dataset(fname, drop_variables=self.drop_variables)
        
        sample_file = sample_file.where((sample_file.x > self.minlat) & (sample_file.x < self.maxlat), drop=True)
        sample_file = sample_file.where((sample_file.y > self.minlon) & (sample_file.y < self.maxlon), drop=True)

        sample_file = FORMAT_PARSE[source](sample_file)

        if base:
            self.minlat =  min(sample_file.x).values
            self.maxlat =  max(sample_file.x).values
            self.minlon =  min(sample_file.y).values
            self.maxlon =  max(sample_file.y).values
        

        return self.special_prep(sample_file, source)
    

    def get_velocity_fname(self, year):
        return TIF_LOCATION + str(year) + self.label + "_v.tif"
        
        

    def get_elevation_fname(self, year):
        return TIF_LOCATION + str(year) + "_e.tif"
    

    def get_elevation_gpkg_fname(self, year):
        return TIF_LOCATION + str(year) + "_e.gpkg"
        
        

    def build_velocity_files(self, dim=None):
        '''
        Opens all files from all sources in a range of years (self.yearStart through self.yearEnd inclusively)
        places relevant information from sourcs into self.file, one dataset where all other files have been concatonated
        along the new year dimension.


        Parameters
        ----------
        None

        Returns
        -------
        String[]
            list of the generated data files
        '''
        
        self.close()

        #years_found = []
        progress = LoadingBar()
        print("Opening " + ", ".join(self.sources) + " data.")
        self.get_data(base=True)

        for x in list(range(self.yearStart, self.yearEnd+1)):
            if not os.path.exists(self.get_velocity_fname(x)):

                found = {}


                for sources in self.sources:
                    done = False

                    for formats in self.fname_format[sources]:

                        if done or not Path(formats.format(str(x), str(int(x) + 1))).is_file():
                            continue
                        

                        f = self.get_data(fname=formats.format(str(x), str(int(x) + 1)), source=sources)

                        found[sources] = f
                        done = True

                    if not done:
                        print("No", sources, "file found at the year", x, "                                          ")

                    



                if len(found.keys()) != 0:
                    to_add = self.get_data()
                    has_data = True

                    if "ItsLive" in found and "ItsLive" != self.sample_source:

                        ygrid, xgrid = np.meshgrid(to_add.y.values, to_add.x.values)
                        vel = RegularGridInterpolator((found['ItsLive'].y.values, found['ItsLive'].x.values), 
                                                    found['ItsLive'].velocity.values, method='linear')
                        
                        #print(len(to_add.y.values), len(to_add.x.values))
                        #print(len(found['ItsLive'].y.values), len(found['ItsLive'].x.values))
                        
                        
                        vel = vel((ygrid, xgrid))
                        vel = xr.DataArray(vel, 
                                            coords={'x': to_add.x.values, 'y': to_add.y.values},
                                            dims=['x', 'y'])


                        c = RegularGridInterpolator((found['ItsLive'].y.values, found['ItsLive'].x.values), 
                                                    found['ItsLive'].v_error.values, method='linear')
                        c = c((ygrid, xgrid))
                        c = xr.DataArray(c, 
                                        coords={'x': to_add.x.values, 'y': to_add.y.values},
                                        dims=['x', 'y'])
                            
                        
                        if "Measures" in found and has_data:

                            if self.combo_mode == "weighted":

                                to_add['velocity'] = ((found["Measures"].velocity * found["Measures"].v_error) + (vel * c)) / (found["Measures"].v_error + c)
                                to_add['v_error'] = found["Measures"].v_error + c


                            elif self.combo_mode == "average":

                                to_add['velocity'] = (found["Measures"].velocity + vel) / 2
                                to_add['v_error'] = found["Measures"].v_error + c




                        elif "Measures" in found and "ItsLive" not in found and not has_data:
                            to_add['velocity'] = found["Measures"].velocity
                            to_add['v_error'] = found["Measures"].v_error
                        elif not has_data:
                            continue
                        else:
                            to_add['velocity'] = vel
                            to_add['v_error'] = c

                    elif "ItsLive" != self.sample_source:
                        to_add = found["Measures"]
                    else: 
                        to_add  = found["ItsLive"]



                    #self.file.extend([to_add])
                    tif_to_save = to_add.velocity
                    tif_to_save = tif_to_save.rio.set_spatial_dims(x_dim='x', y_dim='y')
                    self.generate_image(tif_to_save, self.get_velocity_fname(x))

                self.file[x] = self.get_velocity_fname(x)


                '''
                if self.combo_mode == 'offset':
                    cur_years = []
                    if "Measures" in found:
                        cur_years.append(x)
                    if "ItsLive" in found:
                        cur_years.append(x+.5)
                else:
                    cur_years = [x]
                years_found.extend(cur_years)
            '''   
            else :
                self.file[x] = self.get_velocity_fname(x)

            progress.load_bar(x - self.yearStart, self.yearEnd - self.yearStart)
            '''
        self.file = xr.concat(self.file, dim=years_found)
        self.file = self.file.rename({'concat_dim': 'year'})
'''
        return self.file


    def pointify(self, row):
        return Point(row['longitude'],row['latitude'])
    
    def build_elevation_files(self):
        progress = LoadingBar()

        #Dr. Lilien code

        attrs = ['h_corr', 'latitude', 'longitude', 'delta_time', 'h_corr_sigma'] 

        D11=[]
        pairs=[1, 2, 3]
        files = sorted(glob.glob(self.h5_location + '/*.h5'))

        for f in files:
            with h5py.File(f) as h5f:
                # loop over beam pairs
                
                for pair in pairs:
                    # check if a beam exists, if not, skip it
                    if '/pt%d' % (pair) not in h5f:
                        continue
                    # loop over the groups in the dataset dictionary
                    
                    temp={}
                    for dataset in attrs:
                    
                        DS='/pt%d/%s' % (pair, dataset)
                        # since a dataset may not exist in a file, we're going to try to read it, and if it doesn't work, we'll move on to the next:
                        try:
                            temp[dataset]=np.array(h5f[DS])
                            # some parameters have a _FillValue attribute.  If it exists, use it to identify bad values, and set them to np.nan
                            if '_FillValue' in h5f[DS].attrs:
                                fill_value=h5f[DS].attrs['_FillValue']
                                bad = temp[dataset]==fill_value
                                temp[dataset]=np.float64(temp[dataset])
                                temp[dataset][bad]=np.nan
                            #  if dataset == 'delta_time':
                            #      temp[dataset] = np.datetime64("2018-01-01T00:00") + temp[dataset].astype('timedelta64[s]')
                        except KeyError as e:
                            pass
                    D11.append(temp)


        for c in range(self.yearStart, self.yearEnd+1):
            self.file[np.datetime64(str(c))] = pd.DataFrame(columns=['latitude', 'longitude', 'velocity', 'date'])

        cur_track = 0
        max = len(D11)
        progress.load_bar(cur_track, max)
        for track in D11:
            
            for v in range(len(track['h_corr'])-1):
                dates = ((track['delta_time'][v]).astype('timedelta64[s]') + np.datetime64("2018-01-01T00:00"))
                for x in range(len(dates)):
                    if str(dates[x]) =='NaT':
                        continue
                    year = dates[x].astype('M8[Y]')

                    try:
                        self.file[year]
                    except:
                        continue
                    #uncert = np.sqrt(np.nansum(track['h_corr_sigma'][v] ** 2.0, axis=1) / np.sum(~np.isnan(track['h_corr_sigma'][v]), axis=1))
                    df = pd.DataFrame({'latitude': track['latitude'][v], 'longitude': track['longitude'][v], 'velocity': [track['h_corr'][v][x]], })#'uncert': uncert})
                    df['geometry'] = df.apply(self.pointify, axis=1)
                    self.file[year] = pd.concat([self.file[year]])
            cur_track += 1
            progress.load_bar(cur_track, max)

        for c in range(self.yearStart, self.yearEnd):



            try:
                self.file[year].to_file(self.get_elevation_gpkg_fname(c), driver='GPKG')
            except ValueError:
                print("Value Error")
                pass

            try:
                gdf_final = gpd.GeoDataFrame(self.file[year], geometry='geometry', crs='EPSG:4326')
                
                to_tif = make_geocube(
                    vector_data=gdf_final,
                    measurements=["velocity"],
                    resolution=(-0.1, 0.1),
                )
                
                self.generate_image(to_tif["velocity"], self.get_elevation_fname(cur_track))
            except:
                print('image failed')


        #print(D11)





    def close(self):
        '''
        Resets the current file to hold nothing.
        '''
        self.file = {}

