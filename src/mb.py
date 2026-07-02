from utils import * 
from file_manager import IPRManager ,REMATileManager, BedmapManager, GeoidManager, VelocityManager, SMBManager, AvgXVelManager, AvgYVelManager
import geopandas as gpd
import numpy as np
import pandas as pd
from pointwise import FlowProfile
import math
from shapely.ops import linemerge
import datetime
import matplotlib.pyplot as plt
import rioxarray # used by xarray for some reason, must be first
import xarray as xr


'''
REMA & Bedmap:
   id     Date_1     Date_2     Date_3  ...                           path IPR_agreement                                           geometry  discharges
0   1 2026-01-10 2026-01-11 2026-02-27  ...  /home/mallory/gl_feb_2026.shp          True  MULTILINESTRING ((135.35726 -66.10097, 135.346...   29.646589
1   2 2026-01-10 2026-01-11 2026-02-03  ...                        gl4.shp         False  MULTILINESTRING ((135.38143 -66.10341, 135.362...   28.852910
2   3 2026-02-03 2026-02-04 2026-02-27  ...                         gl.shp          True  MULTILINESTRING ((135.35854 -66.10094, 135.349...   29.694725
3   4 2026-02-03 2026-02-04 2026-03-11  ...                        gl3.shp         False  MULTILINESTRING ((135.39237 -66.10397, 135.381...   29.173067
4   5 2026-02-27 2026-02-28 2026-03-11  ...                        gl2.shp          True  MULTILINESTRING ((135.39282 -66.10375, 135.383...   29.856185

Equilibrium:
   id     Date_1     Date_2     Date_3  ...                           path IPR_agreement                                           geometry  discharges
0   1 2026-01-10 2026-01-11 2026-02-27  ...  /home/mallory/gl_feb_2026.shp          True  MULTILINESTRING ((135.35726 -66.10097, 135.346...   17.684126
1   2 2026-01-10 2026-01-11 2026-02-03  ...                        gl4.shp         False  MULTILINESTRING ((135.38143 -66.10341, 135.362...   15.323299
2   3 2026-02-03 2026-02-04 2026-02-27  ...                         gl.shp          True  MULTILINESTRING ((135.35854 -66.10094, 135.349...   18.220929
3   4 2026-02-03 2026-02-04 2026-03-11  ...                        gl3.shp         False  MULTILINESTRING ((135.39237 -66.10397, 135.381...   14.813213
4   5 2026-02-27 2026-02-28 2026-03-11  ...                        gl2.shp          True  MULTILINESTRING ((135.39282 -66.10375, 135.383...   17.807347
'''

class MBCalculation():
    def __init__(self, xlims, ylims, flags, method='flux'):

        if method == 'flux':
            self.thickness_calculator = ThicknessIPR(xlims, ylims, flags)
        else:
            self.thickness_calculator = ThicknessEquilibrium(xlims, ylims, flags)
        self.flux_calculator = VelocityFlux(xlims, ylims, flags)
        self.SMB = SMBManager(xlims, ylims, flags, 'smb')
        self.flags = flags
        if method == 'gl':
            self.results = gpd.read_file(GL_GPKG_manual)
        elif method == 'flux':
            self.results = gpd.read_file(SHAPEFILES['fluxgate']) #

        self.vels = []
        self.thickness = []
        self.lengths = []
        pass

    def calculate_discharge(self):
        final_df = self.results
        return final_df

    def get_discharge_results(self, id = 1, year = 2019):


        df = self.results[self.results['id'] == id]
        

        thickness = self.thickness_calculator.get_thickness(df)
        vels = self.flux_calculator.get_velocity(df, year=year)

        if type(vels) != gpd.GeoDataFrame:
            return
        if len(vels['velx'].dropna()) != 0:
            vels.to_file(
                'DISCHARGE_SAMPLE.gpkg'
            )


        discharge = (vels['discharge_vel'] * thickness['thickness'] * thickness['lens'] * GLACIAL_ICE_DENSITY) / 1e12
        df['discharge'] = discharge
        print(vels['discharge_vel'])
        print(thickness['thickness'])
        print(thickness['lens'])
        print(np.nansum(discharge))

        self.vels.append(np.nansum(vels['discharge_vel']))
        self.thickness.append(np.nansum(thickness['thickness']))
        self.lengths.append(np.nansum(thickness['lens']))
        
        '''discharges.append(np.nansum(discharge))

        df['discharge'] = discharges

        df['discharges_total_vel'] = discharges
        self.calculate_discharge()'''

        return np.nansum(discharge)
    

    def plot_MB(self, ids=[0, 1, 2, 3, 4, 5], title='All GL Locations'):


        smb_df = self.SMB.get_surface_balance_df()


        for id in ids:
            self.vels = []
            self.thickness = []
            self.lengths = []

            discharges = []
            discharges_dt = []
            for dt in smb_df.dt:
                dis = self.get_discharge_results(id=id, year = dt.year)
                if dis == 0 or dis == None:
                    #print(dt.year)
                    #input(str(id))
                    continue
                discharges.append(dis)
                discharges_dt.append(datetime.datetime(dt.year, 1, 1))

            print()
            print()
            print()
            print()
            print(discharges)
            discharges = np.array(discharges)
            discharges_dt = np.array(discharges_dt)[discharges != np.nan]
            discharges = discharges[discharges != np.nan]
            print(discharges)
            #input("WAITING FOR INPUT")
            plt.plot(discharges_dt, discharges, label='Yearly Discharge, GL=' + str(id))


            #plt.plot(discharges_dt, self.vels, label='Total Velocity')
            #plt.plot(discharges_dt, self.thickness, label='Total Thickness')
            #plt.plot(discharges_dt, self.lengths, label='Total length')



        plt.plot(smb_df['dt'], smb_df['smb'], label='Yearly SMB')
        plt.legend()
        plt.xlabel('Date')
        plt.ylabel('Sum Total Mass (GT/yr)')
        plt.title(title)
        plt.savefig(MB_OUTPUT + title + self.flags.sources_v()[0][0] + '_' + str(self.thickness_calculator) +'_SMBs.png')



        plt.savefig(
            'MB_ALL.png'
        )

        return





class VelocityFlux(FlowProfile):
    def __init__(self, xlims, ylims, flags):
        super().__init__(flags, xlims, ylims, 
                         {'point': [0,0], 'type':'fl', 'point_range':[0,0], 'point_spacing': 0},
                          'pink')
        self.xlim = xlims
        self.ylim = ylims

    def get_velocity(self, gdp, year = None):
        if year != None:
            new_flags = self.flags.copy()
            new_flags.YEARSTART = year
            new_flags.YEAREND = year + 1
            self.flags = new_flags

        

        self.velx_manager = VelocityManager(self.xlim, self.ylim, self.flags, 'velx')
        self.vely_manager = VelocityManager(self.xlim, self.ylim, self.flags, 'vely')
        self.avg_velx_manager = AvgXVelManager(self.xlim, self.ylim, self.flags, 'velx')
        self.avg_vely_manager = AvgYVelManager(self.xlim, self.ylim, self.flags, 'vely')

        out_x = self.velx_manager.get_ouput_files()
        out_y = self.vely_manager.get_ouput_files()
        avg_out_x = self.avg_velx_manager.get_ouput_files()
        avg_out_y = self.avg_vely_manager.get_ouput_files()
        
        #input("INPUT")
        if type(out_y) != xr.Dataset or type(out_x) != xr.Dataset:
            #input("BAD")
            return
        #print(out_y['band_data'])
        #print(out_x['band_data'])
        
        avg_vel_df = gl_geotiff_s_join(avg_out_x, gdp, label='velx')
        avg_vel_df = avg_vel_df.merge(gl_geotiff_s_join(avg_out_y, gdp, label='vely'))
        

        vel_df = gl_geotiff_s_join(out_x, gdp, label='velx')
        vel_df = vel_df.merge(gl_geotiff_s_join(out_y, gdp, label='vely'))
        vel_df = vel_df.combine_first(avg_vel_df) # fill with averages

        vel_df['vel_angle'] = np.degrees(np.arctan2(vel_df['vely'], vel_df['velx']))  % 360
        vel_df['vel_angle_diff'] = ((vel_df['angle'] - vel_df['vel_angle']) % 360) #% 360
        vel_df['total_vel'] = overall_velocity(vel_df['velx'], vel_df['vely'])
        vel_df['discharge_velx'] = np.cos(vel_df['vel_angle_diff']) * vel_df['velx']
        vel_df['discharge_vely'] = np.sin(vel_df['vel_angle_diff']) * vel_df['vely']
        #vel_df['discharge_vel'] = vel_df['discharge_velx'] + vel_df['discharge_vely']
        vel_df['discharge_vel'] = np.abs(np.sin(np.deg2rad(vel_df['vel_angle_diff'])) * vel_df['total_vel'])
        #vel_df['discharge_vel'][vel_df['discharge_vel'] < 0] = 0 
        #vel_df['discharge_vel2'] = np.sin(vel_df['vel_angle_diff']) * vel_df['total_vel']
        
        print(vel_df)
        return vel_df






class ThicknessCalculation(FlowProfile):
    def __init__(self, xlims, ylims, flags):
        super().__init__(flags, xlims, ylims, 
                         {'point': [0,0], 'type':'fl', 'point_range':[0,0], 'point_spacing': 0},
                          'ocean')
        self.FIRNAIR = 20
        pass




    def get_thickness(self, gdp):
        pass

class ThicknessIPR(ThicknessCalculation):
    def __init__(self, xlims, ylims, flags):
        super().__init__(xlims, ylims, flags)
        self.IPR = IPRManager(xlims, ylims, flags, 'ipr')
        self.max_dist = 50

    def __str__(self):
        return 'IPR'

    def get_thickness(self, gdp):
        out = self.IPR.get_ouput_files()
        out = gl_geotiff_s_join(out, gdp, column_of_interest='THICK', label='thickness')
        return out
        

class ThicknessEquilibrium(ThicknessCalculation):
    def __init__(self, xlims, ylims, flags):
        super().__init__(xlims, ylims, flags)
        self.REMA = REMATileManager(xlims, ylims, flags, 'rema')
        self.geoid = GeoidManager(xlims, ylims, flags, '2008')
        pass

    def __str__(self):
        return 'equilibrium'

    def get_thickness(self, gdp):
        rema = self.REMA.get_ouput_files()
        geoid = self.geoid.get_ouput_files()

        surface_elevation = gl_geotiff_s_join(rema, gdp, label='elev')
        geoid_elevation = gl_geotiff_s_join(geoid, gdp, label='geoid')

        surface_elevation['geoid'] = geoid_elevation['geoid']
        surface_elevation['elev'] -= self.FIRNAIR
        surface_elevation['elev'] += geoid_elevation['geoid']
        
        surface_elevation['thickness'] = np.abs((surface_elevation['elev'] * WATER_DENSITY) / (WATER_DENSITY - GLACIAL_ICE_DENSITY))
        return surface_elevation


class ThicknessBedmapREMA(ThicknessCalculation):
    def __init__(self, xlims, ylims, flags):
        super().__init__(xlims, ylims, flags)

        self.REMA = REMATileManager(xlims, ylims, flags, 'rema')
        self.bed = BedmapManager(xlims, ylims, flags, 'bedmachine')
        pass

    def __str__(self):
        return 'bedmapREMA'

    def get_thickness(self, gdp):
        rema = self.REMA.get_ouput_files()
        bed = self.bed.get_ouput_files()

        surface_elevation = gl_geotiff_s_join(rema, gdp, label='elev')
        bed_elevations = gl_geotiff_s_join(bed, gdp, label='bed')
        surface_elevation['bed'] = bed_elevations['bed']

        surface_elevation['thickness'] = np.abs(surface_elevation['elev'] - bed_elevations['bed'])

        surface_elevation['thickness'] -= self.FIRNAIR
        return surface_elevation



def gl_geotiff_s_join(out, points, column_of_interest='band_data', record_angle = True, label='vals', dtype=float):
    
    dists = []
    values = []
    ids = []
    lats = []
    lons = []
    lens = []
    angle = []
    #out = out.to_crs('EPSG:4326')
    progress = LoadingBar()
    points = points.to_crs('EPSG:3031')
    line_spacing_m = 100

    for line in points.itertuples():
        gl = max(line.geometry.geoms, key=lambda line: line.length)
        
        distances = np.arange(0, gl.length, line_spacing_m)
        poses = [gl.interpolate(distance) for distance in distances]
        last_pos = None
        if type(out) == gpd.geodataframe.GeoDataFrame:
            poses_gdf = gpd.GeoDataFrame({'geometry': poses})
            poses_gdf = poses_gdf.set_crs('EPSG:3031')
            print(gpd.sjoin_nearest(poses_gdf, out,how='left'))
            values.extend(gpd.sjoin_nearest(poses_gdf, out, max_distance=line_spacing_m*4, how='left')[column_of_interest].astype(dtype=dtype)[1:-1])
            print(len(values))

        for i, pos in enumerate(poses):
            if i == len(poses) - 1 or i == 0:
                last_pos = pos
                continue
            next_pos = poses[i+1]
            dists.append(i)
            if type(out) != gpd.geodataframe.GeoDataFrame:
                values.append(dtype(out.sel(x=pos.x, y=pos.y, method='nearest')[column_of_interest].mean()))
            ids.append(line.id)
            lats.append(pos.y)
            lons.append(pos.x)
            lens.append(overall_velocity(next_pos.x - last_pos.x, next_pos.y - last_pos.y))
            if record_angle:
                angle.append(math.degrees(math.atan2(next_pos.y - last_pos.y, next_pos.x - last_pos.x))  % 360)
            last_pos = pos
            progress.load_bar(i, len(poses))

    #values = np.nan_to_num(values)
    #to_fill_with = np.nanmean(values)
    #values = np.array(values)
    #values[values == np.nan] = to_fill_with

    if not record_angle:
        df = {
            "dists": dists,
            label: values,
            "id": ids,
            "lens": lens,
            "latitude": lats,
            "longitude": lons,
        }
    else:
        df = {
            "dists": dists,
            label: values,
            "id": ids,
            "lens": lens,
            "angle": angle,
            "latitude": lats,
            "longitude": lons,
        }

    geom = []
    for x in range(len(df['latitude'])):
        geom.append(pointify({'latitude': df['latitude'][x], 'longitude': df['longitude'][x]}))
    df['geometry'] = geom #df.apply(pointify, axis=1)
    df = gpd.GeoDataFrame(df, geometry='geometry')

    df = df.set_geometry('geometry')
    df = df.set_crs('EPSG:3031')
    

    df = df.sort_values('dists')
    df.to_file(f'TEST DATA{label}.gpkg')
    return df