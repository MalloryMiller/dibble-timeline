import datetime
from utils import *
from file_manager import GravimetryManager, ElevationManager, VelocityManager, IPRManager, FirnAirManager

import geopandas as gpd
import rioxarray # used by xarray for some reason, must be first
import xarray as xr
from shapely.geometry import Point
import pandas as pd
import numpy as np
from matplotlib import cm
import matplotlib.colors as mcolors
import matplotlib as mpl
from photutils.aperture import CircularAperture

from plotting import Plotting

class Pointwize():
    def __init__(self, flags, xlim, ylim, points, data, pt_range = [-2, 4], point_spacing=17000, change=True, streamwise=True, time_diff_year = 2020):
        self.flags = flags
        self.xlim = xlim
        self.ylim = ylim
        self.points = points
        print(points)
        self.point_label = str(int(points[0])) + '_' + str(int(points[1]))
        self.data = data
        self.change = change
        self.time_diff_year = time_diff_year
        self.pt_range = pt_range
        self.labels = []


        self.max_dist = 100
        self.label_type = flags.label_type()


        if streamwise:
            
            s = StreamFlow(xlim, ylim, flags, self.points, point_spacing, pt_range, max_dist=self.max_dist, label_type = self.label_type)
            self.point_spacing = point_spacing
            e = ElevationManager(xlim, ylim, flags, 'elev')
            if self.data == 'gl':
                self.points, self.labels, self.fl = s.get_points(e.sample_source, include_all=True)
            else:
                self.points, self.labels = s.get_points(e.sample_source)
                
        max_dist = max(max(self.labels), -min(self.labels))
        self.norm = mcolors.Normalize(vmin=-max_dist, vmax=max_dist)
        self.cm = cm.get_cmap('managua', 256)

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
            date = np.datetime64(date).astype(datetime.datetime)

        if type(date) == datetime.date:
            date = datetime.datetime(date.year, date.month, date.day)
        return date


    def gpd_geom_match(self, out, index, column_of_interest = 'elev', add_result=True, date_col='date'):

        '''rename_for_datasource = {'elev': {'_xerr': '_xerr'},
                                 'gl': {}}
        out = out.rename(columns=rename_for_datasource[self.data])'''
        
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
            val_arr = val_arr.sort_values(by=date_col)
            val_arr = val_arr.reset_index(drop=True)
            

            val_arr = val_arr.iloc[len(val_arr)//2]
            
            
            val = val_arr[column_of_interest]


            if np.isnan(val):
                continue
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


        if type(time[0]) == str:
            for x in range(len(time)):
                time[x] = np.datetime64(time[x])
        time = np.array(time).astype(datetime.datetime)
        data = np.array(data)
        sources = np.array(sources)

        if len(data) == 0:
            return

        if self.change:
            tiem, data = self.gpd_time_difference(time, data)

        df_contents = {'time': time, self.data: data}
        if len(sources):
            df_contents['sources'] = sources
        for y in other_items.keys():
            df_contents[y] = other_items[y]

        df = pd.DataFrame(df_contents)
        
        if add_result:
            if self.get_label(index) not in self.results.keys():
                self.results[self.get_label(index)] = pd.DataFrame()
                
            if len(self.results[self.get_label(index)]) == 0:
                self.results[self.get_label(index)] = df
            self.results[self.get_label(index)] = pd.concat([self.results[self.get_label(index)], df], axis=0, ignore_index=True)
        else:

            self.results[self.get_label(index)] = df

    
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


    def gpd_time_difference(self, time, data):
        time = np.array(time)
        data = np.array(data)

        ref_datetime = datetime.datetime(self.time_diff_year, 1, 1)

        if type(self.change) != bool and 'interp' in self.change and ref_datetime not in time and np.datetime64(ref_datetime) not in time:
            ref_pre = np.array(sorted(time[data != np.nan], key=lambda x: abs(np.datetime64(x) - np.datetime64(ref_datetime))))
            ref_post = np.array(sorted(time[data != np.nan], key=lambda x: abs(np.datetime64(x) - np.datetime64(ref_datetime))))
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
            if self.time_diff_year == None:
                ref_time = min(time[data != np.nan])
            elif type(self.time_diff_year) == int:
                ref_time = sorted(time[data != np.nan], key=lambda x: abs(x - datetime.datetime(self.time_diff_year, 1, 1)))[0]

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
        sm = mpl.cm.ScalarMappable(norm=self.norm, cmap=self.cm)


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


    def get_dataset_display_range(self, dataset):
        dataset= np.array(dataset)
        dataset = dataset[~np.isnan(dataset)]
        if len(dataset) == 0:
            return False

        ymin = dataset.min()
        ymax = dataset.max()

        ypadd = 0.05 * (ymax - ymin)
        if np.isnan(ypadd):
            return False
        return [ymin - np.abs(ypadd), ymax + np.abs(ypadd)]

    def plot_elevation_summary(self, fig, ax):
            
        sm = mpl.cm.ScalarMappable(norm=self.norm, cmap=self.cm)
        color = sm.to_rgba(0)

        fm = IPRManager(self.xlim, self.ylim, self.flags, self.data)
        out = fm.get_ouput_files()
        out = df_ref = gpd.sjoin_nearest(self.fl, out, max_distance=self.max_dist*10)

        out = out.sort_values('dist_from_grndline')
        
        bad_out = out.copy(deep=True)
        out['real_elevation1'] = out['real_elevation1'].where(out['dist_from_grndline'] < 0)


        ax.plot(bad_out['real_elevation1'] - bad_out['THICK'], bad_out['dist_from_grndline'].values, marker= 'None', color=color, label='Bottom', ls = ':', alpha=0.5)
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





class StreamFlow():
    def __init__(self, xlims, ylims, flags, starting_pos, step_dist, step_num, date_steps = STREAM_PLOT_STEPS, max_dist = 500, label_type = 'dist'):
        f = Flags()
        f.add('-'+str(flags.YEARSTART)+'-'+str(flags.YEAREND))
        f.add('-itslive')
        self.fmx = VelocityManager(xlims, ylims, f, 'velx')
        self.fmy = VelocityManager(xlims, ylims, f, 'vely')

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

        

        
    


