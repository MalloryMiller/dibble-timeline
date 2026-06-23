from utils import * 
from file_manager import IPRManager ,REMATileManager, BedmapManager, GeoidManager, VelocityManager, SMBManager
import geopandas as gpd
import numpy as np
from pointwise import FlowProfile
import math
from shapely.ops import linemerge


'''
   id     Date_1     Date_2     Date_3     Date_4                                              layer                           path  IPR_agreement                                           geometry  discharge  discharges_total_vel
0   1 2026-01-10 2026-01-11 2026-02-27 2026-02-28  T069_A2_phase_difference_27Feb2026_28Feb2026_1...  /home/mallory/gl_feb_2026.shp           True  MULTILINESTRING ((135.35726 -66.10097, 135.346...   0.913152              1.604109
1   2 2026-01-10 2026-01-11 2026-02-03 2026-02-04  T069_A2_phase_difference_10Jan2026_11Jan2026_0...                        gl4.shp          False  MULTILINESTRING ((135.38143 -66.10341, 135.362...   4.806796              7.783742
2   3 2026-02-03 2026-02-04 2026-02-27 2026-02-28  T069_A2_phase_difference_03Feb2026_04Feb2026_2...                         gl.shp           True  MULTILINESTRING ((135.35854 -66.10094, 135.349...   8.267287             20.083571
3   4 2026-02-03 2026-02-04 2026-03-11 2026-03-12  T069_A2_phase_difference_03Feb2026_04Feb2026_1...                        gl3.shp          False  MULTILINESTRING ((135.39237 -66.10397, 135.381...   5.890144             21.604217
4   5 2026-02-27 2026-02-28 2026-03-11 2026-03-12  T069_A2_phase_difference_27Feb2026_28Feb2026_1...                        gl2.shp           True  MULTILINESTRING ((135.39282 -66.10375, 135.383...   3.059803              4.684091
'''

class MBCalculation():
    def __init__(self, xlims, ylims, flags):

        self.thickness_calculator = ThicknessBedmapREMA(xlims, ylims, flags)
        self.flux_calculator = VelocityFlux(xlims, ylims, flags)
        self.SMB = SMBManager(xlims, ylims, flags, 'smb')

        self.results = gpd.read_file(GL_GPKG_manual)
        pass

    def calculate_discharge(self):
        final_df = self.results
        return final_df

    def get_results(self, id = 1):


        df = self.results[self.results['id'] == id]
        '''df = gpd.read_file(GL_GPKG_InSAR)
        print(df)
        df = df[df['Glac_Name'] == 'Dibble']
        print(df)'''

        thickness = self.thickness_calculator.get_thickness(df)
        vels = self.flux_calculator.get_velocity(df)
        print(thickness)
        vels.to_file(
            'PROGRESS.gpkg'
        )
        #smb_df = self.SMB.get_surface_balance_df()
        discharges = []

        for x in df['id'].unique():
            discharge = (vels[vels['id'] == x]['discharge_vel'] * thickness[thickness['id'] == x]['thickness'] * thickness[thickness['id'] == x]['lens'] * GLACIAL_ICE_DENSITY) / 1e12
            print(np.sum(discharge))
            discharges.append(np.sum(discharge))

        df['discharge'] = discharges

        df['discharges_total_vel'] = discharges
        print(df)
        self.calculate_discharge()

        return discharges[0]
    

    def plot_MB(self):
        self.get_results()

        discharges = []
        for x in self.results['id'].unique():
            d = self.get_results(x)
            discharges.append(d)

        self.results['discharges'] = discharges
        print(self.results)

        return





class VelocityFlux(FlowProfile):
    def __init__(self, xlims, ylims, flags):
        super().__init__(flags, xlims, ylims, 
                         {'point': [0,0], 'type':'fl', 'point_range':[0,0], 'point_spacing': 0},
                          'pink')
        self.velx_manager = VelocityManager(xlims, ylims, flags, 'velx')
        self.vely_manager = VelocityManager(xlims, ylims, flags, 'vely')

    def get_velocity(self, gdp):
        out_x = self.velx_manager.get_ouput_files()
        out_y = self.vely_manager.get_ouput_files()
        print(out_x)
        vel_df = gl_geotiff_s_join(out_x, gdp, label='velx')
        vel_df = vel_df.merge(gl_geotiff_s_join(out_y, gdp, label='vely'))

        vel_df['vel_angle'] = np.degrees(np.arctan2(vel_df['vely'], vel_df['velx']))  % 360
        vel_df['vel_angle_diff'] = ((vel_df['angle'] - vel_df['vel_angle']) % 360) #% 360
        vel_df['total_vel'] = overall_velocity(vel_df['velx'], vel_df['vely'])
        vel_df['discharge_velx'] = np.cos(vel_df['vel_angle_diff']) * vel_df['velx']
        vel_df['discharge_vely'] = np.sin(vel_df['vel_angle_diff']) * vel_df['vely']
        #vel_df['discharge_vel'] = vel_df['discharge_velx'] + vel_df['discharge_vely']
        vel_df['discharge_vel'] = np.abs(np.sin(np.deg2rad(vel_df['vel_angle_diff'])) * vel_df['total_vel'])
        vel_df['discharge_vel'][vel_df['discharge_vel'] < 0] = 0 
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

class ThicknessCentralIPR(ThicknessCalculation):
    def __init__(self, xlims, ylims, flags):
        super().__init__(xlims, ylims, flags)
        self.IPR = IPRManager(xlims, ylims, flags, 'ipr')
        self.max_dist = 10

    def get_thickness(self, gdp):
        out = self.IPR.get_ouput_files()
        out = gpd.sjoin_nearest(gdp, out, max_distance=self.max_dist*10)
        

class ThicknessEquilibrium(ThicknessCalculation):
    def __init__(self, xlims, ylims, flags):
        super().__init__(xlims, ylims, flags)
        self.REMA = REMATileManager(xlims, ylims, flags, 'rema')
        self.geoid = GeoidManager(xlims, ylims, flags, '2008')
        pass

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
        for i, pos in enumerate(poses):
            if i == len(poses) - 1 or i == 0:
                last_pos = pos
                continue
            next_pos = poses[i+1]
            dists.append(i)
            values.append(dtype(out.sel(x=pos.x, y=pos.y, method='nearest')[column_of_interest].mean()))
            ids.append(line.id)
            lats.append(pos.y)
            lons.append(pos.x)
            lens.append(overall_velocity(next_pos.x - last_pos.x, next_pos.y - last_pos.y))
            if record_angle:
                angle.append(math.degrees(math.atan2(next_pos.y - last_pos.y, next_pos.x - last_pos.x))  % 360)
            last_pos = pos
            progress.load_bar(i, len(poses))

    if not record_angle:
        df = gpd.GeoDataFrame({
            "dists": dists,
            label: values,
            "id": ids,
            "lens": lens,
            "latitude": lats,
            "longitude": lons,
        })
    else:
        df = gpd.GeoDataFrame({
            "dists": dists,
            label: values,
            "id": ids,
            "lens": lens,
            "angle": angle,
            "latitude": lats,
            "longitude": lons,
        })


    df['geometry'] = df.apply(pointify, axis=1)
    df = df.set_geometry('geometry')

    df = df.sort_values('dists')
    df.to_file(f'TEST DATA{label}.gpkg')
    return df