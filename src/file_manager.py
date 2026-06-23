import glob
from utils import *
from pathlib import Path
import os
import numpy as np
import datetime

from plotting import Plotting

from scipy.interpolate import RegularGridInterpolator
import rioxarray # used by xarray for some reason, must be first
import xarray as xr
import matplotlib.pyplot as plt

from shapely.geometry import Point
import pandas as pd
import geopandas as gpd
from functools import partial
from geocube.api.core import make_geocube
from geocube.rasterize import rasterize_image
from osgeo import gdal
from osgeo_utils import gdal_calc

from rasterstats import zonal_stats
import rasterio as rs
from exactextract import exact_extract

import xvec
from dateutil.relativedelta import relativedelta

import h5py


class FileManager:
    def __init__(self, xlims, ylims, flags, data, ftype,
                 fname_formats = FILE_FORMATS, h5_location = ELEVATION_H5_LOCATION,
                 source_override = False, label='', further_processing = lambda x: x, 
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
        self.gpkg_source = 'IceSAT2'
        self.sources = flags.sources_v()

        self.yearStart = int(flags.YEARSTART)
        self.yearEnd = int(flags.YEAREND)
        self.drop_variables = base_drop_vars

        self.special_prep = further_processing


        self.source_override = source_override



        if self.source_override:
            self.sample_source = self.source_override.sample_source
            self.sample_file = self.source_override.sample_file

        elif self.sources != None and self.sources != []:
            self.sample_source = self.sources[0]
            self.sample_file = SOURCE_SAMPLE_FILES[self.sample_source]

        
        

        self.file = {}


    def chack_valid_path(self, fname):
        if '.' in fname.split('/')[-1]:
            fname = '/'.join(fname.split('/')[:-1])
        os.makedirs(fname, exist_ok=True)

    
    def get_ouput_files(self):
        f, years, sources = self.fnames()
        all_files = []

        for i, file in enumerate(f):
            if file.split('.')[-1] == 'gpkg':
                cur_df = gpd.read_file(file)
                cur_df = cur_df.to_crs('EPSG:3031')
                cur_df['sources'] = self.gpkg_source

            elif file.split('.')[-1] == 'tif':
                cur_df = xr.open_dataset(file).squeeze()

                if len(sources) != 0:
                    cur_df['sources'] = sources[i]
                if len(sources) != 0 and sources[i] == 'ItsLive' and 'Measures' in sources:
                    ref = xr.open_dataset(f[sources.index('Measures')]).squeeze()

                    ygrid, xgrid = np.meshgrid(ref.y.values, ref.x.values)
                    vel = RegularGridInterpolator((cur_df.y.values, cur_df.x.values), 
                                                cur_df.band_data.values, method='linear')
                    
                    vel = vel((ygrid, xgrid))
                    ref['band_data'] = (('x', 'y'), vel)
                    ref['sources'] = sources[i]
                    cur_df = ref
                    
                    
            all_files.append(cur_df)
        print(all_files)

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
            
            self.file = xr.concat(all_files, dim=years, join='outer')
            self.file = self.file.rename({'concat_dim': 'year'})


        return self.file

    
    


    def generate_image(self, data, data_name, chart_function, year, reprojected = False):
        if type(data) != bool:
            os.makedirs(TIF_LOCATION + '/'.join(data_name.split('/')[:-1]), exist_ok=True)
            data.transpose('y', 'x').rio.to_raster(TIF_LOCATION + data_name)
            if reprojected:
                os.makedirs(TIF_LOCATION +'reprojected/' + '/'.join(data_name.split('/')[:-1]), exist_ok=True)
        
        if chart_function != None:
            fig, ax = plt.subplots()
            plt.title(data_name)
            location = TIF_LOCATION + data_name
            if reprojected:
                os.makedirs(TIF_LOCATION +'reprojected/' + '/'.join(data_name.split('/')[:-1]), exist_ok=True)
                location = TIF_LOCATION +'reprojected/' + data_name

            if not chart_function(location, year):
                plt.close('all')
                return
            
            #print("Saving image...")
            path = TEST_PNG_LOCATION + data_name.split('.')[0] + '.png'
            self.chack_valid_path(path)
            plt.savefig(path, dpi=200)
            
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
                 source_override = False, label=''):
        
        
        further_processing = VELOCITY_SPECIAL_PREP[None]
        ftype='tif'
        base_drop_vars = []


        if data == 'velx':
            further_processing = VELOCITY_SPECIAL_PREP['x']
            base_drop_vars = VELOCITY_DROP_VARS['x']
            label = VELOCITY_DIM_LABELS['x']
        elif data == 'vely':
            further_processing = VELOCITY_SPECIAL_PREP['y']
            base_drop_vars = VELOCITY_DROP_VARS['y']
            label = VELOCITY_DIM_LABELS['y']
        elif data == 'vel':
            base_drop_vars = ['STDX', 'STDY', #'ERRX', 'ERRY',
                                    'mapping', 'landice', 
                                    'vx_error', 'vy_error', #'v_error',
                                    'coord_system']
            
        self.combo_mode = flags.combo_method()
            
        super().__init__(xlims, ylims, flags, data, ftype, fname_formats=fname_formats, h5_location=h5_location,
                            source_override=source_override, label=label, 
                            further_processing=further_processing, base_drop_vars=base_drop_vars)
        if self.sources != None and len(self.sources) == 1 and self.data == 'vel':
            self.label += "_" + self.sources[0][0]
        
        


    def get_velocity_fname(self, year, target_source=None):
        #if target_source != None and len(self.sources) != 1:
        return 'velocities/' + str(year) + "_" + self.label + "_v." + self.ftype
        #return 'velocities/' + str(year) + self.label + "_v." + self.ftype
        

    def get_tif_velocity_fname(self, year, target_source=None):
        
        #if target_source != None and len(self.sources) != 1:
        return 'velocities/' + str(year) + "_" + self.label + "_v." + self.ftype
        #return 'velocities/' + str(year) + self.label + "_v.tif"
        

        
    def build_velocity_files(self, rebuild=True):
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

        progress = LoadingBar()
        print("Opening " + ", ".join(self.sources) + " data.")
        self.get_tif_data(base=True)

        for x in list(range(self.yearStart, self.yearEnd+1)):
            if not os.path.exists(self.get_velocity_fname(x) or rebuild):

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

                    self.generate_image(tif_to_save, self.get_tif_velocity_fname(x), self.plotter.plot_velocity, x)

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
            
        '''self.file = xr.concat(self.file, dim=years_found)
        self.file = self.file.rename({'concat_dim': 'year'})'''
        
        return self.file

    def build_files(self):
        self.build_velocity_files()


    def fnames(self, data_override=None):
        if data_override == None:
            data = self.data
        else:
            data = data_override

        fname_data = {
            'ItsLive': self.get_velocity_fname,
            'Measures': self.get_velocity_fname,
        }
        year_offset = {
            'ItsLive': 1,
            'Measures': 6,

        }
        fname_prefix = {
            'vel': OUTPUT,
            'velx': OUTPUT,
            'vely': OUTPUT,
        }

        fnames = []
        found_years = []
        sources = []
        print(self.sources)
        for s in self.sources:
            for year in range(self.yearStart, self.yearEnd):
                location = fname_data[s]

                f = fname_prefix[data] + location(year, target_source=s)
                print(f)
                if not Path(f).is_file():
                    continue

                fnames.append(f)
                found_years.append(datetime.datetime(year, year_offset[s], 1))
                sources.append(s)


        return fnames, found_years, sources
    


class ElevationManager(FileManager):

    def __init__(self, xlims, ylims, flags, data,
                 source_override = False, label='',  sources = None):
        
        further_processing = VELOCITY_SPECIAL_PREP[None]
        base_drop_vars = []
        ftype = 'gpkg'



            
        super().__init__(xlims, ylims, flags, data, ftype,
                            source_override=source_override, label=label, 
                            further_processing=further_processing, base_drop_vars=base_drop_vars)
        
        if data== 'elev':
            self.sample_source = gpd.read_file(INPUT + 'elevation/ATL11_trends_APS.gpkg')
        
        
        if data == 'evel' and sources == None:
            self.sources = 'IceSAT2'
        elif data == 'rema':
            ftype='tif'
            self.sources = 'REMAPrev'
        elif data == 'remaraw':
            ftype='tif'
            self.sources = 'REMA'
    
        

    def get_elevation_fname(self, year):
        return  'elevation/' + str(year) + "_e." + self.ftype
        
    def get_tif_elevation_fname(self, year):
        return  'elevation/' + str(year) + "_e.tif"
        
        
        

    def get_interpolated_elevation_fname(self, year):
        return  'elevation/' + str(year) + "_e." + self.ftype
        

    def get_rema_fname(self, year):
        return  'rema/' + str(year) + "_r." + self.ftype
    
    def get_rema_raw_fname(self, year):
        return 'rema/raw/' + str(year) + "/"
    

    def get_ouput_files(self):
        super().get_ouput_files()

        #self.file = self.file.rename(columns={'elevation': 'elev', 'elevation_yerr': 'elev_yerr'})
        
        new_dates = []
        if len(self.file) == 0:
            return self.file
        for x in self.file['date']:
            try:
                new_dates.append(datetime.datetime(year=int(x), day=1, month=1).replace(hour=0, second=0, minute=0))
            except ValueError:
                new_dates.append(np.datetime64(x).item().replace(hour=0, second=0, minute=0))

        self.file['date'] = new_dates
        return self.file


    def build_files(self):
        
        if self.data == 'elev':
            self.build_elevation_files()
        
        elif self.data == 'rema':
            self.build_rema_files()
        
        elif self.data == 'rawrema':
            self.build_raw_rema_files()


    def get_point_data(self, p):
        f, years, sources = self.fnames('remaraw')

        found_files = []
        found_years = []
        found_sources = []
        found_err = []
        


        for i, f in enumerate(f):
            cur = xr.open_dataset(f)
            df = cur.sel(x=p[1], y=p[0], method='nearest').squeeze()

            if np.isnan(df['band_data'].values) or df['band_data'].values == 0:
                continue

            found_files.append(df['band_data'].values)
            found_years.append(years[i])
            found_sources.append('Coregistered REMA')


        dataset = {'time': found_years,
                           'sources': found_sources,
                           'elev': found_files}
        if len(found_err) != 0:
            dataset[['elev_yerr']] = found_err



        df = pd.DataFrame(dataset)
        
        return df



    def fnames(self, data_override=None):
        if data_override == None:
            data = self.data
        else:
            data = data_override

        fname_data = {
            'elev': self.get_elevation_fname,
            'rema': self.get_rema_fname,
            'remaraw': self.get_rema_raw_fname
        }
        fname_prefix = {
            'elev': OUTPUT,
            'rema': OUTPUT,
            'remaraw': INPUT
        }

        fnames = []
        found_years = []
        sources = []

        for year in range(self.yearStart, self.yearEnd):
            location = fname_data[data]

            if data == 'remaraw':
                f = fname_prefix[data] + location(year)
                if not Path(f).is_dir():
                    continue 
                # DOING REMA SHENANIGANS

                new_names = os.listdir(f)

                for year_folder in new_names:
                    cur_folder = f + year_folder + '/'

                    if Path(cur_folder).is_dir():
                        file_options = os.listdir(cur_folder)

                        for final_files in file_options:
                            if final_files.split('.')[-1] == 'tif':
                                fnames.append(cur_folder + final_files)
                                fname_date = final_files.split('_')[3]
                                dt = datetime.datetime(int(fname_date[:4]), int(fname_date[4:6]), int(fname_date[6:8]))

                                found_years.append(dt)
                                sources.append(self.sources)

            elif data == 'elev':
                f = fname_prefix[data] + location(year)
                if not Path(f).is_file():
                    continue
                fnames.append(f)
                found_years.append(year)
                sources.append(self.sources)

        return fnames, found_years, sources
    



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
            self.file[np.datetime64(str(c))] = pd.DataFrame(columns=['latitude', 'longitude', 'date', 'geometry'])

        cur_track = 0
        max = len(D11)
        progress.load_bar(cur_track, max)
        
        cur_track = 0
        max = len(D11)
        progress.load_bar(cur_track, max)
        for track in D11:
        
            dates = (track['delta_time'].astype('timedelta64[s]') + np.datetime64("2018-01-01T00:00")).astype('M8[Y]')
            track['latitude'] = np.transpose([track['latitude']] * len(track['h_corr'][0]))
            track['longitude'] = np.transpose([track['longitude']] * len(track['h_corr'][0]))
            track['datetime'] = (track['delta_time'].astype('timedelta64[s]') + np.datetime64("2018-01-01T00:00")).astype(str)

            for c in self.file.keys():
                df = pd.DataFrame({'latitude': track['latitude'][dates == c].flatten(),
                                    'longitude': track['longitude'][dates == c].flatten(), 
                                    'elev': track['h_corr'][dates == c].flatten(),
                                    'elev_yerr': track['h_corr_sigma'][dates == c].flatten(),
                                    'date': track['datetime'][dates == c].flatten()})
                df['geometry'] = df.apply(pointify, axis=1)
                self.file[c] = pd.concat([self.file[c], df])
            
            cur_track += 1
            progress.load_bar(cur_track, max)

            
        for c in self.file.keys():
            #print(gpd.GeoDataFrame(self.file[np.datetime64(str(c))]))
            if not len(self.file[c]):
                continue
            
            self.chack_valid_path(OUTPUT + self.get_elevation_fname(c))
            gdf_final = gpd.GeoDataFrame(self.file[c], geometry='geometry', crs='EPSG:4326')
            gdf_final.to_crs('EPSG:3031')
            gdf_final.to_file(OUTPUT + self.get_elevation_fname(c), driver='GPKG')

            to_tif = make_geocube(
                vector_data=gdf_final,
                measurements=["elev"],

                resolution=(-0.1, 0.1),
                rasterize_function=rasterize_image,
            )
            print(TIF_LOCATION + self.get_tif_elevation_fname(c))
            to_tif['elev'].rio.to_raster(TIF_LOCATION + self.get_tif_elevation_fname(c))


            #self.generate_image(to_tif["elev"], TIF_LOCATION + self.get_tif_elevation_fname(cur_track))



    def apply_rate_(self, ref_file, rate_fname, floating, to_build=2011):
        # TODO: make this not suck
        progress = LoadingBar()
        start_year = max(2010, self.yearStart-1)

        factor = 1

        if floating:
            factor = 0.1

        
        offset = xr.open_dataset(rate_fname)
        lat = []
        lon = []
        new_vals = []
        j = 0

        for i, r in ref_file.iterrows():
            j += 1
            try:
                offset_found = offset.sel(x=r['geometry'].x, y=r['geometry'].y, method="nearest", tolerance=50).squeeze()
            except Exception as e:
                continue

            offset_found = offset_found['band_data']  * (to_build-start_year) * factor
            

            
            new_vals.append((float(r['elev']) + float((offset_found))))
            lat.append(r['latitude'])
            lon.append(r['longitude'])

            progress.load_bar(j, len(ref_file))


        dates = [str(np.datetime64(str(to_build)))] * len(new_vals)

        return lat, lon, new_vals, dates



    def build_supplementary_files(self, to_build=2009):

        ref_year = 2019
        if not np.datetime64(str(ref_year)) in self.file.keys():
            self.file[np.datetime64(str(ref_year))] = gpd.read_file(TIF_LOCATION + self.get_elevation_fname(ref_year))
        ref_file = self.file[np.datetime64(str(ref_year))].copy(deep=True)
        ref_file = ref_file.sort_values(by='date')
        ref_file.drop_duplicates()

        lat_g, lon_g, new_vals_g, dates_g = self.apply_rate_(ref_file, ICESAT1_ELEVATION_RATE, False, to_build=to_build)
        lat_f, lon_f, new_vals_f, dates_f = self.apply_rate_(ref_file, ICESAT1_ELEVATION_RATE_FLOATING, True, to_build=to_build)

        lat = lat_g + lat_f
        lon = lon_g + lon_f
        new_vals = new_vals_g + new_vals_f
        dates = dates_g + dates_f

        df = pd.DataFrame({'latitude': lat,
                            'longitude': lon, 
                            'elev': new_vals,
                            'date': dates})
        df['geometry']  = df.apply(pointify, axis=1)
        self.chack_valid_path(OUTPUT + self.get_elevation_fname(to_build))
        df = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
        df.to_file(OUTPUT + self.get_elevation_fname(to_build), driver='GPKG')
        
        df = df.dropna()
        self.file[np.datetime64(str(to_build))] = df

        out_grid = make_geocube(
            vector_data=self.file[np.datetime64(str(to_build))],
            measurements=["elev"],
            resolution=(-0.001, 0.001), 
            output_crs=self.file[np.datetime64(str(to_build))].crs 
        )


        out_grid["elev"].rio.to_raster(TIF_LOCATION + self.get_tif_elevation_fname(to_build))


        os.makedirs(TIF_LOCATION +'reprojected/' + '/'.join(self.get_tif_elevation_fname(to_build).split('/')[:-1]), exist_ok=True)
        gdal.Warp(TIF_LOCATION +'reprojected/' + self.get_tif_elevation_fname(to_build), 
                    TIF_LOCATION + self.get_tif_elevation_fname(to_build),
                    dstSRS='EPSG:3031')
        

        #self.generate_image(False, self.get_tif_elevation_fname(to_build), self.plotter.plot_elevation, to_build, reprojected=True)

        



    def build_rema_files(self):
        for x in list(range(self.yearStart, self.yearEnd+1)):
            self.generate_image(False, self.get_rema_fname(x), self.plotter.plot_rema_coverage, x, )

    def build_raw_rema_files(self):
        for x in list(range(self.yearStart, self.yearEnd+1)):
            self.generate_image(False, self.get_rema_raw_fname(x), self.plotter.plot_raw_rema_data, x, )



class GravimetryManager(FileManager):

    def __init__(self, xlims, ylims, flags, data, label=''):
        
        ftype='tif'
        super().__init__(xlims, ylims, flags, data, ftype,label=label)
        
    

    def build_files(self):
        return
    


    def fnames(self, data_override=None):
        if data_override == None:
            data = self.data
        else:
            data = data_override
        return [GRAV_LOCATION], [], []



class BedmapManager(FileManager):

    def __init__(self, xlims, ylims, flags, data, label=''):
        
        ftype='tif'
        super().__init__(xlims, ylims, flags, data, ftype,label=label)
        
    

    def build_files(self):
        return
    


    def fnames(self, data_override=None):
        if data_override == None:
            data = self.data
        else:
            data = data_override
        return [BEDMAP_FILE], [], []





class GeoidManager(FileManager):

    def __init__(self, xlims, ylims, flags, data, label=''):
        
        ftype='tif'
        super().__init__(xlims, ylims, flags, data, ftype,label=label)
        
    

    def build_files(self):
        return
    


    def fnames(self, data_override=None):
        if data_override == None:
            data = self.data
        else:
            data = data_override
        return [SEA_LEVEL_TIF], [], []



class REMATileManager(FileManager):

    def __init__(self, xlims, ylims, flags, data, label=''):
        
        ftype='tif'
        super().__init__(xlims, ylims, flags, data, ftype,label=label)
        
    

    def build_files(self):
        return
    


    def fnames(self, data_override=None):
        if data_override == None:
            data = self.data
        else:
            data = data_override
        return [REMA_TILE_DEM], [], []


class IPRManager(FileManager):

    def __init__(self, xlims, ylims, flags, data, label='', corrected=False):
        
        ftype='csv'
        super().__init__(xlims, ylims, flags, data, ftype,label=label)
        self.gpkg_source = "Open Polar Radar, 2024"
        self.corrected = corrected
        
    

    def build_files(self):
        return

    
    


    def fnames(self, data_override=None):
        if self.corrected:
            return [ADJUSTED_IPR], [], []
        return [IPR_GPKG_LOCATION], [], []


class FirnAirManager(FileManager):

    def __init__(self, xlims, ylims, flags, data, label='', source=0):
        
        ftype='csv'
        super().__init__(xlims, ylims, flags, data, ftype,label=label)

        self.start_band_year = [1950, 2015, 2015]

        self.source_firn_file = [HISTORIC_FIRN_TIF, SSP585_FIRN_TIF, SSP126_FIRN_TIF]
        self.tif_source = ["Historic (Veldhuijsen, 2024)", "SSP585 (Veldhuijsen, 2024)", "SSP126 (Veldhuijsen, 2024)"]
        self.source = source
        
    

    def build_files(self):
        return self.build_firn_files()

    def get_firn_fname(self, year):
        source_label = self.source_firn_file[self.source].split('/')[-1].split('.')[0]
        return OUTPUT + 'firn_air/' + str(year) + "_" + self.label + "_" + source_label + ".tif"

    
    def build_firn_files(self):
        '''
        splits firn file into years with each band of the image being a year offset from the last.


        Parameters
        ----------
        None

        Returns
        -------
        String[]
            list of the generated data files
        '''

        for x in range(self.yearStart, self.yearEnd):
            if x - self.start_band_year[self.source] + 1 < 0:
                pass
            try:
                gdal.Translate(self.get_firn_fname(x), self.source_firn_file[self.source], bandList=[x - self.start_band_year[self.source] + 1])
            except RuntimeError as e:
                print("No firn air data for " + self.tif_source[self.source] + " at year " + str(x))
                print(e)
                

        
        self.close()


    def fnames(self):

        fnames = []
        found_years = []
        sources = []
        for year in range(self.yearStart, self.yearEnd):
            f = self.get_firn_fname(year)
            
            if not Path(f).is_file():
                continue

            fnames.append(f)
            found_years.append(datetime.datetime(year, 1, 1))
            sources.append(self.tif_source[self.source])
            
        return fnames, found_years, sources
    
class SMBManager(FileManager):

    def __init__(self, xlims, ylims, flags, data, label=''):
        
        ftype='csv'
        super().__init__(xlims, ylims, flags, data, ftype,label=label)

        self.start_band_time = datetime.datetime(1979, 1, 16)
        self.band_steps = relativedelta(month=1)

        self.source_file = SMB_FILE_LOCATION
        self.mask_file = SMB_FILE_LOCATION
        self.area_file = SMB_FILE_LOCATION
        self.tif_source = "RACMO SMB"
        self.crs_wkt = """GEOGCRS["Rotated_pole",BASEGEOGCRS["WGS 84",DATUM["World Geodetic System 1984",ELLIPSOID["WGS 84",6378137,298.257223563,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4326]],DERIVINGCONVERSION["Pole rotation (netCDF CF convention)",METHOD["Pole rotation (netCDF CF convention)"],PARAMETER["Grid north pole latitude (netCDF CF convention)",-185,ANGLEUNIT["degree",0.0174532925199433,ID["EPSG",9122]]],PARAMETER["Grid north pole longitude (netCDF CF convention)",-160,ANGLEUNIT["degree",0.0174532925199433,ID["EPSG",9122]]],PARAMETER["North pole grid longitude (netCDF CF convention)",0,ANGLEUNIT["degree",0.0174532925199433,ID["EPSG",9122]]]],CS[ellipsoidal,2],AXIS["geodetic latitude (Lat)",north,ORDER[1],ANGLEUNIT["degree",0.0174532925199433,ID["EPSG",9122]]],AXIS["geodetic longitude (Lon)",east,ORDER[2],ANGLEUNIT["degree",0.0174532925199433,ID["EPSG",9122]]]]"""
        
        
    

    def build_files(self):
        return self.build_smb_files()

    def get_smb_fname(self, date):
        return OUTPUT + 'smb/' + str(date) + "_" + self.label + ".tif"

    def get_temp_fname(self):
        return OUTPUT + 'smb/temp.tif'

    
    def build_smb_files(self):
        '''
        splits firn file into years with each band of the image being a year offset from the last.


        Parameters
        ----------
        None

        Returns
        -------
        String[]
            list of the generated data files
        '''
        dates = []
        sums = []
        year_dates = []
        year_sums = []
        mask = rioxarray.open_rasterio(SMB_MASK_LOCATION)
        area = rioxarray.open_rasterio(SMB_AREA_LOCATION)
        
        #mask["spatial_ref"] = xr.DataArray(0, attrs={"crs_wkt": self.crs_wkt, "spatial_ref": self.crs_wkt})
        #mask.attrs["grid_mapping"] = "spatial_ref"

        #area["spatial_ref"] = xr.DataArray(0, attrs={"crs_wkt": self.crs_wkt, "spatial_ref": self.crs_wkt})
        #area.attrs["grid_mapping"] = "spatial_ref"
        print(mask.variable)
        print(area.variable)

        mask *= (area * 1000000) # convert km2 to m2 and multiplty it w mask
        

        for x in range(self.yearStart, self.yearEnd):
            cur_smb = 0
            
            for m in range(1, 13):
                if ((((x * 12) + m) - (self.start_band_time.year * 12))) < 0:
                    pass
                try:
                    self.get_temp_fname()
                    fname = self.get_smb_fname(datetime.datetime(x, m, self.start_band_time.day))
                    gdal.Translate( self.get_temp_fname(), self.source_file, bandList=[(((x * 12) + m) - (self.start_band_time.year * 12))])
                    cur = rioxarray.open_rasterio(self.get_temp_fname(), masked=True)

                    cur["spatial_ref"] = xr.DataArray(0, attrs={"crs_wkt": self.crs_wkt, "spatial_ref": self.crs_wkt})
                    cur.attrs["grid_mapping"] = "spatial_ref"

                    print()
                    print()
                    print()
                    cur.values *= mask

                    cur = cur.rio.write_crs(self.crs_wkt)
                    '''cur = cur.rio.reproject(dst_crs="epsg:3031")
                    print(np.nansum(cur.values))'''
                    
                    cur.rio.to_raster(fname)


                    sum_smb = self.get_zonal_data(self.get_smb_fname(datetime.datetime(x, m, self.start_band_time.day)), 'dibble_large_basins')['sum'] * (1/1e12)
                    sum_smb = self.get_zonal_data(self.get_smb_fname(datetime.datetime(x, m, self.start_band_time.day)), 'dibblebasins')['sum'] * (1/1e12)
                    sums.append(sum_smb * 12)
                    print(sum_smb)

                    cur_smb += sum_smb
                    dates.append(datetime.datetime(x, m, self.start_band_time.day))
                except RuntimeError as e:
                    print("No SMB data for " + self.tif_source + " at datetime " + str(datetime.datetime(x, m, self.start_band_time.day)))
                    print(e)
            year_sums.append(cur_smb)
            print(cur_smb)
            year_dates.append(datetime.datetime(x, 6, self.start_band_time.day))


        plt.plot(dates, np.array(sums), label='Monthly')
        plt.plot(year_dates, np.array(year_sums), label='Yearly')
        plt.legend()
        plt.xlabel('Date')
        plt.ylabel('Sum Surface Mass Balance for Basin (GT/yr)')
        plt.savefig('SMBs.png')

        print("Mean (GT/yr): ", np.mean(sums))
        print("Std. Dev. (GT/yr): ", np.std(sums))
        print("Median (GT/yr): ", np.median(sums))
        
        self.close()

    def get_surface_balance_df(self, yearly=True):
        dates = []
        sums = []
        year_dates = []
        year_sums = []

        for x in range(self.yearStart, self.yearEnd):
            cur_smb = 0
            
            for m in range(1, 13):
                if ((((x * 12) + m) - (self.start_band_time.year * 12))) < 0:
                    pass
                try:
                    fname = self.get_smb_fname(datetime.datetime(x, m, self.start_band_time.day))
                    cur = rioxarray.open_rasterio(fname, masked=True)

                    cur = cur.rio.write_crs(self.crs_wkt)
                    
                    cur.rio.to_raster(fname)
                    sum_smb = self.get_zonal_data(self.get_smb_fname(datetime.datetime(x, m, self.start_band_time.day)), 'dibble_large_basins')['sum'] * (1/1e12)
                    sum_smb = self.get_zonal_data(self.get_smb_fname(datetime.datetime(x, m, self.start_band_time.day)), 'dibblebasins')['sum'] * (1/1e12)
                    sums.append(sum_smb * 12)
                    print(sum_smb)

                    cur_smb += sum_smb
                    dates.append(datetime.datetime(x, m, self.start_band_time.day))
                except RuntimeError as e:
                    print("No SMB data for " + self.tif_source + " at datetime " + str(datetime.datetime(x, m, self.start_band_time.day)))
                    print(e)
            year_sums.append(cur_smb)
            print(cur_smb)
            year_dates.append(datetime.datetime(x, 6, self.start_band_time.day))


        plt.plot(dates, np.array(sums), label='Monthly')
        plt.plot(year_dates, np.array(year_sums), label='Yearly')
        plt.legend()
        plt.xlabel('Date')
        plt.ylabel('Sum Surface Mass Balance for Basin (GT/yr)')
        plt.savefig('SMBs.png')


        if yearly:
            df = pd.DataFrame(
            {
                "smb": year_sums,
                "dt": year_dates,
            })
        else:
            df = pd.DataFrame(
            {
                "smb": sums,
                "dt": dates,
            })

        return df

        
        

    def get_zonal_data(self, fname, mask):
        '''
        dataset = rs.open(fname)
        arr = dataset.read(1)
        affine=dataset.transform

        zone = gpd.read_file(SHAPEFILES[mask])
        if zone.crs is None:
            zone = zone.set_crs('EPSG:3031')

        zone = zone.to_crs(self.crs_wkt)
        stats = zonal_stats(zone, arr, affine=affine,
                            stats=['sum', 'count'], all_touched=True)
        print(stats)
        return stats[0]
    '''

        zone = gpd.read_file(SHAPEFILES[mask])
        if zone.crs is None:
            zone = zone.set_crs('EPSG:3031')

        zone = zone.to_crs(self.crs_wkt)
        raster = rs.open(fname)
        stats = exact_extract(raster, zone, ['count', 'sum'])

        print(stats)

        return stats[0]['properties']

    def fnames(self):

        fnames = []
        found_years = []
        sources = []

        for x in range(self.yearStart, self.yearEnd):
            for m in range(1, 13):
                f = self.get_smb_fname(datetime.datetime(x, m, self.start_band_time.day))
                if not Path(f).is_file():
                    continue

                fnames.append(f)
                found_years.append(datetime.datetime(x, m, self.start_band_time.day))
                sources.append(self.tif_source)

            
        return fnames, found_years, sources
