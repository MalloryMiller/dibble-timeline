from utils import *
from pathlib import Path
import numpy as np


from scipy.interpolate import RegularGridInterpolator
import rioxarray # used by xarray for some reason, must be first
import xarray as xr


class FileManager:
    def __init__(self, minlat, maxlat, minlon, maxlon, sources, combo_mode,
                 yearStart, yearEnd, fname_formats = VEL_FILE_FORMATS, 
                 further_processing = drop_unnecessary_for_v,
                 base_drop_vars = ['STDX', 'STDY', #'ERRX', 'ERRY',
                                    'mapping', 'landice', 
                                    'vx_error', 'vy_error', #'v_error',
                                    'coord_system'],
                                    source_override = False):
        
        self.minlat =  minlat
        self.maxlat =  maxlat
        self.minlon =  minlon
        self.maxlon =  maxlon

        self.fname_format = fname_formats
        self.sources = sources
        self.combo_mode = combo_mode

        self.yearStart = yearStart
        self.yearEnd = yearEnd
        self.drop_variables = base_drop_vars

        self.special_prep = further_processing


        self.source_override = source_override


        if self.source_override:
            self.sample_source = self.source_override.sample_source
            self.sample_file = self.source_override.sample_file

        else:
            self.sample_source = self.sources[0]
            self.sample_file = SOURCE_SAMPLE_FILES[self.sample_source]

        
        

        self.file = []



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
        
        


    def open(self):
        '''
        Opens all files from all sources in a range of years (self.yearStart through self.yearEnd inclusively)
        places relevant information from sourcs into self.file, one dataset where all other files have been concatonated
        along the new year dimension.


        Parameters
        ----------
        None

        Returns
        -------
        xarray.Dataset
            Processed dataset with columns TODO
        '''
        
        self.close()

        years_found = []
        progress = LoadingBar()
        print("Opening " + ", ".join(self.sources) + " data.")
        self.get_data(base=True)

        for x in list(range(self.yearStart, self.yearEnd+1)):

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
                to_add = [self.get_data()]
                has_data = True

                if "ItsLive" in found and "ItsLive" != self.sample_source:

                    ygrid, xgrid = np.meshgrid(to_add[0].y.values, to_add[0].x.values)
                    vel = RegularGridInterpolator((found['ItsLive'].y.values, found['ItsLive'].x.values), 
                                                  found['ItsLive'].velocity.values, method='linear')
                    
                    #print(len(to_add[0].y.values), len(to_add[0].x.values))
                    #print(len(found['ItsLive'].y.values), len(found['ItsLive'].x.values))
                    
                    
                    vel = vel((ygrid, xgrid))
                    vel = xr.DataArray(vel, 
                                        coords={'x': to_add[0].x.values, 'y': to_add[0].y.values},
                                        dims=['x', 'y'])


                    c = RegularGridInterpolator((found['ItsLive'].y.values, found['ItsLive'].x.values), 
                                                found['ItsLive'].v_error.values, method='linear')
                    c = c((ygrid, xgrid))
                    c = xr.DataArray(c, 
                                    coords={'x': to_add[0].x.values, 'y': to_add[0].y.values},
                                    dims=['x', 'y'])
                        
                    
                    if "Measures" in found and has_data:

                        if self.combo_mode == "weighted":

                            to_add[0]['velocity'] = ((found["Measures"].velocity * found["Measures"].v_error) + (vel * c)) / (found["Measures"].v_error + c)
                            to_add[0]['v_error'] = found["Measures"].v_error + c


                        elif self.combo_mode == "average":

                            to_add[0]['velocity'] = (found["Measures"].velocity + vel) / 2
                            to_add[0]['v_error'] = found["Measures"].v_error + c


                        elif self.combo_mode == 'offset':

                            to_add[0]['velocity'] = found["Measures"].velocity
                            to_add[0]['v_error'] = found["Measures"].v_error

                            to_add.append(self.get_data())

                            to_add[1]['velocity'] = vel
                            to_add[1]['v_error'] = c




                    elif "Measures" in found and "ItsLive" not in found and not has_data:
                        to_add[0]['velocity'] = found["Measures"].velocity
                        to_add[0]['v_error'] = found["Measures"].v_error
                    elif not has_data:
                        continue
                    else:
                        to_add[0]['velocity'] = vel
                        to_add[0]['v_error'] = c

                elif "ItsLive" != self.sample_source:
                    to_add = [found["Measures"]]
                else: 
                    to_add = [found["ItsLive"]]



                self.file.extend(to_add)

                if self.combo_mode == 'offset':
                    cur_years = []
                    if "Measures" in found:
                        cur_years.append(x)
                    if "ItsLive" in found:
                        cur_years.append(x+.5)
                else:
                    cur_years = [x]
                years_found.extend(cur_years)
                
            progress.load_bar(x - self.yearStart, self.yearEnd - self.yearStart)
            
        self.file = xr.concat(self.file, dim=years_found)
        self.file = self.file.rename({'concat_dim': 'year'})

        return self.file







    def close(self):
        '''
        Resets the current file to hold nothing.
        '''
        self.file = []

