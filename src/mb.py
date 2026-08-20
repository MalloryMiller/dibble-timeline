from utils import * 
from file_manager import IPRManager ,REMATileManager, GravimetryManager, BedmapManager, GeoidManager, VelocityManager, SMBManager, ATL15SMBManager, SingleFirnSourceManager, AvgXVelManager, AvgYVelManager, REMATileSlopeManager
import geopandas as gpd
import numpy as np
import pandas as pd
from pointwise import FlowProfile, PolyFlowHybridLine
import math
from shapely.ops import linemerge
import shapely
import datetime
import matplotlib.pyplot as plt
import rioxarray # used by xarray for some reason, must be first
import xarray as xr
import csv

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
        self.xlims = xlims
        self.ylims = ylims
        self.flags = flags

        if method == 'flux':
            self.thickness_calculator = ThicknessIPR(xlims, ylims, flags)
            self.depth_correct_velocity = True

        else:
            self.thickness_calculator = ThicknessEquilibrium(xlims, ylims, flags)
            self.depth_correct_velocity = False

        self.flux_calculator = VelocityFlux(xlims, ylims, flags)
        self.SMB = SMBManager(xlims, ylims, flags, 'smb')
        self.atl_MB = ATL15SMBManager(xlims, ylims, flags, 'ATL15')
        self.firn = SingleFirnSourceManager(xlims, ylims, flags)
        self.grav = GravimetryManager(xlims, ylims, flags)
        self.slope_manager = SlopeManager(xlims, ylims, flags)
        self.flags = flags
        if method == 'gl':
            self.results = gpd.read_file(GL_GPKG_manual)
        elif method == 'flux':
            self.results = gpd.read_file(SHAPEFILES['fluxgate']) #
            
        self.method = method
        self.vels = []
        self.thickness = []
        self.lengths = []
        pass

    def calculate_discharge(self):
        final_df = self.results
        return final_df

    def get_discharge_results(self, id = 1, year = 2019, get_exclusion=False, get_extra_mask=False):


        df = self.results[self.results['id'] == id]

        if get_extra_mask:
            try:
                first_vertex = shapely.get_coordinates(df.geometry.head(1))[0]
                last_vertex = shapely.get_coordinates(df.geometry.head(1))[1]
            except:
                return None, None
            
            
            extra_mask = PolyFlowHybridLine(self.xlims, self.ylims, self.flags, 
                                [list(reversed(first_vertex)),
                                list(reversed(last_vertex))], [-2500, 500]).get_polygon(include_og_line=False)
        else:
            extra_mask = None

        if get_exclusion:
            try:
                first_vertex = shapely.get_coordinates(df.geometry.head(1))[0]
                last_vertex = shapely.get_coordinates(df.geometry.head(1))[1]
            except:
                return None, None
            
            
            exclusion_mask = PolyFlowHybridLine(self.xlims, self.ylims, self.flags, 
                                [list(reversed(first_vertex)),
                                list(reversed(last_vertex))], [0, 500]).get_polygon(include_og_line=True)
        else:
            exclusion_mask = None

        thickness = self.thickness_calculator.get_thickness(df)
        vels = self.flux_calculator.get_velocity(df, year=year)
        slopes = self.slope_manager.get_slopes(df)

        if type(vels) != gpd.GeoDataFrame:
            return None, exclusion_mask, extra_mask
        if len(vels['velx'].dropna()) != 0:
            vels.to_file(
                'DISCHARGE_SAMPLE.gpkg'
            )

        vel_discharges = []
        if self.depth_correct_velocity:
            for v in range(len(vels['total_vel'])):
                vel_discharges.append(self.depth_adjusted_velocity_discharge(vels['discharge_vel'][v], thickness['thickness'][v], slopes['slope'][v]))
        else:
            for v in range(len(vels['total_vel'])):
                vel_discharges.append(vels['discharge_vel'][v] * thickness['thickness'][v])


        #discharge = (vels['discharge_vel'] * thickness['thickness'] * thickness['lens'] * GLACIAL_ICE_DENSITY) / 1e12
        discharge = (vel_discharges * thickness['lens'] * GLACIAL_ICE_DENSITY) / 1e12
        df['discharge'] = discharge

        self.vels.append(np.nansum(vels['discharge_vel']))
        self.thickness.append(np.nansum(thickness['thickness']))
        self.lengths.append(np.nansum(thickness['lens']))
        
        '''discharges.append(np.nansum(discharge))

        df['discharge'] = discharges

        df['discharges_total_vel'] = discharges
        self.calculate_discharge()'''

        return np.nansum(discharge), exclusion_mask, extra_mask
    

    def depth_adjusted_velocity_discharge_noslip(self, velocity, thickness, slope, plot=False):
        '''
        https://courses.washington.edu/ess431/LECTURES/LECTURE_2018/vertical_profile_ice_sheet_derivation.pdf
        '''

        velocities = []
        step_size = 1
        n = 3

        for x in range(round(thickness) // step_size):
            s = (velocity * (1 - ((1 - (x / thickness)) ** (n+1)))) * step_size
            velocities.append(s)

        if plot:
            fig, ax = plt.subplots()

            ax.plot(velocities, list(range(round(thickness)//step_size)), label='Ice Speed')
            plt.xlabel("Velocity (m/yr)")
            plt.ylabel("Height (m)")
            plt.title("Velocity by Depth")
            fig.savefig('velocity_profile.pdf')
            plt.close(fig)

        discharge = sum(velocities)
        
        return discharge


    def fast_depth_adjusted_velocity_discharge(self, velocity, thickness, slop, plot=False):
        factor = 1.2505

        return velocity*thickness / factor

    

    def depth_adjusted_velocity_discharge(self, velocity, thickness, slope, plot=False):
        velocities = []
        step_size = 1

        n = 3
        shape_factor= 1 #0.806 # https://books.google.com/books?hl=en&lr=&id=Jca2v1u1EKEC&oi=fnd&pg=PP1&ots=KOMQ32smmd&sig=DSxwoIBC_qXWTiShNp503GSLRHw#v=onepage&q=shape%20factor&f=false
        
        A = 38e-25 # A(T=0)

        tau = shape_factor * GLACIAL_ICE_DENSITY * GRAVITY * thickness * slope

        '''
        velocity: 89.26762319651945 thickness: 1323.03 slope: 0.8546802401542664 tau: 6226166.467255807
        creep: 0.6067160408266269
        slip: 88.66090715569283
        '''


        print('velocity:', velocity, 'thickness:', thickness, 'slope:', slope, 'tau:', tau)

        creep_speed = ((2 * A)  / (n+1)) * ((tau**n)*thickness)
        slip_speed = velocity - creep_speed

        if slip_speed < 0: #overestimated velocity, assume no slip
            creep_speed = velocity
            slip_speed = 0

        #('creep:', creep_speed)
        #print('slip:', slip_speed)

        for x in range(round(thickness) // step_size):
            s = (slip_speed + (creep_speed * (1 - ((1 - (x / thickness)) ** (n+1))))) * step_size #(slip_speed + ((creep_speed * (1 - ((1 - (x / thickness)) ** (n+1)))))) * step_size
            velocities.append(s)

        if plot:
            fig, ax = plt.subplots()

            ax.plot(velocities, list(range(round(thickness)//step_size)), label='Ice Speed')
            plt.xlabel("Velocity (m/yr)")
            plt.ylabel("Height (m)")
            plt.title("Velocity by Depth")
            fig.savefig('velocity_profile.pdf')
            plt.close(fig)
        
        return sum(velocities)

    def plot_MB(self, ids=[0, 1, 2, 3, 4, 5], title='All GL Locations', seperate=False):
        csv_text = 'title,σ SMB,SMB,D,σ D,'
        for x in range(self.flags.YEARSTART, self.flags.YEAREND):
            csv_text += str(x) + ','
        csv_text += '\n'


        smb_df = self.SMB.get_surface_balance_df(plot=False)
        elevation_mb = self.atl_MB.get_surface_balance_df(True)
        grav_mb = self.grav.get_surface_balance_df(True)
        #firn_m = self.firn.get_surface_balance_df(True)
        

        fig, ax = plt.subplots()
        if not seperate:
            ax.axhline(0, color='black', label='Equilibrium', linewidth=2)
        #print(elevation_mb)
        ax.plot(elevation_mb['dt'], elevation_mb['smb'], label='ATL15-derived Total Mass Balance')
        ax.plot(grav_mb['dt'], grav_mb['smb'], label='GRACE-derived Total Mass Balance')

        for id in ids:
            print("ID:", id)
            self.vels = []
            self.thickness = []
            self.lengths = []

            discharges = []
            discharges_dt = []
            first_run = True

            smb_df = smb_df[smb_df['smb'] != 0]

            for dt in smb_df.dt:
                print("dt:", dt)
                if first_run:
                    dis, exclude, extra_mask = self.get_discharge_results(id=id, year = dt.year, get_exclusion = first_run, get_extra_mask= first_run and self.method == 'flux')
                    first_run = exclude == None
                else:
                    dis, _, __ = self.get_discharge_results(id=id, year = dt.year, get_exclusion = first_run)

                if dis == 0 or dis == None:
                    discharges.append(np.nan)
                    discharges_dt.append(datetime.datetime(dt.year, 6, 1))
                    continue
                discharges.append(dis)
                discharges_dt.append(datetime.datetime(dt.year, 6, 1))


            discharges = np.array(discharges)

            if self.method == 'flux':
                smb_df = self.SMB.get_surface_balance_df(extra_mask=extra_mask, exclusion=exclude, plot=False)
            else:
                smb_df = self.SMB.get_surface_balance_df(exclusion=exclude, plot=False)
            #print(smb_df)
            smb_df = smb_df[smb_df['smb'] != 0]

            #print(discharges)
            result = smb_df['smb'] - discharges
            result_dt = np.array(discharges_dt)[result != np.nan]
            result = result[result != np.nan]
            #print(result)

            discharges_dt = np.array(discharges_dt)[discharges != np.nan]
            discharges = discharges[discharges != np.nan]
            #input("WAITING FOR INPUT")
            #plt.plot(discharges_dt, discharges, label='Yearly Discharge, ID=' + str(id))

            csv_text += title + " (" + str(id) + '),'
            csv_text += str(np.nanstd(smb_df['smb'])) + ','
            csv_text += str(np.nanmean(smb_df['smb'])) + ','
            csv_text += str(np.nanmean(discharges)) + ','
            csv_text += str(np.nanstd(discharges)) + ','
            #for x in range(self.flags.YEARSTART, self.flags.YEAREND):
            csv_text += str(','.join(list(discharges.astype(str)))).replace('nan', '') + ','
            csv_text += '\n'

            #plt.plot(smb_df['dt'], smb_df['smb'], label='Yearly SMB, ID=' + str(id))

            ax.plot(result_dt, result, label='Total Mass Balance Change, ID=' + str(id))


            #plt.plot(discharges_dt, self.vels, label='Total Velocity')
            #plt.plot(discharges_dt, self.thickness, label='Total Thickness')
            #plt.plot(discharges_dt, self.lengths, label='Total length')


        with open(MB_OUTPUT + title+'.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            to_write = csv_text.split('\n')
            for i, l in enumerate(to_write):
                to_write[i] = l.split(',')
            writer.writerows(to_write)

        ax.legend()
        ax.set_xlabel('Date')
        ax.set_ylabel('Total Mass Change (GT/yr)')
        ax.grid()
        ax.set_title(title)
        fig.savefig(MB_OUTPUT + title + self.flags.sources_v()[0][0] + '_' + str(self.thickness_calculator) +'_SMBs.pdf')
        fig.savefig(MB_OUTPUT + title + self.flags.sources_v()[0][0] + '_' + str(self.thickness_calculator) +'_SMBs.png')

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
        
        vel_df['discharge_vel'] = np.sin(np.deg2rad(vel_df['vel_angle_diff'])) * vel_df['total_vel']
        
        return vel_df




class SlopeManager(FlowProfile):
    def __init__(self, xlims, ylims, flags):
        super().__init__(flags, xlims, ylims, 
                         {'point': [0,0], 'type':'fl', 'point_range':[0,0], 'point_spacing': 0},
                          'pink')
        self.tile = REMATileSlopeManager(xlims, ylims, flags, 'ipr')
        self.max_dist = 50

    def __str__(self):
        return 'slopes'

    def get_slopes(self, gdp):
        out = self.tile.get_ouput_files()
        out = gl_geotiff_s_join(out, gdp, column_of_interest='band_data', label='slope')
        return out


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
            
            values.extend(gpd.sjoin_nearest(poses_gdf, out, max_distance=line_spacing_m*4, how='left')[column_of_interest].astype(dtype=dtype)[1:-1])

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
