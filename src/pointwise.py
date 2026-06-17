import datetime
from utils import *
from file_manager import GravimetryManager, ElevationManager, VelocityManager, IPRManager, FirnAirManager, REMATileManager

import geopandas as gpd
import rioxarray # used by xarray for some reason, must be first
import xarray as xr
from shapely.geometry import Point
import pandas as pd
import numpy as np
from matplotlib import cm
import matplotlib.colors as mcolors
import matplotlib as mpl
import matplotlib.dates as mdates
from photutils.aperture import CircularAperture
import itertools


from plotting import Plotting

class Pointwize():
    def __init__(self, flags, xlim, ylim, points, data, change=True, time_diff_year = 2020, cmap='managua'):
        self.flags = flags
        self.xlim = xlim
        self.ylim = ylim
        if 'point_labels' in points.keys():
            self.title = '-'.join(points['point_labels'])
            self.trend_adjustment = points['trend_adjustment']
        else:
            self.title = ''
            self.trend_adjustment = 0
        self.points = points['point']
        print(points)

        if type(self.points) ==list and type(self.points[0]) == list:
            temp = [str(self.points[0][0]), str(self.points[0][1])]
        else:
            temp = [str(self.points[0]), str(self.points[1])]
        self.point_label = '_'.join(temp)

        self.data = data
        self.change = change
        self.time_diff_year = time_diff_year
        self.labels = []


        self.max_dist = 100
        self.label_type = flags.label_type()


        if points['type'] == 'fl':
            self.pt_range = points['point_range']
            self.point_spacing = points['point_spacing']
            
            s = StreamFlow(xlim, ylim, flags, self.points, self.point_spacing, self.pt_range, max_dist=self.max_dist, label_type = self.label_type)

        elif points['type'] == 'l':
            labels = points['labels']
            s = PointSeries(xlim, ylim, flags, self.points, labels) 

        elif points['type'] == 'pl':
            pt_cnt = points['point_spacing']
            s = PolyLine(xlim, ylim, flags, self.points, points['point_labels'], pt_cnt, fname=points['fname'] + "_" + points['point_labels'][0]) 

        
        e = ElevationManager(xlim, ylim, flags, 'elev')
        if self.data == 'gl':
            self.points, self.labels, self.fl = s.get_points(e.sample_source, include_all=True)
        else:
            self.points, self.labels = s.get_points(e.sample_source)
                
        if type(self.labels[0]) == int or type(self.labels[0]) == float:
            max_dist = max(max(self.labels), -min(self.labels))
        else:
            max_dist = len(self.labels) // 2
        self.norm = mcolors.Normalize(vmin=-max_dist, vmax=max_dist)
        self.cmap = cmap
        self.cm = cm.get_cmap(cmap, 256)

        self.point_df = None
        self.results = {}

    def create_point_df(self, pointls=None):
        if pointls == None:
            pointls = self.points

        point_geom = []
        for p in pointls:
            if type(p) == list:
                point_geom.append(Point(p[1], p[0]))
            else:
                point_geom.append(p)

        df_ref = pd.DataFrame({'geometry':point_geom})
        df_ref = gpd.GeoDataFrame(df_ref, geometry=point_geom, crs='EPSG:3031')
        if len(pointls) > 1:
            df_ref.to_file(POINTWISE_OUTPUT_LOCATION + str(self.point_label) + ".gpkg", layer="geometry", driver="GPKG")
        return df_ref
    
    
    def get_label(self, index, style=None):
        if style == None:
            style = self.label_type


        if type(index) != int:
            return ''
        if style == 'date':
            return str(round(float(self.labels[index]))) + ' years'
        if style == 'dist':
            return str(round(self.labels[index] / 1000, 1)) + ' km'

        
        return str(chr(index + 65))


    def save_point_df(self):
        p = Plotting()
        df = self.create_point_df()
        labels = []
        for x in range(len(self.points)):
            labels.append(self.get_label(x))
        df['labels'] = labels

        
        p.plot_df_on_borders(df, self.cm, self.norm, self.labels, POINTWISE_OUTPUT_LOCATION + str(self.point_label) + "_locations.png")



    def get_gl_set(self, fname = GL_GPKG_InSAR, date_cols=['Date_4', 'Date_1', 'Date_2', 'Date_3'], source_label='Rignot, 2026'):
        layers = len(gpd.list_layers(fname))
        '''if layers >1:
            gdf = gpd.read_file(fname, layer="gl")
        else:'''
        
        gdf = gpd.read_file(fname)
        

        if 'lat' in gdf.columns:
            gdf = gdf.drop(columns=['lat', 'lon'])
        
        gdf = gdf.to_crs(3031)

        gdf['date'] = gdf[date_cols].mean(axis=1)
        gdf['gl_xerr_min'] = gdf['date'] - gdf[date_cols].min(axis=1)
        gdf['gl_xerr_max'] = gdf[date_cols].max(axis=1) - gdf['date']
        gdf['sources'] = [source_label] * len(gdf)
        

        self.gpd_geom_match(gdf, self.fl, column_of_interest = 'dist_from_grndline', date_col='date', add_result=True)
        
        if '' not in self.results.keys():
            return

        self.results[''] = self.results[''].sort_values(by='time')
        pass

    def round_dates(self, date):
        if type(date) != datetime.datetime:
            try:
                date = np.datetime64(date).astype(datetime.datetime)
            except:
                return date

        if type(date) == datetime.date:
            date = datetime.datetime(date.year, date.month, date.day)
        return date


    def gpd_geom_match(self, out, index, column_of_interest = 'elev', add_result=True, date_col='date', 
                       force_index=False, closest_time=False):

        key = self.get_label(index)
        if force_index != False:
            key = force_index
        
        
        if type(index) == int:
            p = self.points[index]
            df_ref = self.create_point_df([p])
        else:
            df_ref = index

        
        df_ref = gpd.sjoin(df_ref, out, distance=self.max_dist, predicate='dwithin')
        
        #if self.data == 'gl':
        #    df_ref.to_file(POINTWISE_OUTPUT_LOCATION + str(self.point_label) + "_gl.gpkg", layer="geometry", driver="GPKG")
        
        time = []
        sources = []
        data = []

        other_items = {}
        potential_cols = [self.data + '_xerr_min', self.data + '_xerr_max', self.data + '_xerr',
                          self.data + '_yerr_min', self.data + '_yerr_max', self.data + '_yerr']
        item_combiner = {self.data + '_xerr_min' : np.min, 
                         self.data + '_xerr_max': np.max, 
                         self.data + '_xerr': np.mean,
                         self.data + '_yerr_min' : np.min, 
                         self.data + '_yerr_max': np.max, 
                         self.data + '_yerr': np.mean}

        for x in potential_cols:
            if x in df_ref.columns:
                other_items[x] = []

        grouped_dates = []
        for x in df_ref[date_col]:
            grouped_dates.append(self.round_dates(x))
        grouped_dates = np.array(grouped_dates)

        for x in np.unique(grouped_dates):
            val_arr = df_ref[grouped_dates == x].dropna()
            if len(val_arr) == 0:
                continue 
            if closest_time and key in self.results.keys() and len(self.results[key]) != 0:
                nearby_existing = self.get_closest_existing_value_dist(x, self.results[key]['time']) < closest_time
                nearby_currentg = self.get_closest_existing_value_dist(x, time) < closest_time
                print(nearby_existing, self.get_closest_existing_value_dist(x, self.results[key]['time']))
                if nearby_existing or nearby_currentg:
                    continue

            val_arr = val_arr.sort_values(by=date_col)
            val_arr = val_arr.reset_index(drop=True)
            

            val_arr = val_arr.iloc[len(val_arr)//2]
            
            
            val = val_arr[column_of_interest]
            
            try:
                if np.isnan(val):
                    continue
            except:
                pass
            if 'sources' in df_ref.columns:
                

                src = val_arr['sources']

                if type(src) != str:
                    src = src.values
                sources.append(src)
                
                for y in other_items.keys():

                    v = val_arr[y]

                    other_items[y].append(v)
                

            
            data.append(val)
            time.append(x)

        if len(time) == 0:
            return []
        if type(time[0]) == str:
            for x in range(len(time)):
                time[x] = np.datetime64(time[x])
        time = np.array(time).astype(datetime.datetime)
        data = np.array(data)
        sources = np.array(sources)

        if len(data) == 0:
            return []

        if self.change:
            tiem, data = self.gpd_time_difference(time, data)

        df_contents = {'time': time, self.data: data}
        if len(sources):
            df_contents['sources'] = sources
        for y in other_items.keys():
            df_contents[y] = other_items[y]

        df = pd.DataFrame(df_contents)

        if add_result:
            if key not in self.results.keys():
                self.results[key] = pd.DataFrame()
                
            if len(self.results[key]) == 0:
                self.results[key] = df
            self.results[key] = pd.concat([self.results[key], df], axis=0, ignore_index=True)
        else:

            self.results[key] = df
        return df

    
    def geotiff_geom_match(self, out, index, column_of_interest = 'band_data', add_result=True):
        p = self.points[index]

        df = out.sel(x=p[1], y=p[0], method='nearest')


        if 'time' not in df.variables and 'year' in df.variables:
            t = df['year'].values
            new_dates = []
            for x in range(len(t)):
                new_dates.append(t[x])
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

        values = df[column_of_interest]
        
        if self.change:
            new_dates, values = self.gpd_time_difference(new_dates, df[column_of_interest])

        if 'sources' in df.variables:
            df = pd.DataFrame({'time': new_dates, 'sources': df['sources'],
                               self.data: values})

        else:
            df = pd.DataFrame({'time': new_dates,
                                self.data: values})
            

        
        if add_result:
            if self.get_label(index) not in self.results.keys() or len(self.results[self.get_label(index)]) == 0:
                self.results[self.get_label(index)] = df
            else:
                self.results[self.get_label(index)] = pd.concat([self.results[self.get_label(index)], df], axis=0, ignore_index=True)
        else:
            self.results[self.get_label(index)] = df


    def get_closest_existing_date(self, date, date_array):
        return np.array(sorted(date_array, key=lambda x: abs(np.datetime64(x) - np.datetime64(date))))


    def get_closest_existing_value_dist(self, val, val_array):
        ranked = np.array(sorted(np.abs(val_array - val)))
        if len(ranked) != 0:
            return ranked[0]
        return 9999999999999


    def gpd_time_difference(self, time, data):
        time = np.array(time)
        data = np.array(data)

        ref_datetime = datetime.datetime(self.time_diff_year, 1, 1)

        if type(self.change) != bool and 'interp' in self.change and ref_datetime not in time and np.datetime64(ref_datetime) not in time:
            ref_pre = self.get_closest_existing_date(ref_datetime, time[data != np.nan])
            ref_post = self.get_closest_existing_date(ref_datetime, time[data != np.nan])
            ref_pre = ref_pre[ref_pre < ref_datetime]
            ref_post = ref_post[ref_post > ref_datetime]


            if len(ref_pre) == 0 and len(ref_post) == 0:
                return
            elif len(ref_pre) == 0 or ref_post[0] - np.datetime64(ref_datetime ) == 0:
                ref = data[time == ref_post[0]]
            elif len(ref_post) == 0 or ref_pre[0] - np.datetime64(ref_datetime ) == 0:
                ref = data[time == ref_pre[0]]
            else:
                ref_pre = ref_pre[0]
                ref_post = ref_post[0]
                dif = data[time == ref_post] - data[time == ref_pre]

                perc = 1 - ((ref_datetime - ref_post) / (ref_pre - ref_post))

                ref = data[time == ref_pre] + (dif * perc)

        else:
            
            if type(self.time_diff_year) == int and type(time[0]) != int:
                ref_time = sorted(time[data != np.nan], key=lambda x: abs(x - datetime.datetime(self.time_diff_year, 1, 1)))[0]
            elif self.time_diff_year == None or type(time[0]) == int or type(time[0]) == float:
                ref_time = min(time[data != np.nan])
                
            ref = data[time == ref_time]

            
        
        if type(self.change) != bool and '%' in self.change:
            data = ((data - ref) / abs(ref)) * 100
        else:
            data = data - ref

        return time, data



    def plot_time_series(self, fig, ax, rema=False, unified_line=True, plot_range=None):
        if not self.results:
            self.get_data(rema)
        if not self.results:
            print('No values found for time series.')
            return

        if plot_range == None:
            plot_range = [datetime.datetime(self.flags.YEARSTART, 1, 1), datetime.datetime(self.flags.YEAREND, 1, 1)]

        shapes_set = {}
        shapes = ['s', '^', 'D']
        sm = mpl.cm.ScalarMappable(norm=self.norm, cmap=self.cmap)


        all_results_time = self.results[list(self.results.keys())[0]]['time']
        all_results_values = self.results[list(self.results.keys())[0]][self.data]

        

        for p in self.results.keys():
            if p == list(self.results.keys())[0]:
                continue
            all_results_time =  np.concat([all_results_time, self.results[p]['time']])
            all_results_values = np.concat([all_results_values, self.results[p][self.data]])


        '''

        for j, p in enumerate(self.results.keys()):
            self.results[p] = self.results[p].dropna()
            ls = 'None'
            color = sm.to_rgba(self.labels[j])
            ax.plot(self.results[p]['time'], 
                            self.results[p][self.data].values, marker= 'None', color=color)
        
        good_type = []
        for x in range(len(all_results_time)):
            good_type.append(pd.to_datetime(all_results_time[x]))'''
        

        self.set_range_only_in_frame(ax, all_results_time, all_results_values, plot_range, 'y')
        ax.set_xlim((plot_range[0], plot_range[1]))
        


        if 'sources' in self.results[list(self.results.keys())[0]].columns:
            for i, s in enumerate(self.results[list(self.results.keys())[0]]['sources'].unique()):
                shapes_set[s] = shapes[i]
                ax.plot([], [], label = s, marker= shapes_set[s], color=sm.to_rgba(0), linestyle='None')


        print(self.results[p].columns)

        for j, p in enumerate(self.results.keys()):
            self.results[p] = self.results[p].dropna()
            ls = 'None'
            color = sm.to_rgba(self.labels[j])
            if self.data == 'gl':
                color = sm.to_rgba(0)

            if unified_line:
                ax.plot(self.results[p]['time'], 
                            self.results[p][self.data].values, marker= 'None', color=color)
            else:
                ls = 'solid'
            
            if 'sources' in self.results[p].columns:
                for i, s in enumerate(self.results[p]['sources'].unique()):
                    cur = self.results[p][self.results[p]['sources'] == s]
                    
                    ax.plot(cur['time'], 
                        cur[self.data].values, marker= shapes_set[s], color=color, linestyle=ls)
            else:
                ax.plot(self.results[p]['time'], 
                        self.results[p][self.data].values, label = p, marker= 'o', color=color, linestyle=ls)


            if self.data +'_xerr' in self.results[p].columns:
                ax.errorbar(self.results[p]['time'], 
                            self.results[p][self.data].values, marker= '', xerr= self.results[p][self.data +'_xerr'],
                            fmt='none')
            elif self.data +'_xerr_min' in self.results[p].columns:
                ax.errorbar(self.results[p]['time'], 
                            self.results[p][self.data].values, marker= '', 
                            xerr= [self.results[p][self.data +'_xerr_min'], self.results[p][self.data +'_xerr_max']],
                            fmt='none')


            if self.data +'_yerr' in self.results[p].columns:
                ax.errorbar(self.results[p]['time'], 
                            self.results[p][self.data].values, marker= '', yerr= self.results[p][self.data +'_yerr'],
                            fmt='none')
            elif self.data +'_yerr_min' in self.results[p].columns:
                ax.errorbar(self.results[p]['time'], 
                            self.results[p][self.data].values, marker= '', 
                            xerr= [self.results[p][self.data +'_yerr_min'], self.results[p][self.data +'_yerr_max']],
                            fmt='none')

            if self.data == 'gl':
                return


    def get_dataset_display_range(self, dataset, padding=0.05):
        dataset= np.array(dataset)
        dataset = dataset[~np.isnan(dataset)]
        if len(dataset) == 0:
            return False

        ymin = dataset.min()
        ymax = dataset.max()

        ypadd = padding * (ymax - ymin)
        if np.isnan(ypadd):
            return False
        return [ymin - np.abs(ypadd), ymax + np.abs(ypadd)]

    def plot_elevation_summary(self, fig, ax):
            
        sm = mpl.cm.ScalarMappable(norm=self.norm, cmap=self.cmap)
        color = sm.to_rgba(0)

        fm = IPRManager(self.xlim, self.ylim, self.flags, self.data)
        out = fm.get_ouput_files()
        out = df_ref = gpd.sjoin_nearest(self.fl, out, max_distance=self.max_dist*10)

        out = out.sort_values('dist_from_grndline')
        
        bad_out = out.copy(deep=True)
        out['real_elevation1'] = out['real_elevation1'].where(out['dist_from_grndline'] < 0)


        #ax.plot(bad_out['real_elevation1'] - bad_out['THICK'], bad_out['dist_from_grndline'].values, marker= 'None', color=color, label='Bottom', ls = ':', alpha=0.5)
        ax.plot(out['real_elevation1'] - out['THICK'], out['dist_from_grndline'].values, marker= 'None', color=color, label='Bed')
        
        ax.legend()
        ax.grid()


        y_lims = self.get_dataset_display_range(self.results[''][self.data].values)

        ax.set_ylim(y_lims[0], y_lims[1])
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")

        #ax.set_xlim(-1800, -1450)
        self.set_range_only_in_frame(ax, bad_out['real_elevation1'] - bad_out['THICK'], bad_out['dist_from_grndline'].values, y_lims, 'x')


        #ax.set_ylabel("Grounding Line Change (m)")
        ax.set_xlabel("Elevation (m)")


    def set_range_only_in_frame(self, ax, x, y, other_axis_range, axis):

        axis_params = {
            'x': {
                'to_crop': x,
                'crop_by': y,
                'set_axis': ax.set_xlim,
                'set_other_axis': ax.set_ylim
            },

            'y': {
                'to_crop': y,
                'crop_by': x,
                'set_axis': ax.set_ylim,
                'set_other_axis': ax.set_xlim
            }
        }

        key_area = axis_params[axis]['to_crop'].copy()
        key_area[axis_params[axis]['crop_by'] < min(other_axis_range)] = np.nan
        key_area[axis_params[axis]['crop_by'] > max(other_axis_range)] = np.nan
        lims = self.get_dataset_display_range(key_area)
        if not lims:
            return
        axis_params[axis]['set_axis'](lims[0], lims[1])
        axis_params[axis]['set_other_axis'](other_axis_range[0], other_axis_range[1])


        

    def get_data_rema(self):

        for p in range(len(self.points)):
            if self.get_label(p) not in self.results.keys():
                self.results[self.get_label(p)] = pd.DataFrame({})

        filemanager = ElevationManager(self.xlim, self.ylim, self.flags, self.data)
        
        for p, point in enumerate(self.points):
            new_df = filemanager.get_point_data(point)
            self.results[self.get_label(p)] = pd.concat([self.results[self.get_label(p)], new_df])
            self.results[self.get_label(p)] = self.results[self.get_label(p)].sort_values('time')


    def get_data(self, rema=False, firn_source=-1):

        type_info = {
            'vel': 'band_data',
            'grav': 'dm',
            'elev': 'elev',
            'firn': 'band_data',
        }
        
        fms = {
            'vel': VelocityManager,
            'grav': GravimetryManager,
            'elev': ElevationManager,
            'firn': FirnAirManager,
        }

        if self.data == 'gl':
            self.get_gl_set()
            self.get_gl_set(GL_GPKG_manual, source_label='Manual Sentinel-1 selections, 2026')
            self.get_gl_set(GL_GPKG_radar, ['date'], 'Open Polar Radar, 2024')
            return 

        if self.data == 'firn' and firn_source == -1:
            self.get_data(firn_source=0)
            self.get_data(firn_source=1)
            self.get_data(firn_source=2)
            return
        elif self.data == 'firn':
            filemanager = fms[self.data](self.xlim, self.ylim, self.flags, self.data, source=firn_source)
        else:
            filemanager = fms[self.data](self.xlim, self.ylim, self.flags, self.data)

        print('getting output')
        out = filemanager.get_ouput_files()
        print('comparing points')
        for p in range(len(self.points)):
            if type(out) == gpd.geodataframe.GeoDataFrame:
                self.gpd_geom_match(out, p, column_of_interest=type_info[self.data])
            elif type(out) == xr.core.dataset.Dataset:
                self.geotiff_geom_match(out, p, column_of_interest=type_info[self.data])

            if self.get_label(p) not in self.results.keys():
                return
            
            self.results[self.get_label(p)] = self.results[self.get_label(p)].sort_values('time')

        if rema and self.data == 'elev':
            return self.get_data_rema()



class FlowProfile(Pointwize):
    def __init__(self, flags, xlim, ylim, points, cmap='winter', dates=False):
        super().__init__(flags,xlim,ylim,points,'gl',cmap=cmap)
        self.change = False
        self.max_dist = 50
        self.specific_dates = dates
        if dates:
            self.dates = [datetime.datetime(2020, 1, 1), 
                        datetime.datetime(2021, 1, 1), 
                        datetime.datetime(2022, 1, 1), 
                        datetime.datetime(2023, 1, 1), 
                        datetime.datetime(2024, 1, 1),]
        else:
            self.dates = [datetime.datetime(flags.YEARSTART, 1, 1), datetime.datetime(flags.YEAREND, 1, 1),]
        self.norm = mcolors.Normalize(vmin=mdates.date2num(self.dates[0]), vmax=mdates.date2num(self.dates[-1]))
        self.cmap = cmap
        

    
    def get_data(self, date, seek=True):
        if date == None:
            f=self.flags.copy()
        else:
            f = self.flags.copy()
            f.add('-' + str(date.year-1) + '-' + str(date.year + 1))

        filemanager = ElevationManager(self.xlim, self.ylim, f, 'elev')
        out = filemanager.get_ouput_files()
        if len(out) == 0:
            return []

        self.gpd_geom_match(out, self.fl, column_of_interest='date', date_col='dist_from_grndline', add_result=False, force_index=date)
        
        if date != None:
            print([date, date])
            if date not in self.results.keys():
                self.results[date] = []
                return [date, date]
            date_options = self.get_closest_existing_date(date, self.results[date]['gl'].dt.to_period('D').dt.to_timestamp().unique().copy())
            self.results[date] = []
            print(date)

            closest = date_options[0]
            seeking = True

            date_range = [closest, closest]
            
            while seeking:
                try:
                    out_temp = out[out['date'].dt.to_period('D').dt.to_timestamp() == closest]
                    ret = self.gpd_geom_match(out_temp, self.fl, column_of_interest='elev', date_col='dist_from_grndline', add_result=True, force_index=date,closest_time=1000)
                    if len(ret) != 0:
                        if closest < date_range[0]:
                            date_range[0] = closest
                        elif closest > date_range[1]:
                            date_range[1] = closest
                except IndexError as e:
                    seeking |= seek
                    pass
                
                print(self.results[date])
                
                out = out[out['date'].dt.to_period('D').dt.to_timestamp() != closest]
                if len(out) == 0:
                    seeking = False
                date_options = date_options[1:]
                if len(date_options) == 0:
                    seeking = False
                    break
                closest = date_options[0]
                seeking |= seek

        else:
            dates = self.results[date]['gl'].dt.to_period('D').dt.to_timestamp().unique().copy()
            
            for d in dates:
                out_temp = out[out['date'].dt.to_period('D').dt.to_timestamp() == d]
                ret = self.gpd_geom_match(out_temp, self.fl, column_of_interest='elev', date_col='dist_from_grndline', add_result=True, force_index=d,closest_time=1000)
            date_range=[datetime.datetime(self.flags.YEARSTART, 1, 1), datetime.datetime(self.flags.YEAREND, 1, 1),]
                    



        return date_range
    
    def geotiff_s_join(self, out, points, column_of_interest = 'band_data'):
        dists = []
        values = []
    
        for pos in points.itertuples():
            dists.append(pos.dist_from_grndline)
            values.append(out.sel(x=pos.geometry.x, y=pos.geometry.y, method='nearest')[column_of_interest].values)

        df = gpd.GeoDataFrame({
            "dists": dists,
            "vals": values
        })
        df = df.sort_values('dists')
        return df
    

    def get_equilibrium(self, elevations, FAC=20, SEA_LEVEL_ELEVATION=SEA_LEVEL_ELEVATION,  in_ellipsoid=False):

        new_elevations = elevations + SEA_LEVEL_ELEVATION # Rise from WSG-84 to relative to local sea level
        new_elevations -= FAC # remove firn air content

        total_elevation = new_elevations / 0.1 # remaining height is 10% of total, so this obtains the total
        total_elevation -= new_elevations # remove the 10% above the surface
        total_elevation = -total_elevation # INVERSION: now working with negative values

        final_elevations = total_elevation
        if not in_ellipsoid:
            final_elevations = total_elevation - SEA_LEVEL_ELEVATION # Adjust from local sea level to WSG-84
            
        return final_elevations

    '''def invert_equilibrium(self, elevations, FAC=20, SEA_LEVEL_ELEVATION=SEA_LEVEL_ELEVATION, in_ellipsoid=False):
        new_elevations = elevations + SEA_LEVEL_ELEVATION # Rise from WSG-84 to relative to local sea level

        thickness = ((new_elevations - FAC) * 1027) / (1027 - 917)
        floatation = elevations + thickness
        floatation += FAC

        if not in_ellipsoid:
            floatation = floatation - SEA_LEVEL_ELEVATION # Adjust from local sea level to WSG-84

        return floatation'''


    def invert_equilibrium(self, elevations, FAC=20, SEA_LEVEL_ELEVATION=SEA_LEVEL_ELEVATION, in_ellipsoid=False):

        new_elevations = elevations + SEA_LEVEL_ELEVATION # Rise from WSG-84 to relative to local sea level

        total_elevation = new_elevations / 0.9 # Height is 90% of total, so this obtains the total
        total_elevation -= new_elevations # remove the 90% under the surface
        total_elevation = -total_elevation # INVERSION: now working with positive values

        total_elevation = np.array(total_elevation)
        total_elevation += np.array(FAC) # add the firn air content to the height

        final_elevations = total_elevation
        if not in_ellipsoid:
            final_elevations = total_elevation - SEA_LEVEL_ELEVATION # Adjust from local sea level to WSG-84

        return final_elevations

    def get_simple_equilibrium(self, elevations):
        total_height = (elevations / 0.1)
        return -(total_height - elevations)
    

    def plot_specific_date(self, fig, ax, p, x):
        label = self.get_data(x)
        label = self.create_date_range_label(label)

        if len(self.results[x]) == 0:
            return

        self.results[x] = self.results[x].sort_values(by='time')
        p.plot_elevation_data(fig, ax, self.cmap, self.norm,
                            self.results[x]['time'], self.results[x]['gl'],
                            label=str(label), color_key=mdates.date2num(x))
        

    def plot_all_by_date(self, fig, ax, p):
        label = self.get_data(None)
        

        if len(self.results.keys()) == 0:
            return

        for x in self.results.keys():
            label = self.create_date_range_label([x, x])
            #self.results[x] = self.results[x].sort_values(by='time')
            p.plot_elevation_data(fig, ax, self.cmap, self.norm,
                                self.results[x]['time'], self.results[x]['gl'],
                                label=str(label), color_key=mdates.date2num(x))

    
    def plot_pair(self, fname):
        p = Plotting()
        fig, ax = p.elevation_profile_plot()

        rema_fm = REMATileManager(self.xlim, self.ylim, self.flags, self.data, 'REMA')
        out = rema_fm.get_ouput_files()
        rema_vals = self.geotiff_s_join(out, self.fl)
        ax[0].plot(rema_vals['dists'], rema_vals['vals'], ls='dotted', marker= 'None', label='REMA Surface')
        

        if self.specific_dates:
            for x in self.dates:
                self.plot_specific_date(fig, ax, p, x)
        else:
            self.plot_all_by_date(fig, ax, p)
            

        
        fm = IPRManager(self.xlim, self.ylim, self.flags, self.data)
        out = fm.get_ouput_files()
        out = gpd.sjoin_nearest(self.fl, out, max_distance=self.max_dist*10)

        out = out.sort_values('dist_from_grndline')
        bad_out = out.copy()
        out['real_elevation1'] = out['real_elevation1'].where(out['dist_from_grndline'] <= 0)
        #out['real_elevation1'] = out['real_elevation1'].where(out['dist_from_grndline'] > 0)
        ax[1].plot(bad_out['dist_from_grndline'].values, bad_out['real_elevation1'] - bad_out['THICK'], ls='dashed', marker= 'None', label='IPR Bottom')
        
        ax[1].plot(out['dist_from_grndline'].values, out['real_elevation1'] - out['THICK'], marker= 'None', label='IPR Bed')
        
        


        FAC = 20
        FAC2 = 16
        
        rema_vals_bottom = self.get_equilibrium(rema_vals['vals'], FAC)
        ax[1].plot(rema_vals['dists'], rema_vals_bottom, ls='dotted', marker= 'None', label='REMA Equilibrium, FAC=' + str(FAC))
        rema_vals_bottom = self.get_equilibrium(rema_vals['vals'], FAC2)
        ax[1].plot(rema_vals['dists'], rema_vals_bottom, ls='dotted', marker= 'None', label='REMA Equilibrium, FAC=' + str(FAC2))


        limsy = self.get_dataset_display_range(out['real_elevation1'] - out['THICK'], padding=0.1)
        ax[1].set_ylim(limsy)
        ax[1].set_xlim(ax[0].get_xlim())

        ax[0].legend()
        ax[1].legend()
        p.save_close(fig, ax, OUTPUT + fname + "_profile_pair")
        

    def plot(self, fname):
        p = Plotting()

        geoid = False


        fig, ax = p.elevation_profile_plot_single()

        out = xr.open_dataset(SEA_LEVEL_TIF)

        sea_level = self.geotiff_s_join(out, self.fl)
        
        general_sea_level = sea_level['vals'].mean()

        rema_fm = REMATileManager(self.xlim, self.ylim, self.flags, self.data, 'REMA')
        out = rema_fm.get_ouput_files()
        rema_vals = self.geotiff_s_join(out, self.fl)
        if geoid:
            rema_vals['vals'] -= sea_level['vals']
        ax.plot(rema_vals['dists'], rema_vals['vals'], ls='dotted', marker= 'None', label='REMA Surface')
        
        for x in self.dates:
            label = self.get_data(x)
            label = self.create_date_range_label(label)
            if x not in self.results.keys():
                continue

            if len(self.results[x]) == 0:
                continue

            print(label)

            self.results[x] = self.results[x].sort_values(by='time')
            if geoid:
                self.results[x]['gl'] -= general_sea_level
            p.plot_elevation_data(fig, ax, self.cmap, self.norm,
                                self.results[x]['time'], self.results[x]['gl'],
                                label=str(label), color_key=mdates.date2num(x))
        
            

        fm = IPRManager(self.xlim, self.ylim, self.flags, self.data)
        out = fm.get_ouput_files()
        out = gpd.sjoin_nearest(self.fl, out, max_distance=self.max_dist*10)

        out = out.sort_values('dist_from_grndline')
        bad_out = out.copy()
        out['real_elevation1'] = out['real_elevation1'].where(out['dist_from_grndline'] <= 0)
   


        fm = IPRManager(self.xlim, self.ylim, self.flags, self.data, corrected=True)
        out = fm.get_ouput_files()
        out = gpd.sjoin_nearest(self.fl, out, max_distance=self.max_dist*10)
        out.dropna(how='any')

        out = out.sort_values('dist_from_grndline')

        out = out.dropna()
        sea_level['dist_from_grndline'] = sea_level['dists']
        out = out.merge(sea_level, on='dist_from_grndline', how='inner')
        out['atm_height'] += out['vals']
        #out['firnair'] = out['firnair'].apply(lambda x: sum(x) / len(x) if len(x) > 0 else None)


        FAC_med = out['firnair'].quantile(.5)
        FAC1 =  22 #out['firnair'].quantile(.6)
        FAC2 =  14 #out['firnair'].quantile(.4)


        IPR_mirror1 = self.invert_equilibrium(out['atm_height'] - out['corrected_thickness'], FAC1, SEA_LEVEL_ELEVATION=-out['vals'], in_ellipsoid=geoid)
        IPR_mirror2 = self.invert_equilibrium(out['atm_height'] - out['corrected_thickness'], FAC2, SEA_LEVEL_ELEVATION=-out['vals'], in_ellipsoid=geoid)
        IPR_mirror_med = self.invert_equilibrium(out['atm_height'] - out['corrected_thickness'], FAC_med, SEA_LEVEL_ELEVATION=-out['vals'], in_ellipsoid=geoid)
        print(FAC1)
        print(FAC2)
        
        IPR_mirror2 = list(itertools.chain.from_iterable(IPR_mirror2))
        IPR_mirror1 = list(itertools.chain.from_iterable(IPR_mirror1))
        
        ax.fill_between(out['dist_from_grndline'], IPR_mirror1, IPR_mirror2, color='lightgray', alpha=0.5, label='IPR Floatation Height Range (' +str(round(FAC1)) + '-' + str(round(FAC2)) +" FAC)")
        #ax.plot(out['dist_from_grndline'], IPR_mirror_med, color='darkgray')


        if geoid:
            out['atm_height'] -= out['vals']
        ax.plot(out['dist_from_grndline'], out['atm_height'], marker= 'None', color='black', label='Corrected IPR Surface Elevation')


        
        out = out.merge(rema_vals, on='dists', how='inner', suffixes=('_sea_level', '_rema'))
        

        
        if geoid:
            out['vals_rema'] += out['vals_sea_level']
            
        IPR_mirror1 = self.invert_equilibrium(out['vals_rema'] - out['THICK'], FAC1, SEA_LEVEL_ELEVATION=SEA_LEVEL_ELEVATION, in_ellipsoid=geoid)
        IPR_mirror2 = self.invert_equilibrium(out['vals_rema'] - out['THICK'], FAC2, SEA_LEVEL_ELEVATION=SEA_LEVEL_ELEVATION, in_ellipsoid=geoid)
        IPR_mirror_med = self.invert_equilibrium(out['vals_rema'] - out['THICK'], FAC_med, SEA_LEVEL_ELEVATION=SEA_LEVEL_ELEVATION, in_ellipsoid=geoid)
            


        #IPR_mirror2 = list(itertools.chain.from_iterable(IPR_mirror2))
        #IPR_mirror1 = list(itertools.chain.from_iterable(IPR_mirror1))
        '''IPR_range = out['dist_from_grndline'].values[~np.isnan(IPR_mirror1)]
        IPR_mirror2 = IPR_mirror2[~np.isnan(IPR_mirror2)]
        IPR_mirror1 = IPR_mirror1[~np.isnan(IPR_mirror1)]'''

        out['dist_from_grndline'] = np.array(out['dist_from_grndline'], dtype=float)
        IPR_mirror1 = np.array(IPR_mirror1, dtype=float)
        IPR_mirror2 = np.array(IPR_mirror2, dtype=float)
        
        
        ax.fill_between(out['dist_from_grndline'].values, IPR_mirror1, IPR_mirror2, color='lightsteelblue', alpha=0.5, label='REMA Floatation Height Range (' +str(round(FAC1)) + '-' + str(round(FAC2)) +" FAC)")
        
        
        #a = ax.plot(out['dist_from_grndline'].values, IPR_mirror1, ls='dashed', marker= 'None', label='IPR Floatation Height, FAC=' + str(FAC1))
        #ax.plot(out['dist_from_grndline'].values, IPR_mirror2, marker= 'None', color=a[0].get_color(), label='IPR Floatation Height, FAC=' + str(FAC2))
        
        #ax.plot(out['dist_from_grndline'], IPR_mirror_med, color='darkgray')


        #ax.set_ylim([ax.get_ylim()[0] - 20, ax.get_ylim()[1]])
        if geoid:
            ax.set_ylabel('Geoid Elevation (m)')

        ax.legend()
        p.save_close(fig, ax, OUTPUT + fname + "_profile")
        

    def plot_diff(self, fname):
        p = Plotting()
        fig, ax = p.elevation_profile_plot_single()
        labels = {}
        
        if self.specific_dates:
            
            for x in self.dates:
                label = self.get_data(x)
                labels[x] = self.create_date_range_label(label)

                if len(self.results[x]) == 0:
                    continue

                self.results[x] = self.results[x].sort_values(by='time')
        else:
            self.get_data(None, seek=False)
            self.dates = self.results.keys()
            for dates in self.dates:
                if dates == None:
                    continue
                labels[dates] = self.create_date_range_label([dates, dates])

        print(self.results.keys())
        print(self.results[None])
        del self.results[None]

        full_track_length = 0
        remove = []
        for x in self.results.keys():
            if len(self.results[x]['gl']) > full_track_length:
                full_track_length = len(self.results[x]['gl'])
        for x in self.results.keys():
            if len(self.results[x]['gl']) < full_track_length:
                remove.append(x)
        for x in remove:
            print(x, "does not have enough points, ", len(self.results[x]['gl']), '/',  full_track_length)
            del self.results[x]
        start = min(self.results.keys())

        
            
        for x in sorted(self.dates):
            if len(self.results[x]['gl']) == len(self.results[start]['gl']):
                diffed = self.results[x]['gl'] - self.results[start]['gl']
                projected = ((x.toordinal() - start.toordinal())/365) * self.trend_adjustment
                diffed -= projected
                p.plot_elevation_data(fig, ax, self.cmap, self.norm, 
                                    self.results[x]['time'], diffed, 
                                    label=str(labels[x]), change_lims=False, color_key=mdates.date2num(x))
            else:
                continue
                

        ax.set_ylabel("WSG-84 Elevation Difference (m)")
        ax.set_xlabel("Distance along profile line (m)")

        ax.legend()
        ax.set_title("Profile " + fname + " (" + self.title + ")")
        p.save_close(fig, ax, OUTPUT + fname + "_profile")


    def create_date_range_label(self, date_range):
        date_labels = []
        for y in range(len(date_range)):
            if date_range[y] == None:
                continue
            date_labels.append(str(date_range[y].month) + '/' + str(date_range[y].year))
        if len(date_labels) == 0:
            return ''

        if date_labels[0] == date_labels[1]:
            for y in range(len(date_labels)):
                date_labels[y] = str(date_range[y].day) + '/' + date_labels[y]


        if date_labels[0] == date_labels[1]:
            date_labels = [date_labels[0]]


        label = '-'.join(date_labels)
        
        return label

        
        
        


        

    

        
    



class PointSeries():
    def __init__(self, xlims, ylims, flags, starting_poses, labels=None):
        self.xlims = xlims
        self.ylims = ylims
        self.flags = flags
        self.labels = labels
        if type(starting_poses) == list and type(starting_poses[0]) == list:
            self.points = starting_poses
        else:
            self.points = [starting_poses]

        if self.labels == None:
            labels = []
            for x in range(len(self.points)):
                labels.append(str(x+1))

    def get_points(self, overlap_ds=False, include_all=True, index='index'):
        if include_all:
            points = []
            for p in self.points:
                points.append(Point(p[1], p[0]))
            gpd_df = gpd.GeoDataFrame({'dist_from_grndline': self.labels, 'vel_dates': self.labels}, geometry=points, crs='EPSG:3031')
            return np.array(self.points), np.array(self.labels), gpd_df
        return np.array(self.points), np.array(self.labels)

class PolyLine(PointSeries):
    def __init__(self, xlims, ylims, flags, starting_poses, pt_label, step_dist = 50, fname="POLYLINE_TEST"):
        super().__init__(xlims, ylims, flags, starting_poses)

        self.step_dist = step_dist
        self.main_pts = starting_poses
        self.pt_label = pt_label
        self.points = []
        self.labels = []

        temp = []
        for p in self.main_pts:
            temp.append(Point(p[1], p[0]))
        df_ref = pd.DataFrame({'geometry':temp, 'labels':self.pt_label})
        df_ref = gpd.GeoDataFrame(df_ref, geometry=temp, crs='EPSG:3031')
        df_ref.to_file(fname + '.gpkg', driver="GPKG")

    def distance(self, pos1, pos2):
        return overall_velocity(pos1[0] - pos2[0], pos1[1] - pos2[1])

    def interpolation(self, pos1, pos2, perc):
        pos = []
        for x in range(len(pos1)):

            cur = pos1[x] + ((pos2[x] - pos1[x]) * perc)

            pos.append(cur)

        return pos
    
    
    def two_point_array(self, p1, p2, cur_dist=0):
        total_dist = self.distance(p1, p2)
        percs = self.step_dist / total_dist
        cur = -percs

        while cur <= 1:
            cur += percs
            self.points.append(self.interpolation(p1, p2, cur))
            self.labels.append((cur * total_dist) + cur_dist)

        return total_dist


    def get_points(self, overlap_ds=False, include_all=True, index='index'):
        
        cur_dist = 0
        for x in range(1, len(self.main_pts)):
            cur_dist += self.two_point_array(self.main_pts[x-1], self.main_pts[x], cur_dist=cur_dist)

        if include_all:
            points = []
            for p in self.points:
                points.append(Point(p[1], p[0]))
            gpd_df = gpd.GeoDataFrame({'dist_from_grndline': self.labels, 'vel_dates': self.labels}, geometry=points, crs='EPSG:3031')
            gpd_df.to_file('POLYLINE_TEST.gpkg', driver='GPKG')
            return np.array(self.points), np.array(self.labels), gpd_df

        return np.array(self.points), np.array(self.labels)


class StreamFlow(PointSeries):
    def __init__(self, xlims, ylims, flags, starting_pos, step_dist, step_num, date_steps = STREAM_PLOT_STEPS, max_dist = 500, label_type = 'dist', cmap='managua'):
        f = flags.copy()
        f.add('-itslive')
        self.fmx = VelocityManager(xlims, ylims, f, 'velx')
        self.fmy = VelocityManager(xlims, ylims, f, 'vely')
        super().__init__(xlims, ylims, f, starting_pos)

        self.cmap = cmap

        self.starting_pos = starting_pos
        self.pos = [0, 0]
        self.pos[0] = self.starting_pos[1] # y is stored as first item in the coords
        self.pos[1] = self.starting_pos[0]

        self.date = 0
        self.dist = []
        self.flags = f

        self.duration = step_dist * (step_num[1] - step_num[0])
        self.step_dist = step_dist
        self.step_num = step_num[1] - step_num[0]
        self.step_range = step_num
        self.date_steps = date_steps
        self.max_dist = max_dist

        self.label_type = label_type

        #self.output['velocity'] = self.output['velocity'].where(False)
        #self.output = self.output.where(self.output['visted'] != 0)

        self.dates = []
        self.velocities = []
        self.dist = []
        self.points = []


    def follow_flow(self, cur_dist, fx, fy, dir=1):
        cur_vx = dir * float(fx.sel(x=self.pos[0], y=self.pos[1], method='nearest')['band_data'].dropna(dim='year').mean())
        cur_vy = dir * float(fy.sel(x=self.pos[0], y=self.pos[1], method='nearest')['band_data'].dropna(dim='year').mean())
        #print(fx.sel(x=self.pos[0], y=self.pos[1], method='nearest')['band_data'])
        #print(fx.sel(x=self.pos[0], y=self.pos[1], method='nearest')['band_data'].dropna(dim='year'))
        
        if np.isnan(cur_vx):
            return self.duration + 1

        

        v = float(overall_velocity(cur_vx, cur_vy))
        self.velocities.append(v)
        self.date += dir * self.date_steps
        self.dates.append(self.date)


        self.pos[0] += cur_vx * self.date_steps
        self.pos[1] += cur_vy * self.date_steps

        self.points.append(Point(self.pos[0], self.pos[1]))

        cur_dist += dir * float(overall_velocity(cur_vx * self.date_steps, cur_vy * self.date_steps))
        self.dist.append(int(cur_dist))

        return cur_dist
    

    def get_stream(self, direction=1, points=None):
        if points == None:
            points = self.step_num
        fx = self.fmx.get_ouput_files()
        fy = self.fmy.get_ouput_files()
        
        cur_dist = 0
        self.date = 0

        self.pos[0] = self.starting_pos[1]
        self.pos[1] = self.starting_pos[0]


        cutoff = self.duration * 100000
        i = 0

        partial_duration = (np.abs(points)/self.step_num) * self.duration #only do the needed duration (points can be negative so it is abs'ed)
        

        while cur_dist < partial_duration and cur_dist > -partial_duration and cutoff > i:
            cur_dist = self.follow_flow(cur_dist, fx, fy, dir=direction)
            i += 1


    def run_experiment(self):
        self.dates = []
        self.date = 0
        self.velocities = []
        self.dist = []
        self.points = []
        if self.step_range[0] < 0:
            self.get_stream(direction=-1, points=min(self.step_range[0], self.step_range[0]-self.step_range[1]))

        if self.step_range[1] > 0:
            self.get_stream(direction=1, points=min(self.step_range[1], self.step_range[1]-self.step_range[0]))


    def get_points(self, overlap_ds=False, include_all=False, index='dist'):
        if self.dist == []:
            self.run_experiment()

        if type(overlap_ds) != bool:
            gpd_df = gpd.GeoDataFrame({'dist_from_grndline': self.dist, 'vel_dates': self.dates}, geometry=self.points, crs='EPSG:3031')
            if include_all:
                all_p = gpd_df.copy(deep=True)
            new_df = gpd.sjoin_nearest(overlap_ds, gpd_df, max_distance=self.max_dist)

            
            new_df.set_index('geometry')
            new_df = new_df.drop(columns=['latitude', 'longitude', 'index_right', 'trend', 'date', 'uncert'])
            new_df = new_df[~new_df.index.duplicated(keep='first')]
            self.points = list(new_df['geometry'])
            self.dist = list(new_df['dist_from_grndline'])
            self.dates = list(new_df['vel_dates'])


        df = xr.Dataset({
            'date': (('dist'), self.dates),
            'geometry': (('dist'), self.points),
            }, coords={
            'dist': self.dist}).drop_duplicates(dim='dist')


        

        point_dists = np.array(list(range(self.step_range[0], self.step_range[1]))) * self.step_dist

        points = []
        labels = []

        df = df.sortby(df['dist'])
        
        for x in point_dists:
            selected_point = df.sel(dist=x, method='nearest')
            points.append([selected_point['geometry'].values.max().y, selected_point['geometry'].values.max().x])
            if self.label_type == 'dist':
                labels.append(int(selected_point.dist))
            elif self.label_type == 'date':
                labels.append(selected_point['date'].values)
            

        if include_all:
            return points, labels, all_p


        return points, labels

        