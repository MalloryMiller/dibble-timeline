
from file_manager import GravimetryManager, ElevationManager, VelocityManager, IPRManager, FirnAirManager
from plotting import Plotting

import glob
from utils import *
import matplotlib.pyplot as plt
import numpy as np

class TimeSeries():

    def __init__(self, flags, xlim, ylim, data, years=[2000, 2025]):

        self.flags = flags
        self.xlim = xlim
        self.ylim = ylim
        self.data = data

        self.years = years

        

        managers = {
            'vel': VelocityManager,
            'elev': ElevationManager,
            'firn': FirnAirManager,
            'grav': GravimetryManager
        }
        
        self.fm = managers[self.data](self.xlim, self.ylim, self.flags,
                        data=data)

        self.data_got = False

        self.output = []


    def get_data(self):
        '''
        Gets data for the file manager if it has not been retrieved yet. If it already has, do nothing.
        '''
        if not self.data_got:
            self.output = self.fm.get_ouput_files()
            print(self.output)
            self.data_got = True


    def generate_nc(self, title):

        '''
        Saves whatever xarray.Dataset is in the self.output variable as a netcdf.
        Continues prompting until save successful or program ended with keyboard interrupt.


        Parameters
        ----------
        title : String
            Name for the file, not including the ending .nc. 'Velocities.nc' will be added to the end of this.

        Returns
        -------
        None
        '''

        cont = True
        print("Saving output...")
        while cont:
            try:
                print(OUTPUT + title + self.data+ ".nc")
                self.output.to_netcdf(OUTPUT + title + self.data+ ".nc")
                print("Saved.")
                cont = False
            except:
                print("Save Failed. \nYou likely have already generated this file. Delete the original so the new version can be saved.")
                print("This could also happen if the folder the file goes in does not exist yet.")
                a = input("After the issue is remedied, press enter to try again. Ctrl+C to quit without saving.")
                if 'n' in a:
                    cont = False


    def generate_charts(self, title):

        fout = OUTPUT + "fits/" + title + '.png'
        print('/'.join(fout.split('/')[:-1]))
        os.makedirs('/'.join(fout.split('/')[:-1]), exist_ok=True)
        print('Saving %s'%(fout))
        plt.savefig(fout, dpi=200)
        plt.close('all')

                

    def calculate_fit(self, vs, errors=[]):
        '''
        Generates the R-squared, slope, and intercept for the best fit line of a set of weighted points.


        Parameters
        ----------
        vs : List[Float]
            List of points to fit.
        errors : List[Float]
            List of errors. The data will be weighted as 1/errors.

        Returns
        -------
        Float
            The R-squared value for the fit
        Float
            The slope for the fit
        Float
            The intercept for the fit
        '''
        if errors == []:
            errors = np.array([1]*len(vs))

        weights = 1/errors

        lin_fit = np.polyfit(vs.year.data, vs.data, 1, w=weights)
        v_slope = lin_fit[0]
        intercept = lin_fit[1]
        
        expected = lin_fit[1] + (lin_fit[0] * vs.year)
        
        sst = np.sum((vs - np.mean(vs))**2)
        ssr = np.sum((vs - expected)**2)

        rsq = 1 - (ssr / sst)

        return rsq, v_slope, intercept


class VelTimeSeries(TimeSeries):
    def __init__(self, flags, xlim, ylim, data, years=[2000, 2025]):
        super().__init__(flags, xlim, ylim, data, years=[2000, 2025])

    def get_data(self):
        if not self.data_got:
            self.output = self.fm.get_ouput_files()
            self.data_got = True


    def generate_nc(self, title):
        '''
        After files have been open()ed in the file manager, this will read the information inside
        and run linear fits & regression tests on each pixel therein. This data will be rendered as an nc file.


        Parameters
        ----------
        title : String
            Name for the file, not including the ending .nc. 'Velocities.nc' will be added to the end of this.

        Returns
        -------
        None
        '''

        self.get_data()

        self.output = self.output.drop_vars(["velocity"])
        self.output = self.output.assign(v_sum=(('y','x'), np.zeros((len(self.output.y), len(self.output.x)))))
        self.output = self.output.assign(v_slope=(('y','x'), np.zeros((len(self.output.y), len(self.output.x)))))
        self.output = self.output.assign(rsq=(('y','x'), np.zeros((len(self.output.y), len(self.output.x)))))
        self.output = self.output.assign(coverage=(('y','x'), np.zeros((len(self.output.y), len(self.output.x)))))
        self.output = self.output.assign(v_avg=(('y','x'), np.zeros((len(self.output.y), len(self.output.x)))))

        print("Linear Fits running...")
        for x in range(len(self.fm.file.x)):
            for y in range(len(self.fm.file.y)):
                #yearly_err = self.fm.file['v_error'][:,y,x].copy(deep=True, data=None).fillna(MAX_ERR)
                vs = self.fm.file['band_data'][:,y,x].copy(deep=True, data=None)

                #no_err_info = (~np.isnan(vs) & np.isnan(yearly_err))
                #yearly_err[no_err_info] = MAX_ERR

                vel_count_overlap = ~(np.isnan(vs)) 
                
                #yearly_err = yearly_err.where(vel_count_overlap).dropna(dim="year", how="any")
                vs = vs.dropna(dim="year", how="any")



                if len(vs) >= MINIMUM_COVERAGE:
                    count = self.fm.file['CNT'][:,y,x].sum()


                    self.output.CNT[y, x] = count
                    self.output.coverage[y, x] = len(vs)
                    self.output.v_avg[y, x] = float(vs.sum()) / count


                    rsq, v_slope, intercept = self.calculate_fit(vs)#, yearly_err)

                    self.output.v_slope[y, x] = v_slope
                    self.output.rsq[y,x] = rsq


                else:
                    self.output.coverage[y, x] = np.nan
                    self.output.v_slope[y, x] = np.nan
                    self.output.rsq[y, x] = np.nan
                    self.output.v_avg[y, x] = np.nan

        
                #print(self.fm.file['velocity'][:,x,y])


        self.output = self.output.drop_vars(["v_sum", "v_error"])

        print(self.output)
        super().generate_nc(title)





    def generate_charts(self, title):
        '''
        After files have been open()ed in the file manager, this will read the information inside
        and run linear fits & regression tests on each pixel therein. This data will be rendered as a plot
        where the x axis is time and the y axis is velocity.


        Parameters
        ----------
        title : String
            Name for the file, not including the ending .nc. 'Velocities.nc' will be added to the end of this.

        Returns
        -------
        None
        '''
        self.get_data()

        dpi, scale = 200, 15
        fig, ax = plt.subplots()


        print("Linear Fits running...")

        cmap = plt.get_cmap(DIVERGENT_CMAP)
        cmap_fits = plt.get_cmap(DIVERGENT_CMAP_FIT_LINES)
        norm = plt.Normalize(vmin=-10, vmax=10)


        


        print(self.fm.file)
        for x in range(len(self.fm.file.x)):
            for y in range(len(self.fm.file.y)):

                #yearly_err = self.fm.file['v_error'][:,y,x].copy(deep=True, data=None).fillna(MAX_ERR)
                vs = self.fm.file['band_data'][:,y,x].copy(deep=True, data=None)

                #no_err_info = (~np.isnan(vs) & np.isnan(yearly_err))
                #yearly_err[no_err_info] = MAX_ERR

                vel_count_overlap = ~(np.isnan(vs)) 
                
                #yearly_err = yearly_err.where(vel_count_overlap).dropna(dim="year", how="any")
                vs = vs.dropna(dim="year", how="any")



                if len(vs) >= MINIMUM_COVERAGE:

                    rsq, v_slope, intercept = self.calculate_fit(vs)#, yearly_err)

                    #opacity = yearly_err/500
                    #opacity[opacity > 1] = 1
                    #opacity = 1- opacity
                    
                    ax.scatter(vs.year, vs.data, c=[v_slope]*len(vs.data), cmap=DIVERGENT_CMAP, norm=norm,  s=opacity*10)
                    ax.plot(vs.year, vs.data, color=cmap(norm(v_slope)),  alpha=0.15)
                    ax.plot(vs.year, intercept + (vs.year * v_slope), color=cmap_fits(norm(v_slope)), alpha=0.25)




        ax.set_title(title)
        ax.set_xlabel("Year")
        ax.set_ylabel("Velocity (m/yr)")
        #plt.xticks(self.fm.file['year'])

       # plt.colorbar(norm, label='Calculated Slope', cax=ax)
        '''colorbar_colors = ScalarMappable(norm)
        colorbar_colors.set_cmap(cmap)
        fig.colorbar(colorbar_colors, ax=ax, label = 'Slope of Fits for Points', orientation='horizontal', location='top')
        '''
        colorbar_colors_2 = ScalarMappable(norm)
        colorbar_colors_2.set_cmap(cmap_fits)
        fig.colorbar(colorbar_colors_2, ax=ax, label = 'Slope for Best Fits', orientation='horizontal', location='top')
        


        super().generate_charts(title)
        


class ElevTimeSeries(TimeSeries):
    def __init__(self, fm):
        super().__init__(fm)


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
        
        
        
        


    def generate_gpkg_name(fn):
        Path(gpgk_folder_name+ '/' + fn.split('/')[0]).mkdir(exist_ok=True)
        return gpgk_folder_name + '/' + fn[:-4] + '.gpkg'


    def generate_nc(self, title):

        all_files = sorted(glob.glob(ELEVATION_H5_LOCATION+'*.h5'))



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

    def generate_charts(self,):
        p = Plotting()

        gdf = gpd.read_file('to_save/ATL11_trends_APS.gpkg')#'ATL11_trends_APS.gpkg')
        p.plot_col(gdf, 'trend', 1, -1, 'bwr_r', "IceSAT2 Elevation Trend (m/yr)", velocities=None)

