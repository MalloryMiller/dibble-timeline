import glob
from utils import *
from pathlib import Path
import os
import numpy as np

from plotting import Plotting

from scipy.interpolate import RegularGridInterpolator
import rioxarray # used by xarray for some reason, must be first
import xarray as xr
import matplotlib.pyplot as plt

from shapely.geometry import Point
import pandas as pd
import geopandas as gpd
from geocube.api.core import make_geocube
from osgeo import gdal

import h5py


class FileManager:
    def __init__(self, xlims, ylims, flags, data, ftype,
                 fname_formats = FILE_FORMATS, h5_location = ELEVATION_H5_LOCATION,
                 source_override = False, label='',  sources = None, further_processing = lambda x: x, 
                 base_drop_vars = []):
        
        self.plotter = Plotting()

        self.flags = flags
        
        self.minlat =  xlims[0]
        self.maxlat =  xlims[1]
        self.minlon =  ylims[0]
        self.maxlon =  ylims[1]

        self.label = label
        self.ftype = ftype
        self.data = data

        self.fname_format = fname_formats
        self.h5_location = h5_location
        self.sources = sources

        self.yearStart = int(flags.YEARSTART)
        self.yearEnd = int(flags.YEAREND)
        self.drop_variables = base_drop_vars

        self.special_prep = further_processing


        self.source_override = source_override


        if self.source_override:
            self.sample_source = self.source_override.sample_source
            self.sample_file = self.source_override.sample_file

        elif sources != None and sources != []:
            self.sample_source = self.sources[0]
            self.sample_file = SOURCE_SAMPLE_FILES[self.sample_source]

        
        

        self.file = {}

    
    def get_ouput_files(self):
        f, years = self.fnames()

        all_files = []

        for file in f:
            if file.split('.')[-1] == 'gpkg':
                cur_df = gpd.read_file(file)
                cur_df = cur_df.to_crs('EPSG:3031')

            elif file.split('.')[-1] == 'tif':
                cur_df = xr.open_dataset(file).squeeze()
            all_files.append(cur_df)

        if len(all_files) == 0:
            return

        file = f[0]

        if file.split('.')[-1] == 'gpkg':
            if len(f) == 1:
                return all_files[0]
            self.file = pd.concat(all_files)

        elif file.split('.')[-1] == 'tif':
            if len(f) == 1:
                return all_files[0]
            
            self.file = xr.concat(all_files, dim=years)
            self.file = self.file.rename({'concat_dim': 'year'})

        return self.file

    
    


    def generate_image(self, data, data_name, chart_function, year, reprojected = False):
        try:
            if data != None:
                data.rio.to_raster(TIF_LOCATION + data_name + '.tif')
        except:
            pass
        
        if chart_function != None:
            fig, ax = plt.subplots()
            plt.title(data_name)
            location = TIF_LOCATION + data_name + '.tif'
            if reprojected:
                location = TIF_LOCATION +'reprojected/' + data_name + '.gpkg'

            if not chart_function(location, year):
                plt.close('all')
                return
            
            #print("Saving image...")
            plt.savefig('test.png', dpi=200)
            plt.savefig(TEST_PNG_LOCATION + data_name + '.png', dpi=200)
            
            plt.close('all')



    def get_tif_data(self, fname=None, source=None, base=False):
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
        if self.ftype == 'gpkg':
            return

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
    

    def pointify(self, row):
        #Dr. Lilien code
        return Point(row['longitude'],row['latitude'])
    
    def build_gravimetry_files(self):
        return



    def close(self):
        '''
        Resets the current file to hold nothing.
        '''
        self.file = {}



class VelocityManager(FileManager):

    def __init__(self, xlims, ylims, flags, data,
                 fname_formats = FILE_FORMATS, h5_location = ELEVATION_H5_LOCATION,
                 source_override = False, label='',  sources = None):
        
        further_processing = VELOCITY_SPECIAL_PREP[None]
        ftype='tif'
        base_drop_vars = []

        if data == 'velx':
            further_processing = VELOCITY_SPECIAL_PREP['x'], 
            base_drop_vars = VELOCITY_DROP_VARS['x']
            label = VELOCITY_DIM_LABELS['x']
        elif data == 'vely':
            further_processing = VELOCITY_SPECIAL_PREP['y'], 
            base_drop_vars = VELOCITY_DROP_VARS['y']
        elif data == 'vel':
            base_drop_vars = ['STDX', 'STDY', #'ERRX', 'ERRY',
                                    'mapping', 'landice', 
                                    'vx_error', 'vy_error', #'v_error',
                                    'coord_system']
            
        self.combo_mode = flags.combo_method()
            
        super().__init__(xlims, ylims, flags, data, ftype, fname_formats=fname_formats, h5_location=h5_location,
                            source_override=source_override, label=label, sources=sources, 
                            further_processing=further_processing, base_drop_vars=base_drop_vars)
        
        


    def get_velocity_fname(self, year):
        return 'velocities/' + str(year) + self.label + "_v." + self.ftype
        

        
    def build_velocity_files(self):
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
        self.get_tif_data(base=True)

        for x in list(range(self.yearStart, self.yearEnd+1)):
            if not os.path.exists(self.get_velocity_fname(x, ftype='.tif')):

                found = {}


                for sources in self.sources:
                    done = False

                    for formats in self.fname_format[sources]:

                        if done or not Path(formats.format(str(x), str(int(x) + 1))).is_file():
                            continue
                        

                        f = self.get_tif_data(fname=formats.format(str(x), str(int(x) + 1)), source=sources)

                        found[sources] = f
                        done = True

                    if not done:
                        print("No", sources, "file found at the year", x, "                                          ")
                        continue

                    



                if len(found.keys()) != 0:
                    to_add = self.get_tif_data()
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



                    tif_to_save = to_add.velocity
                    tif_to_save = tif_to_save.rio.set_spatial_dims(x_dim='x', y_dim='y')
                    self.generate_image(tif_to_save, self.get_velocity_fname(x), self.plotter.plot_velocity, x)

                self.file[x] = self.get_velocity_fname(x, ftype='.tif')


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
                self.file[x] = self.get_velocity_fname(x, ftype='.tif')

            progress.load_bar(x - self.yearStart, self.yearEnd - self.yearStart)
            '''
        self.file = xr.concat(self.file, dim=years_found)
        self.file = self.file.rename({'concat_dim': 'year'})
        '''
        return self.file

    def build_files(self):
        self.build_velocity_files()

    def fnames(self):

        fname_data = {
            'vel': self.get_velocity_fname,
            'velx': self.get_velocity_fname,
            'vely': self.get_velocity_fname,
        }
        fname_prefix = {
            'vel': OUTPUT,
            'velx': OUTPUT,
            'vely': OUTPUT,
        }

        fnames = []
        found_years = []

        for year in range(self.yearStart, self.yearEnd):
            location = fname_data[self.data]

            f = fname_prefix[self.data] + location(year)
            if not Path(f).is_file():
                continue
            fnames.append(f)
            found_years.append(year)


        return fnames, found_years
    


class ElevationManager(FileManager):

    def __init__(self, xlims, ylims, flags, data,
                 source_override = False, label='',  sources = None):
        
        further_processing = VELOCITY_SPECIAL_PREP[None]
        base_drop_vars = []
        ftype = 'gpkg'


        
        if data == 'evel' and sources == None:
            sources = ['IceSAT2']
        elif data == 'rema':
            ftype='tif'
            sources = ['REMAPrev']
        elif data == 'remaraw':
            ftype='tif'
            sources = ['REMA']

            
        super().__init__(xlims, ylims, flags, data, ftype,
                            source_override=source_override, label=label, sources=sources, 
                            further_processing=further_processing, base_drop_vars=base_drop_vars)
        
    
        

    def get_elevation_fname(self, year):
        return  'elevation/' + str(year) + "_e." + self.ftype
        
        

    def get_rema_fname(self, year):
        return  'rema/' + str(year) + "_r." + self.ftype
    
    def get_rema_raw_fname(self, year):
        return  'rema/' + str(year) + "_r." + self.ftype
    


    def build_files(self):
        
        if self.data == 'elev':
            self.build_elevation_files()
        
        elif self.data == 'rema':
            self.build_rema_files()
        
        elif self.data == 'rawrema':
            self.build_raw_rema_files()


    def fnames(self):

        fname_data = {
            'elev': self.get_elevation_fname,
            'rema': self.get_rema_fname,
            'remaraw': self.get_rema_raw_fname
        }
        fname_prefix = {
            'elev': OUTPUT,
            'rema': OUTPUT,
            'remaraw': OUTPUT
        }

        fnames = []
        found_years = []

        for year in range(self.yearStart, self.yearEnd):
            location = fname_data[self.data]

            if type(location) == str:
                fnames = [fname_prefix[self.data] + location]

            else:
                f = fname_prefix[self.data] + location(year)
                if not Path(f).is_file():
                    continue
                fnames.append(f)
                found_years.append(year)

        return fnames, found_years
    



    def build_elevation_files(self):
        progress = LoadingBar()
        progress2 = LoadingBar()

        #adapted from Dr. Lilien code

        attrs = ['h_corr', 'latitude', 'longitude', 'delta_time', 'h_corr_sigma'] 

        D11=[]
        pairs=[1, 2, 3]
        files = sorted(glob.glob(self.h5_location + '/*.h5')) #ONLY ONE RIGHT NOW

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
            self.file[np.datetime64(str(c))] = pd.DataFrame(columns=['latitude', 'longitude', 'velocity', 'date', 'geometry'])

        cur_track = 0
        max = len(D11)
        progress.load_bar(cur_track, max)
        for track in D11:
        
            dates = (track['delta_time'].astype('timedelta64[s]') + np.datetime64("2018-01-01T00:00")).astype('M8[Y]')
            track['latitude'] = np.transpose([track['latitude']] * len(track['h_corr'][0]))
            track['longitude'] = np.transpose([track['longitude']] * len(track['h_corr'][0]))
            track['datetime'] = track['delta_time'].astype('timedelta64[s]') + np.datetime64("2018-01-01T00:00")

            for c in self.file.keys():
                df = pd.DataFrame({'latitude': track['latitude'][dates == c].flatten(),
                                    'longitude': track['longitude'][dates == c].flatten(), 
                                    'elevation': track['h_corr'][dates == c].flatten(),
                                    'date': track['datetime'][dates == c].flatten()})
                df['geometry'] = df.apply(self.pointify, axis=1)
                self.file[c] = pd.concat([self.file[c], df])
            
            cur_track += 1
            progress.load_bar(cur_track, max)

        i = 0
        for c in self.file.keys():
            if not len(self.file[c]):
                i+= 1
                continue
            try:
                gdf_final = gpd.GeoDataFrame(self.file[c], geometry='geometry', crs='EPSG:4326')
                gdf_final.to_file(OUTPUT + self.get_elevation_fname(c,ftype='.gpkg'), driver='GPKG')
            except:
                print('Saving year ' + str(c) + ' gpkg failed.')
            
            out_grid = make_geocube(
                vector_data=gdf_final,
                measurements=["elevation"],
                resolution=(-0.001, 0.001), 
                output_crs=gdf_final.crs 
            )

            out_grid["elevation"].rio.to_raster(TIF_LOCATION + self.get_elevation_fname(c) + '.tif')
            gdal.Warp(TIF_LOCATION +'reprojected/' + self.get_elevation_fname(c) + '.tif', 
                      TIF_LOCATION + self.get_elevation_fname(c) + '.tif',
                      dstSRS='EPSG:3031')

            self.generate_image(None, self.get_elevation_fname(c), self.plotter.plot_elevation, c, reprojected=True)
            i += 1
            progress2.load_bar(i, len(list(self.file.keys())))

    def build_rema_files(self):
        for x in list(range(self.yearStart, self.yearEnd+1)):
            self.generate_image(None, self.get_rema_fname(x), self.plotter.plot_rema_coverage, x, )

    def build_raw_rema_files(self):
        for x in list(range(self.yearStart, self.yearEnd+1)):
            self.generate_image(None, self.get_rema_raw_fname(x), self.plotter.plot_raw_rema_data, x, )



class GravimetryManager(FileManager):

    def __init__(self, xlims, ylims, flags, data, label=''):
        
        ftype='tif'
        super().__init__(xlims, ylims, flags, data, ftype,label=label)
        
    

    def build_files(self):
        return
    

    def fnames(self):
        return [GRAV_LOCATION], []