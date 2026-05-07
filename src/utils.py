from flags import *
import time as t
from numpy import abs # type: ignore

AREAS = {

    'Dibble' : [
        [1815595,1882493,],
        [-1876131, -1748203]
        
    ],

    'DibbleSlowing': [
        [1852971,1861727],
        [-1859529, -1847206,]

    ],


}

POINT_LISTS = {

    'Dibble' : [
        {
            'point': [-1806893.758, 1855363.783],
            'point_range': [-5, 5],
            'point_spacing': 2000
        },
    ]
}

TO_FRAME = {
    'itslive_trends.tif': {
        'title': 'ItsLive (2018-2024) Velocity Trends',
        'label': 'Trend (m/yr²)',
        'vmin': -10,
        'vmax': 10,
        'cmap': 'RdYlGn',
        'gl': True
    },
    'itslive_r2.tif': {
        'title': ' ItsLive (2018-2024) Velocity Trends ',
        'label': 'R²',
        'vmin': 0,
        'vmax': 1,
        'cmap': 'Greys_r',
        'gl': False
    },
    'measures_trends.tif': {
        'title': ' MEaSUREs (2018-2024) Velocity Trends ',
        'label': 'Trend (m/yr²)',
        'vmin': -10,
        'vmax': 10,
        'cmap': 'RdYlGn',
        'gl': True
    },
    'measures_r2.tif': {
        'title': ' MEaSUREs (2018-2024) Velocity Trends  ',
        'label': 'R²',
        'vmin': 0,
        'vmax': 1,
        'cmap': 'Greys_r',
        'gl': False
    },
    '': {
        'title': '   (2018-2024) Velocity Trends    ',
        'label': 'Trend',
        'vmin': 0,
        'vmax': 1,
        'cmap': 'Greys_r',
        'gl': 'only'
    },
    ' ': {
        'title': '  ItsLive (2018-2024) Velocity Trends  ',
        'label': '',
        'vmin': 0,
        'vmax': 1,
        'cmap': 'Greys_r',
        'gl': 'only'
    },
}

GL_IPR_FRAME = 2019102408003


POINT_LISTS2 = {

    'Dibble' : [
        {
            'point': [-1806893.758, 1855363.783],
            'point_range': [-2, 4],
            'point_spacing': 14000
        },
        {
            'point': [-1806893.758, 1855363.783],
            'point_range': [-5, 5],
            'point_spacing': 2000
        },
        
        
        {
            'point': [-1815410,1852497],
            'point_range': [-2, 4],
            'point_spacing': 2000
        },
        {
            'point': [-1805005.87,1855416.14],
            'point_range': [-2, 4],
            'point_spacing': 2000,
            
            #'point_range': [-2, 4],
            #'point_spacing': 17000
        },
        {
            'point': [-1835433,1850375],
            'point_range': [-2, 4],
            'point_spacing': 17000
        },
        {
            'point': [-1830432,1861889],
            'point_range': [-2, 4],
            'point_spacing': 17000
        },
    ],


}

DEFAULT_AREA = 'Dibble'


DIVERGENT_CMAP = 'Spectral'
DIVERGENT_CMAP_FIT_LINES = 'Spectral'

MINIMUM_COVERAGE = 2

STREAM_PLOT_STEPS = 1/12

OUTPUT = "output/"
INPUT = "input/"

ELEVATION_H5_LOCATION = INPUT + "elevation/"
ELEVATION_LOCATION = INPUT + 'elevation/ATL11_trends_APS.gpkg'
GRAV_LOCATION = INPUT + "grav/AIS_GMB_grid.tif"
ICESAT1_ELEVATION_RATE = INPUT + 'elevation/change_rates_crs_4326.tif'#INPUT + 'elevation/ICESat1_ICESat2_mass_change_updated_2_2021/dhdt/ais_dhdt_grounded_filt.tif'
ICESAT1_ELEVATION_RATE_FLOATING = INPUT + 'elevation/change_rates_crs_4326_floating.tif'#INPUT + 'elevation/ICESat1_ICESat2_mass_change_updated_2_2021/dhdt/ais_dhdt_grounded_filt.tif'

ELEVATION_GPKG_LOCATION = OUTPUT + 'elevation/'
TIF_LOCATION = OUTPUT
TEST_PNG_LOCATION = OUTPUT +"images/" 
POINTWISE_OUTPUT_LOCATION = OUTPUT + 'pointwise/'

REMA_PREVIEW_LOCATION = INPUT + "rema/"
REMA_RAW_LOCATION = INPUT + "rema/raw/"
REMA_LOCATION = OUTPUT + "rema/"

HISTORIC_FIRN_TIF = INPUT + 'firn_air/firn_air_1950_on.tif'
SSP126_FIRN_TIF = INPUT + 'firn_air/SSP126.tif'
SSP585_FIRN_TIF = INPUT + 'firn_air/SSP585.tif'

SHAPEFILES = {
    'iceshelf': "shapefiles/coastline_EPS.shp",
    'grounding': "shapefiles/InSAR_GL_Antarctica_v1-1992-2025_reprojected.shp",
    'oceanmask': "shapefiles/maskfile.shp",
    'basins': "shapefiles/a_lot_of_basins.shp",
}

GL_GPKG_InSAR = "shapefiles/InSAR_GL_Antarctica_v1-1992-2025_reprojected.gpkg"
GL_GPKG_radar = "shapefiles/radar_derived_grounding_line.gpkg"

IPR_GPKG_LOCATION = INPUT + "ipr/radar_with_rema_elevation_mosaic.gpkg"

VEL_TIF_FORMAT = TIF_LOCATION + "{0}_{1}_v.tif" # 0=year, 1=direction



FILE_FORMATS = {
    'ItsLive': [
         "../src/input/velocities/ITS_LIVE_velocity_120m_RGI19A_{0}_v02.nc",
         "../src/input/velocities/ITS_LIVE_velocity_120m_RGI19A_{0}_v02.1.nc"
    ],

    'Measures': [
        "../src/input/velocities/Antarctica_ice_velocity_{0}_{1}_1km_v01.1.nc",
        "../src/input/velocities/Antarctica_ice_velocity_{0}_{1}_1km_v01.nc",
        "../src/input/velocities/Antarctica_ice_velocity_{0}_{1}_1km_v01.2.nc",
    ]

}

VELOCITY_DROP_VARS = {
    None: None,
    'x': ['STDX', 'STDY', #'ERRY', 'ERRX', 
                                        'mapping', 'landice', 
                                        'vy_error', 'v_error',
                                        'coord_system', 'velocity'],
    'y': ['STDX', 'STDY', #'ERRX', #'ERRY', 
                                        'mapping', 'landice', 
                                        'vx_error', 'v_error',
                                        'coord_system', 'velocity'],
}

VELOCITY_DIM_LABELS = {
    None: '',
    'x': '_x',
    'y': '_y',
}

SOURCE_SAMPLE_FILES = {
    'ItsLive': FILE_FORMATS['ItsLive'][0].format(2000),
    'Measures': FILE_FORMATS['Measures'][0].format(2000, 2001),
}


MAX_ERR = 5000

REMA_CLOUD_LEVEL = 10
REMA_BACKGROUND_LEVEL = 0



OPACITY_CMAP = [0,0,0]


def overall_velocity(vx, vy):
    return (vx**2 + vy**2)**(.5)


def measures_parse(f):
    '''
    Parses a Measures file to add overall velocity and overall velocity error.


    Parameters
    ----------
    f : xarray.Dataset
        The Measures dataset to be parsed

    Returns
    -------
    xarray.Dataset
        Processed dataset with added columns:
        - 'velocity' : Float
        - 'v_error' : Float
    '''
    f = f.where(f.CNT != 0)
    f['velocity'] = overall_velocity(f.VX, f.VY)
    f['v_error'] = abs((overall_velocity(f.VX + f.ERRX, f.VY + f.ERRY) + overall_velocity(f.VX - f.ERRX, f.VY - f.ERRY)) / 2)
    
    return f

def itslive_parse(f):
    '''
    Parses an ItsLive file to be compatible with Measures. Also removes grounded ice.


    Parameters
    ----------
    f : xarray.Dataset
        The ItsLive dataset to be parsed

    Returns
    -------
    xarray.Dataset
        Processed dataset with renamed columns:
        - 'velocity' : Float
        - 'CNT' : Integer
        - 'VY' : Float
        - 'VX' : Float
    '''

    f = f.rename({'v': 'velocity', 'count': 'CNT', 'vx': 'VX', 'vy': 'VY'})
    f = f.where(f.CNT != 0)
    f = f.where(f.floatingice != 0)

    return f



def drop_unnecessary_for_v(f, source):
    '''
    Drops information unecessary for the overall velocity plotting


    Parameters
    ----------
    f : xarray.Dataset
        The dataset to be cleaned
    source : String
        disregarded

    Returns
    -------
    xarray.Dataset
        Cut down dataset
    '''
    if source == 'Measures':
        return f.drop_vars(["VX", "VY", 'ERRY', 'ERRX'])
    if source == 'ItsLive':
        return f.drop_vars(["VX", "VY"])


def x_only_parse(f, source):
    '''
    Rearranges information to use the x component of the velocity as the main velocity


    Parameters
    ----------
    f : xarray.Dataset
        The dataset to be rearranged
    source : String
        Key present in FORMAT_PARSE that dictates the format of the Dataset

    Returns
    -------
    xarray.Dataset
        Rearranged dataset
    '''
    if source == 'Measures':
        f = f.drop_vars(['velocity', 'v_error'])
        f = f.rename({'ERRX': 'v_error', 'VX': 'velocity'})
    elif source == 'ItsLive':
        f = f.drop_vars(['velocity'])
        f = f.rename({'vx_error': 'v_error', 'VX': 'velocity'})
    #f = f.drop_vars(['ERRY', 'ERRX', 'vy', 'vy_error'])
    return f



def y_only_parse(f, source):
    '''
    Rearranges information to use the y component of the velocity as the main velocity


    Parameters
    ----------
    f : xarray.Dataset
        The dataset to be rearranged
    source : String
        Key present in FORMAT_PARSE that dictates the format of the Dataset

    Returns
    -------
    xarray.Dataset
        Rearranged dataset
    '''
    if source == 'Measures':
        f = f.drop_vars(['velocity', 'v_error'])
        f = f.rename({'ERRY': 'v_error', 'VY': 'velocity'})
    elif source == 'ItsLive':
        f = f.drop_vars(['velocity'])
        f = f.rename({'vy_error': 'v_error', 'VY': 'velocity'})
    #f = f.drop_vars(['ERRY', 'ERRX', 'vx', 'vx_error'])
    return f



FORMAT_PARSE = {
    'ItsLive': itslive_parse,
    'Measures': measures_parse
}


VELOCITY_SPECIAL_PREP = {
    None: drop_unnecessary_for_v,
    'x': x_only_parse,
    'y': y_only_parse,
}


class LoadingBar():

    def __init__(self):
        self.start_time = False

    def time_left(self, percent_done):
        '''
        Returns the estimated time until a task is finished based on what percentage of it is has been finished
        since the start time in seconds


        Parameters
        ----------
        percent_done : Float
            A percentage in decimal form (1.0 being 100%, 0 being 0%) that reflects the progress so far

        Returns
        -------
        Integer
            Estimated time remaining for task in seconds
        '''

        cur_time = t.time()
        total_time = cur_time - self.start_time
        if percent_done == 0:
            return 0

        return round(((total_time * (1 - percent_done)) / percent_done))


    def load_bar(self, progress, total):
        '''
        Prints a persistent one line progress bar based on the progress and total provided.
        records the time from the first call to this function and makes a time projection based
        on that time difference. Once the bar is completed the start time is reset.


        Parameters
        ----------
        progress : Integer
            The number of steps completed in the process (all steps should take similar amounts of time)
        total : Integer
            The total number of steps in the process

        Returns
        -------
        None
        '''


        bar = "Progress: [" + ("|" * round(50 * (progress/total))) + (" " * (50 - round(50 * (progress/total)))) \
            + "] {0}/{1}".format(progress, total)
        

        if self.start_time:
            time_remaining = self.time_left(float(progress) / float(total))
            if int(time_remaining) < 60:
                bar += f" {round(time_remaining)} s left         "

            else:
                                            
                bar += f" {round((time_remaining / 60) * 100) / 100} min left         "
        else:
            self.start_time = t.time()
        

        print(bar, end="\r")

        if progress >= total:
            self.start_time = False
            print("")

