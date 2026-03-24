import datetime
from utils import *
from file_manager import GravimetryManager, ElevationManager, VelocityManager

import geopandas as gpd
import rioxarray # used by xarray for some reason, must be first
import xarray as xr
from shapely.geometry import Point
import pandas as pd
import numpy as np
from matplotlib import cm
import matplotlib.colors as mcolors
import matplotlib as mpl

from plotting import Plotting

class Pointwize():
    def __init__(self, flags, xlim, ylim, points, data, pt_range = [-2, 4], point_spacing=17000, change=True, streamwise=True):
        self.flags = flags
        self.xlim = xlim
        self.ylim = ylim
        self.points = points
        print(points)
        self.point_label = str(int(points[0])) + '_' + str(int(points[1]))
        self.data = data
        self.change = change
        self.pt_range = pt_range
        self.labels = []


        self.max_dist = 50
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
            print(str(self.point_label) + ".gpkg")
            df_ref.to_file(POINTWISE_OUTPUT_LOCATION + str(self.point_label) + ".gpkg", layer="geometry", driver="GPKG")
        return df_ref
    
    
    def get_label(self, index, style=None):
        if style == None:
            style = self.label_type

        print(style)

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



    def get_gl_set(self, date_cols=['Date_4', 'Date_1', 'Date_2', 'Date_3']):
        gdf = gpd.read_file(GL_GPKG)
        gdf['date'] = gdf[date_cols].mean(axis=1)
        gdf = gdf.to_crs(3031)
        self.gpd_geom_match(gdf, self.fl, column_of_interest = 'dist_from_grndline', date_col='date')
        self.results[''] = self.results[''].sort_values(by='time')
        print(self.results[''])
        pass



    def gpd_geom_match(self, out, index, column_of_interest = 'elevation', add_result=False, date_col='date'):
        if type(index) == int:
            p = self.points[index]
            df_ref = self.create_point_df([p])
        else:
            df_ref = index
            generate_labels = True

        df_ref = gpd.sjoin(df_ref, out, distance=self.max_dist, predicate='dwithin')
        if self.data == 'gl':
            df_ref.to_file(POINTWISE_OUTPUT_LOCATION + str(self.point_label) + "_gl.gpkg", layer="geometry", driver="GPKG")
        
        time = []
        sources = []
        data = []

        for x in df_ref[date_col].unique():
            val = df_ref[df_ref[date_col] == x][column_of_interest].dropna().mean()
            if np.isnan(val):
                continue
            if 'sources' in df_ref.columns:
                src = df_ref[df_ref[date_col] == x]['sources'][0]
                if type(df_ref[df_ref[date_col] == x]['sources'][0]) != str:
                    src = list(src.values)[0]
                sources.append(src)

            
            data.append(val)
            time.append(x)

        time = np.array(time)
        data = np.array(data)
        sources = np.array(sources)

        if len(data) == 0:
            return

        if self.change:
            ref_time = time.min()
            data = data - data[time == ref_time]

        if len(sources):

            df = pd.DataFrame({'time': time, 'sources': sources,
                                            self.data: data})
        else:
            df = pd.DataFrame({'time': time,
                                        self.data: data})
        
        if add_result:
            if len(self.results[self.get_label(index)]) == 0:
                self.results[self.get_label(index)] = df
            self.results[self.get_label(index)] = pd.concat([self.results[self.get_label(index)], df], axis=0, ignore_index=True)
        else:

            self.results[self.get_label(index)] = df

    
    def geotiff_geom_match(self, out, index, column_of_interest = 'band_data', add_result=False):
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
        
        if 'sources' in df.variables:
            df = pd.DataFrame({'time': new_dates, 'sources': df['sources'],
                               self.data: df[column_of_interest]})

        else:
            df = pd.DataFrame({'time': new_dates,
                                self.data: df[column_of_interest]})
            

        if self.change:
            df = self.geotiff_time_difference(df)
            df = df.dropna()
            ref_time = df['time'].min()
            data = df.copy(deep=True)
            df[self.data] = df[self.data] - data[self.data][data['time'] == ref_time]
        
        if add_result:
            if len(self.results[self.get_label(index)]) == 0:
                self.results[self.get_label(index)] = df
            self.results[self.get_label(index)] = pd.concat([self.results[self.get_label(index)], df], axis=0, ignore_index=True)
        else:
            self.results[self.get_label(index)] = df


    def geotiff_time_difference(self, df):
        zero = df[df['time'] == df.time.min()][self.data].values[0]
        df[self.data] = df[self.data] - zero
        return df


    def plot_time_series(self, fig, ax, rema=False, unified_line=False):
        if not self.results:
            self.get_data(rema)


        shapes = ['s', '^', 'D']
        sm = mpl.cm.ScalarMappable(norm=self.norm, cmap=self.cm)
        if 'sources' in self.results[list(self.results.keys())[0]].columns:
            for i, s in enumerate(self.results[list(self.results.keys())[0]]['sources'].unique()):
                ax.plot([], [], label = s, marker= shapes[i], color=sm.to_rgba(0), linestyle='None')

        

        for j, p in enumerate(self.results.keys()):
            self.results[p] = self.results[p].dropna()
            ls = 'None'
            if unified_line:
                ax.plot(self.results[p]['time'], 
                            self.results[p][self.data].values, marker= 'None', color=sm.to_rgba(self.labels[j]))
            else:
                ls = 'solid'
            
            if 'sources' in self.results[p].columns:
                for i, s in enumerate(self.results[p]['sources'].unique()):
                    cur = self.results[p][self.results[p]['sources'] == s]
                    
                    ax.plot(cur['time'], 
                            cur[self.data].values, marker= shapes[i], color=sm.to_rgba(self.labels[j]), linestyle=ls)
            else:
                ax.plot(self.results[p]['time'], 
                        self.results[p][self.data].values, label = p, marker= 'o', color=sm.to_rgba(self.labels[j]), linestyle=ls)


    def get_data_rema(self):

        for p in range(len(self.points)):
            if self.get_label(p) not in self.results.keys():
                self.results[self.get_label(p)] = pd.DataFrame({})

        filemanager = ElevationManager(self.xlim, self.ylim, self.flags, self.data)
        
        for p, point in enumerate(self.points):
            new_df = filemanager.get_point_data(point)
            if self.change:
                new_df = self.geotiff_time_difference(new_df)
            self.results[self.get_label(p)] = pd.concat([self.results[self.get_label(p)], new_df])
            self.results[self.get_label(p)] = self.results[self.get_label(p)].sort_values('time')


    def get_data(self, rema=False):

        type_info = {
            'vel': 'band_data',
            'grav': 'dm',
            'elev': 'elevation',
        }
        
        fms = {
            'vel': VelocityManager,
            'grav': GravimetryManager,
            'elev': ElevationManager,
        }

        if self.data == 'gl':
            return self.get_gl_set()

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
        cur_vx = dir * float(fx.sel(x=self.pos[0], y=self.pos[1], method='nearest')['band_data'].mean())
        cur_vy = dir * float(fy.sel(x=self.pos[0], y=self.pos[1], method='nearest')['band_data'].mean())
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

        

        
    


