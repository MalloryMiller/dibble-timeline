## Instructions

Python version 3.11

### Input Setup

The velocity data must be downloaded locally into a folder called `input`. This folder should be directly inside the `src` folder. I also made use of a `shapefiles` folder directly inside the `src` folder.

#### Velocity

The ItsLive data should be downloaded from [here](https://nsidc.org/apps/itslive/) by selecting the Antarctica region and downloading each relevant year that you would like to include.  Be sure the names they have match the respective values shown in `FILE_FORMATS` in the `utils.py` file.

The Measures data should be downloaded from [here](https://cmr.earthdata.nasa.gov/virtual-directory/collections/C3298025582-NSIDC_CPRD/temporal) by navigating to each of the folders for each relevant year that you would like to include and downloading them. Be sure the names they have match the respective values shown in `FILE_FORMATS` in the `utils.py` file.

#### Elevation

The ICEsat2 data should be downloaded and the trends calculated using the tool [here](https://github.com/MalloryMiller/icepyx-collection). Be sure the *folder* the raw data is in matches the value shown in `ELEVATION_H5_LOCATION` in the `utils.py` file, while the *name* of the trends calculated should match the `ELEVATION_LOCATION` file.

The ICEsat1 projected trends should be downloaded from [here](https://digital.lib.washington.edu/researchworks/handle/1773/45388). Do not keep everything in the .zip file, but add the dhdt files. You may need to adjust the projection. Be sure the name matches that of `ICESAT1_ELEVATION_RATE` and `ICESAT1_ELEVATION_RATE_FLOATING`  in the `utils.py` file.

#### Grounding Line

The Rignot-derived grounding lines should be downloaded from [here](https://doi.org/10.5067/IKBWW4RYHF1Q). Be sure the name matches the value of `GL_GPKG_InSAR` in the `utils.py` file. By default, this goes in the `shapefiles` folder.

Additional IPR-derived grounding lines should be placed in a gpkg file that matches the file name listed as of `GL_GPKG_radar` in the `utils.py` file. By default, this goes in the `shapefiles` folder.

IPR data in csv form from [Open Polar Radar](https://doi.org/10.5067/IKBWW4RYHF1Q) should be placed in a gpkg file that matches the file name listed as of `IPR_GPKG_LOCATION` in the `utils.py` file. This gpkg file should be draped over an elevation product with a new elevation column called `elevation1`.

#### Firn Data

The firn content data used should be downloaded from [here](https://zenodo.org/records/10726834). The three files of interest are `FDMv12AD_FAC_ANT27_Hist_1950-2014.nc`, `FDMv12AD_FAC_ANT27_SSP126_2015-2100.nc`, and `FDMv12AD_FAC_ANT27_SSP585_2015-2100.nc`. You may need to adjust the projection. Be sure the file names match that of `HISTORIC_FIRN_TIF`, `SSP126_FIRN_TIF`, and `SSP585_FIRN_TIF` respectively in the `utils.py` file.



### Finding your Desired Area

Dibble glacier is the default, and this program has not been tested with other areas. However, if you would like to view other locations you may.

Run `python3 main.py` from the `src` folder to view the list of preset area titles. If the glacier you need to analyze is not in the list, consider adding the EPSG:3031 coordinates to the `AREAS` dictionary in your `utils.py` file in the same format as the other items. This should be:

```
'Title': [
    [x_min, x_max],
    [y_min, y_max]
],
```

Where Title is the area name.

### Running the Program

If the area you want is in the preset area list, run `python3 main.py Title` from the `src` folder where `Title` is the name of the area preset you want to analyze.

If the area you want is not a preset area, you can run `python3 main.py x_min x_max y_min y_max` from the `src` folder with `x_min`, `x_max`, `y_min`, and `y_max` being the EPSG:3031 coordinates you would have used in the preset to define the desired area instead.

Flags are optional, but can be added to this function call to generate different kinds of charts or alter the program's behavior in other ways. *Without adding any flags, nothing will occur.* You must specify the kind of chart for a chart to be created.


### Built/Output Files

The output files should be saved in a new folder called `output` directly inside the `src` folder. If an error is encountered while trying to save it, read the error. You may need to manually create the folder that it will be saved in based on the printed file name. After the folder or folders are created, try again.

## Flags


### Building Files

The first time you run the program, you will need to build files from the input for the plotting to reference. Do this by running `python3 main.py -rebuild`. This may take an hour. If you run into issues and would like to build a specific dataset rather than all of them at once, you may specify as such with the following flags. If errors are encountered during build see the Built/Output Files section above.

| Flag      | Description                                                                                                            |
| --------- | ---------------------------------------------------------------------------------------------------------------------- |
| -rebuild  | Rebuild all required files                                                               |
| -rebuild:elev  | Rebuild the ICEsat2 files                                                               |
| -rebuild:vel | Rebuild the velocities specified by your other flags |
| -rebuild:velx | Rebuild the x directional velicities from ItsLive |
| -rebuild:vely | Rebuild the y directional velicities from ItsLive |
| -rebuild:firn | Rebuild the firn air data by seperating the bands |

Default: None

### Year Flag

These flags can be used to indicate what years to include for analysis. Any years can be used, but the flag must be arranged in the format -first_year-last_year with no spaces. Years without corresponding files will be ignored. See the default as an example. The last year is included. Only one flag of this type can be used at a time.

Default: -2018-2024

### Velocity Source Flags

These flags can be used to indicate what velocity sources should be included in the analysis. More than one can be included.

| Flag      | Description                                                                                                            |
| --------- | ---------------------------------------------------------------------------------------------------------------------- |
| -itslive  | include [ItsLive](https://nsidc.org/apps/itslive/) files                                                               |
| -measures | include [MEaSUREs](https://cmr.earthdata.nasa.gov/virtual-directory/collections/C3298025582-NSIDC_CPRD/temporal) files |

Default: -itslive -measures


### Chart Type Flags

This flag indicates what kind of chart you would like to create. Only one flag of this type can be used at a time.

| Flag        | Description                              | 
| ----------- | ---------------------------------------- | 
| -points         | Creates a pointwise timelines for all locations specified in the `POINT_LISTS` variable of `utils.py`. This variable specifies the start location, spacing of the points in meters, and the number of points before and after the start location. |
| -frame         | For each GEOtiff file specified in the `TO_FRAME` variable of `utils.py`, this looks for that file in the `to_frame` directory directly inside of the `input` folder and plots it on the temporal grounding lines from Rignot in a readable format. |

Default: None

#### -points Configuration

To configure a new point for the `-points` graph, you need to add something to the `POINTS_LIST` dictionary in the `utils.py` file. If the title of your location is already present as a key in the dictionary, add a new point to that entry by adding this inside the square brackets after the first point:

```
        {
            'point': [y_pos, x_pos],
            'point_range': [points_backward, points_forward],
            'point_spacing': spacing_in_meters
        },
```

 Otherwise, add a new area to the dictionary in the following format:

```
'Title' : [
        {
            'point': [y_pos, x_pos],
            'point_range': [points_backward, points_forward],
            'point_spacing': spacing_in_meters
        },
    ]
```

*n.b. Do NOT create two point plots with the same starting location. They will overwrite themselves in the output folder.*

#### -frame Configuration

To configure a figure for the `-frame` functionality, you need to add something to the `TO_FRAME` dictionary in the `utils.py` file. Place the GEOtiff you would like to frame in a folder called `to_frame` inside your `input` folder. Then add the following to `TO_FRAME` in `utils.py`:

```
'filename.tif': {
        'title': 'Display Title',
        'label': 'Colorbar label',
        'vmin': colorbar_min,
        'vmax': colorbar_max,
        'cmap': 'RdYlGn',
        'gl': True
    },
```

The `'RdYlGn'` and `True` values can be changed, but must be a matplotlib colormap string and a Boolean value, respectively.

### Label Type Flags

This flag indicates how you would like the distance from the start of a stream plot to be displayed. This only applies if some stream flow line calculation was done for the chart.

| Flag        | Description                    |
| ----------- | ------------------------------ |
| -date       | Displays as how many years on average it would take for ice to flow from the starting point                              |
| -dist       | Displays in km the distance the ice has moved from the starting point           |

Default: -dist

### Timeline Panel Flags

These flags indicate the order and kind of panels you would like if using the `-points` flag to construct a timeline chart.

| Flag        | Description                    |
| ----------- | ------------------------------ |
| -vel        | Velocity plot over time from the sources specified by your velocity source flags                               |
| -elev       | ICEsat2 elevations over time           |
| -grav       | GRACE gravimetry over time           |
| -firn       | Firn content over time           |
| -gl         | grounding line intersections with the flow line over time with matching bed elevations plotted to the right           |

Default: -gl -elev -vel


