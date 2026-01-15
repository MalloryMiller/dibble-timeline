
'''

Nearly all of this was written by David Lilien

'''


import matplotlib.pyplot as plt
from pathlib import Path
import sys
from PIL import Image
import os
import numpy as np
import colorsys as cs
import glob
from shapely.geometry import Point
import pandas as pd
import geopandas as gpd
import warnings
import tqdm
import shapefile as shp
import matplotlib.colors as colors
from matplotlib.lines import Line2D
import h5py


fname = 'input/elevation'#/ATL11_054410_0326_006_12.h5'

gpgk_folder_name = 'output'



def ATL11_to_dict(filename, attrs):
    """
        Read selected datasets from an ATL06 file
        Input arguments:
            filename: ATL11 file to read
            dataset_dict: A dictinary describing the fields to be read
                    keys give the group names to be read,
                    entries are lists of datasets within the groups
        Output argument:
            D11: dictionary containing ATL11 data.  Each dataset in
                dataset_dict has its own entry in D6.  Each dataset
                in D6 contains a list of numpy arrays containing the
                data
    """

    D11=[]
    pairs=[1, 2, 3]
    # open the HDF5 file
    with h5py.File(filename) as h5f:
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
    return D11
    
    
    


def pointify(row):
    return Point(row['longitude'],row['latitude'])


def ATL11_2_gdf(ATL11_fn, attrs):
    """
    function to convert ATL11 hdf5 to geopandas dataframe, containing columns as passed in dataset dict
    """
    if 'latitude' not in attrs:
        attrs.append('latitude')
    if 'longitude' not in attrs:
        attrs.append('longitude')
    #use Ben's Scripts to convert to dict
    
    data_dict = ATL11_to_dict(ATL11_fn, attrs)
    #this will give us 6 tracks
    i = 0
    for track in data_dict:
        #1 track
        #convert to datafrmae
        df = pd.DataFrame(track)
        df['geometry'] = df.apply(pointify, axis=1)
        if i==0:
            df_final = df.copy()
        else:
            df_final = df_final.append(df)
        i = i+1
    gdf_final = gpd.GeoDataFrame(df_final, geometry='geometry', crs='EPSG:4326')
    return gdf_final
    


def trend(times, values, uncert=None):
    trends = np.zeros((times.shape[0]))
    for i in range(times.shape[0]):
        t = times[i, ~np.isnan(times[i, :])] / (365.25 * 24.0 * 60 * 60)
        print(t)
        A = np.vstack((np.ones_like(t), t)).T
        b = values[i, ~np.isnan(times[i, :])]
        if uncert is not None:
            A *= uncert[i, ~np.isnan(times[i, :])] ** 2.0
            b *= uncert[i, ~np.isnan(times[i, :])] ** 2.0
        trends[i] = np.linalg.lstsq(A, b)[0][1]
    return trends


def ATL11_to_trend_GDF(fn):
    attrs = ['h_corr', 'latitude', 'longitude', 'delta_time', 'h_corr_sigma'] 
    data_dict = ATL11_to_dict(fn, attrs)
    i = 0
    for track in data_dict:
        trendv = trend(track['delta_time'], track['h_corr'])
        uncert = np.sqrt(np.nansum(track['h_corr_sigma'] ** 2.0, axis=1) / np.sum(~np.isnan(track['h_corr_sigma']), axis=1))
        dates = np.nanmean(track['delta_time'], axis=1).astype('timedelta64[s]') + np.datetime64("2018-01-01T00:00")
        df = pd.DataFrame({'latitude': track['latitude'], 'longitude': track['longitude'], 'trend': trendv, 'date': dates, 'uncert': uncert})
        df['geometry'] = df.apply(pointify, axis=1)
        if i==0:
            df_final = df.copy()
        else:
            df_final = pd.concat([df_final, df])
        i = i+1
    gdf_final = gpd.GeoDataFrame(df_final, geometry='geometry', crs='EPSG:4326')
    return gdf_final
    
    
    
    

all_files = sorted(glob.glob(fname+'/*.h5'))


def generate_gpkg_name(fn):
    Path(gpgk_folder_name+ '/' + fn.split('/')[0]).mkdir(exist_ok=True)
    return gpgk_folder_name + '/' + fn[:-4] + '.gpkg'


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for fn in tqdm.tqdm(all_files):
        gdf = ATL11_to_trend_GDF(fn)
        #gdf = gdf.clip(bb).to_crs('EPSG:3348')
        try:
            gdf.to_file(generate_gpkg_name(fn), driver='GPKG')
        except ValueError:
            print("Value Error")
            pass
        if fn == all_files[0]:
            gdf1 = gdf.copy()
        else:
            gdf1 = pd.concat([gdf1, gdf])


    

gdf_out = pd.concat([gpd.read_file(generate_gpkg_name(fn)) for fn in all_files])
print("Output Concated")


gdf_out.to_file(fname + 'ATL11_trends_weighted.gpkg', driver='GPKG')
print("Trends gpkg saved")

