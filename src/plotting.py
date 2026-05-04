
import geopandas as gpd
import shapefile as shp
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib as mp
from matplotlib.lines import Line2D
import rasterio as rs
import os

from utils import *
from matplotlib import cm
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from matplotlib.cm import ScalarMappable
import matplotlib as mpl
import numpy as np

import cartopy.crs as ccrs
from matplotlib_scalebar.scalebar import ScaleBar
from matplotlib_map_utils.core.north_arrow import NorthArrow, north_arrow
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER


gpgk_folder_name = 'gpkg_progress'

velocity_trends_tif = "shapefiles/velocities_measures.tif"#"shapefiles/velocity_trends.tif"

extent = [1.78e6, 1.92e6, -1.91e6,  -1.75e6]
basin_extent = [1, 2.1e6, -2.1e6, -0.75]


class Plotting:
    def __init__(self, extent=extent, basin_extent=basin_extent, get_elevation = False):

        self.extent = extent
        self.crs = ccrs.SouthPolarStereo()
        self.basin_extent = basin_extent
        if get_elevation:
            self.gdf = gpd.read_file(ELEVATION_LOCATION) #base for the elevation df size
        else:
            self.gdf = None
        ##print(gdf.columns.tolist())


    def error_hist(self, df, color_col = 'dist', hist_col='diff', bins=9, min_ = None, max_ = None, min_c=None, max_c=None):
        fig, ax = plt.subplots()
        df = df.fillna(0)
        datas = []
        temps = []

        for t in np.sort(df[color_col].unique()):
            temps.append(t)
            datas.append(df[hist_col][df[color_col] == t])
            

        min_ns = np.min(temps)
        max_ns = np.max(temps)
        if min_c != None:
            min_ns = min_c
        if max_c != None:
            max_ns = max_c

        CMAP = mp.cm.plasma
        norm = colors.Normalize(min_ns, max_ns)
        c_label = "Elevation Trend (m/yr)"

        bin_range = [np.min(df[hist_col]), np.max(df[hist_col])]
        if min_ != None:
            bin_range[0] = min_
        if max_ != None:
            bin_range[1] = max_
        
        h, bins_, patches = ax.hist(datas, bins=bins,  histtype='bar', rwidth=0.95, stacked = True, range=bin_range)
        for i, patch in enumerate(patches):
            for bar in patch:
                bar.set_facecolor(CMAP(norm(temps[i])))

        #ax.bar(n, bins, histtype='bar', rwidth=0.95, stacked = True)
        title = "Elevation Error"
        ax.set_title(title)
        ax.set_xlabel("IceSAT2 - REMA")
        ax.set_ylabel("Count")


        colorbar_colors = ScalarMappable(norm)
        colorbar_colors.set_cmap(CMAP)
        fig.colorbar(colorbar_colors, ax=ax, label = c_label)
        return fig, ax


    def plot_velocity(self, fname, year):
        fig, ax = plt.subplots()
        plt.title("Velocity (" + str(year) + ")")
        plt.xlim(self.extent[0], self.extent[1])
        plt.ylim(self.extent[2],  self.extent[3])
        self.plot_geotiff(fname, fig, ax, vmax=600, vmin=0, label = "Velocity (m/yr)", cmap='viridis')
        self.plot_glacier_borders(fig, ax)
        return True

    def plot_elevation(self, fname, year):
        gdf = gpd.read_file(fname)



        fig, ax = plt.subplots()
        vmin, vmax = 0, 2000
        plt.title("Elevation (" + str(year) + ")")
        gdf.plot(column='elevation', vmax=vmax, vmin=vmin, cmap='viridis', markersize=3, ax=ax)
        plt.xlim(self.extent[0], self.extent[1])
        plt.ylim(self.extent[2],  self.extent[3])
        
        self.plot_glacier_borders(fig, ax)
        
        colorb = plt.cm.ScalarMappable(cmap='viridis', norm=colors.Normalize(vmin=vmin, vmax=vmax))
        self.mask_outside(extent=self.extent)
        
            
        fig.colorbar(colorb, orientation='vertical', label='Elevation (m)', ax=ax)

        return True


    def plot_rema_coverage(self, na, year):
        try:
            strips = os.listdir(REMA_PREVIEW_LOCATION + str(year)) 
        except:
            return False
        
        copper = cm.get_cmap('copper', 256*8)
        newcolors = copper(np.linspace(0, 1, 256*8))
        empty = np.array([0, 0, 0, 0])
        newcolors[:1, :] = empty
        newcmp = ListedColormap(newcolors)
        
        fig, ax = plt.subplots()
        plt.title("REMA Coverage Preview (" + str(year) + ")")
        plt.xlim(self.extent[0], self.extent[1])
        plt.ylim(self.extent[2],  self.extent[3])
        first_item = True
        for s in strips:
            if s.split('.')[-1] != 'tif':
                print('continue')
                continue
            self.plot_geotiff(REMA_PREVIEW_LOCATION + str(year) + '/' + s, fig, ax, vmax=300, vmin=0, label = "Hillshade", cmap=newcmp, legend=first_item, alpha=1)
            first_item = False
        self.plot_glacier_borders(fig, ax)
        return True

    def plot_gpkg(self, fig, ax, gpkg, coloring=None, cmap='summer', cbar=False):
        gdf = gpd.read_file(gpkg)
        gdf = gdf.to_crs(3031)
        
        if coloring != None:
            gdf.plot(ax=ax, column=coloring, cmap=cmap, autolim=False, label=coloring)
            if cbar:
                colorb = plt.cm.ScalarMappable(cmap=cmap, norm=colors.Normalize(vmin=min(gdf[coloring]), vmax=max(gdf[coloring])))
                fig.colorbar(colorb, orientation='vertical', label=cbar + " " + coloring, ax=ax)
        else:
            gdf.plot(ax=ax, autolim=False)

    def plot_temporal_grounding_line(self, fig, ax, cmap='summer', cbar=False):

        self.plot_gpkg(fig, ax, GL_GPKG_InSAR, 'Year', cmap=cmap, cbar=cbar)

    def plot_raw_rema_data(self, na, year):
        try:
            strips = os.listdir(REMA_RAW_LOCATION + str(year)) 
        except:
            return False
        
        copper = cm.get_cmap('copper', 256*8)
        newcolors = copper(np.linspace(0, 1, 256*8))
        empty = np.array([0, 0, 0, 0])
        newcolors[:1, :] = empty
        newcmp = ListedColormap(newcolors)
        
        fig, ax = plt.subplots()
        plt.title("Raw REMA Elevation Data (" + str(year) + ")")
        plt.xlim(self.extent[0], self.extent[1])
        plt.ylim(self.extent[2],  self.extent[3])
        first_item = True
        for s in strips:
            if s.split('.')[-1] != 'tif':
                print('continue')
                continue
            self.plot_geotiff(REMA_RAW_LOCATION + str(year) + '/' + s, fig, ax, vmax=REMA_CLOUD_LEVEL, vmin=0, label = "Elevation (m)", cmap=newcmp, legend=first_item, alpha=1)
            first_item = False
        self.plot_glacier_borders(fig, ax)
        return True

    def plot_geotiff(self, fname, fig, ax, vmax=1000, vmin=0, label = "Velocity Trend Slope (m/yr)", cmap='viridis', alpha=0.5, legend=True):
        with rs.open(fname) as f:
            img = f.read(1)
            minx, miny, maxx, maxy = f.bounds.left, f.bounds.bottom, f.bounds.right, f.bounds.top
            extent = [minx, maxx, miny, maxy]
            
        vmin = vmin
        vmax = vmax
        cmap = cmap
        
        if legend:
            colorb = plt.cm.ScalarMappable(cmap=cmap, norm=colors.Normalize(vmin=vmin, vmax=vmax))
            fig.colorbar(colorb, orientation='vertical', label=label, ax=ax)
        
        
        plt.imshow(img, cmap=cmap, extent = extent, origin='upper', vmin=vmin, vmax=vmax, alpha=alpha, zorder=-10)
        
        
    def plot_shapefile(self, fname, color, z_order = 15, fill=False, extra_xs=[], extra_ys=[]):
        sf = shp.Reader(fname)
        for shape in sf.shapeRecords():

            x = [i[0] for i in shape.shape.points[:]] + extra_xs
            y = [i[1] for i in shape.shape.points[:]] + extra_ys
            if fill:
                plt.fill(x, y, color=color)
            else:
                plt.scatter(x, y, color=color, zorder=z_order, marker='o', linewidths=0, s = 2)
        

        
    def plot_glacier_borders(self, fig, ax, grounding_color='black', glacial_color='blue', basin_color="red", fill=False, legend=True, basins=False):
        if basins:
            self.plot_shapefile(SHAPEFILES['basins'], basin_color, fill=fill)
        self.plot_shapefile(SHAPEFILES['iceshelf'], glacial_color, z_order = 15, fill=fill) # old: https://usicecenter.gov/Products/AntarcData
        self.plot_shapefile(SHAPEFILES['grounding'], grounding_color, z_order = 20, fill=fill) # Qantarctica
        
        if legend:
            leg = ax.legend([Line2D([0], [0], color=grounding_color, lw=1),
                    Line2D([0], [0], color=glacial_color, lw=1)], 
                    ['Grounding Line (Mouginot)', 'Ice Shelf Extent (Bindschadler)'], framealpha=1, loc='lower right')
            leg.set_zorder(100)
        
        
    def mask_outside(self, mask_color='white', extent=None):
        if extent == None:
            extent = self.extent
        self.plot_shapefile(SHAPEFILES['oceanmask'], mask_color, fill=True)
        
        
    def plot_only_vel_geotiff(self, grounding_color='red', glacial_color='slategrey', extent=None):
        if extent == None:
            extent = self.extent
        fig, ax = plt.subplots()
        
        self.plot_geotiff("shapefiles/qantarctica_velocities.tif", fig, ax, alpha=.5, cmap="bone")
        self.plot_glacier_borders(fig, ax, grounding_color=grounding_color, glacial_color=glacial_color)
        if extent:
            plt.xlim(extent[0], extent[1])
            plt.ylim(extent[2],  extent[3])

        
        print("Saving image...")
        plt.savefig("velocity_reading.png", dpi=200)
        print("velocity_reading.png")
        
        plt.close('all')


    def make_cartopy_plot(self):
        fig = plt.figure()
        ax = plt.axes(projection=self.crs)

        return fig, ax

    def add_cartopy_reference_info(self, fig, ax, extent=None):

        if extent:
            plt.xlim(extent[0], extent[1])
            plt.ylim(extent[2],  extent[3])

        gl = ax.gridlines(crs=ccrs.PlateCarree(), 
                  color='gray', 
                  draw_labels=True, 
                  dms=True, 
                  x_inline=False, 
                  y_inline=False,
                  alpha=0.5)
                  

        ax.add_artist(ScaleBar(1))
        north_arrow(ax, location="lower right", rotation={"crs": 3031, "reference": "center"}, scale=0.25)


    def plot_df_on_borders(self, df, cmap, norm, c_list, title, grounding_color='red', glacial_color='slategrey', extent=None, velocity=True, vel_a=.75):
        
        if extent == None:
            extent = self.extent
        fig, ax = self.make_cartopy_plot()
        
        if velocity:
            self.plot_geotiff("shapefiles/qantarctica_velocities.tif", fig, ax, alpha=vel_a, cmap="bone", label='MeASUREs Average Velocity (m/y)')
            self.mask_outside()
        self.plot_temporal_grounding_line(fig, ax)
        

        if 'geometry' in df.columns:
            xs = []
            ys = []
            for p in df['geometry']:
                xs.append(p.x)
                ys.append(p.y)
            df['x'] = xs
            df['y'] = ys

        sm = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
        if 'labels' in df.columns:


            if 'x' in df.columns:
                for i, l in enumerate(df['labels'].unique()):
                    cur = df[df['labels'] == l]
                    if cmap == None or c_list == []:
                        ax.plot(cur['x'], cur['y'], label=l, marker='o', linestyle='None')
                    else:
                        ax.plot(cur['x'], cur['y'], label=l, color=sm.to_rgba(c_list[i]), marker='o', linestyle='None')
                    
        else:
            if cmap == None or c_list == []:
                ax.plot(cur['x'], cur['y'], marker='o', linestyle='None')
            else:
                ax.plot(cur['x'], cur['y'], color=sm.to_rgba(c_list[i]), marker='o', linestyle='None')


        ax.legend()

        fig.colorbar(sm, ax=ax)

        self.add_cartopy_reference_info(fig, ax, extent=extent)


        print("Saving image...")
        plt.savefig(title, dpi=200)
        print(title)
        
        plt.close('all')



    def plot_only_vel_trend_geotiff(self, grounding_color='black', glacial_color='slategrey', extent=None, cmap="RdYlGn"):
        fig, ax = plt.subplots()
        plt.title("Velocity Trend (2010-2020)")

        if extent == None:
            extent = self.extent
        
        self.plot_geotiff(velocity_trends_tif, fig, ax, vmax=10, vmin=-10,  label = "Velocity Trend (m/yr²)", cmap=cmap, alpha=1)
        self.plot_glacier_borders(fig, ax, grounding_color=grounding_color, glacial_color=glacial_color)
        self.mask_outside(extent=extent)
        
        if extent:
            plt.xlim(extent[0], extent[1])
            plt.ylim(extent[2],  extent[3])
        
        print("Saving image...")
        plt.savefig("velocity_trend_reading.png", dpi=200)
        print("velocity_trend_reading.png")
        
        plt.close('all')
        
        
    def show_extent(self, extent=None, glacial_color='black', extent_color='r', extent_line_color='r', linewidth=5):
        if extent == None:
            extent = self.extent
        fig, ax = plt.subplots()
        self.plot_glacier_borders(fig, ax, grounding_color=(1, 0, 0, 0), glacial_color=glacial_color, basin_color=(1, 0, 0, 0), fill=True, legend=False)
        x_pos = [ extent[1],extent[0], extent[0], extent[1]]
        y_pos = [extent[2], extent[2], extent[3], extent[3]]
        plt.fill(x_pos, y_pos, color=extent_color, edgecolor=extent_line_color, linewidth=linewidth)

        
        print("Saving image...")
        plt.savefig("extent.png", dpi=200)
        print("extent.png")
        
        plt.close('all')



    def plot_col(self, gdf, colm, vmax, vmin, cmap, color_label, grounding_color='black', glacial_color='slategrey', velocities=None, extent=None, g_cbar=False, g_cmap='bone_r'):
        print("Plotting ATL11_" + colm + ".png")
        
        
        fig, ax = self.make_cartopy_plot()
        fig.set_figheight(5.8)

        if extent == None:
            extent = self.extent
        
        self.plot_temporal_grounding_line(fig, ax, cmap=g_cmap, cbar=g_cbar)
        
        colorb = plt.cm.ScalarMappable(cmap=cmap, norm=colors.Normalize(vmin=vmin, vmax=vmax))
        plt.title(' '.join(color_label.split(' ')[:-2]))
        
        gdf.to_crs("EPSG:3031")
        gdf.plot(column=colm, vmax=vmax, vmin=vmin, cmap=cmap, markersize=3, ax=ax)
        
        
        if velocities == 'trend':
            print("Plotting velocity trends...")
            self.plot_geotiff("shapefiles/velocity_trends.tif", fig, ax, vmax=10, vmin=-10,  label = "Velocity Trend Slope (m/yr²)", cmap=cmap)
        elif velocities:
            print("Plotting velocities...")
            self.plot_geotiff("shapefiles/qantarctica_velocities.tif", fig, ax, cmap=cmap)
        
        
        self.mask_outside(extent=extent)
        self.add_cartopy_reference_info(fig, ax, extent=extent)
        
        
        # Smith
        #plt.ylim(-0.7e6, -0.5e6)
        #plt.xlim(-1.65e6, -1.3e6)
        
            
        fig.colorbar(colorb, orientation='vertical', label=' '.join(color_label.split(' ')[-2:]), ax=ax)
            
        print("Saving image...")
        plt.savefig(str(velocities) + "ATL11_" + colm + ".png", dpi=200)
        print("ATL11_" + colm + ".png")
        
        plt.close('all')

        
    def plot_only_geotiff(self, fname, title, label, vmax, vmin, cmap='RdYlBu', extent=None, gl=True, legend=True):
        if extent == None:
            extent = self.extent
        fig, ax = self.make_cartopy_plot()
        fig.set_figheight(5.8)

        colorb = plt.cm.ScalarMappable(cmap=cmap, norm=colors.Normalize(vmin=vmin, vmax=vmax))
        plt.title(title)
        if gl:
            self.plot_temporal_grounding_line(fig, ax, cmap='bone_r')
        
        
        if extent == None:
            extent = self.extent

        if gl != 'only':
        
            self.plot_geotiff(fname, fig, ax, alpha=1, cmap=cmap, vmin=vmin, vmax=vmax, legend=legend)


        self.mask_outside(extent=extent)
        self.add_cartopy_reference_info(fig, ax, extent=extent)
        fig.colorbar(colorb, orientation='vertical', label=label, ax=ax)
            
        
        print("Saving image...")
        name = OUTPUT + "images/" + title + ".png"
        plt.savefig(name, dpi=200)
        print(name)
        
        plt.close('all')

        
    def frame(self):
        p = Plotting()
        for f in TO_FRAME.keys():
            if f.strip() == '':
                p.plot_only_geotiff(INPUT + 'to_frame/' + f, TO_FRAME[f]['title'], TO_FRAME[f]['label'],
                                    TO_FRAME[f]['vmax'], TO_FRAME[f]['vmin'], cmap=TO_FRAME[f]['cmap'], gl=TO_FRAME[f]['gl'], legend=False)

            else:
                p.plot_only_geotiff(INPUT + 'to_frame/' + f, TO_FRAME[f]['title'], TO_FRAME[f]['label'],
                                    TO_FRAME[f]['vmax'], TO_FRAME[f]['vmin'], cmap=TO_FRAME[f]['cmap'], gl=TO_FRAME[f]['gl'], legend=False)


    def plot_IPR_range(self, fm, frame):
        out = fm.get_ouput_files()

        out = out[out['FRAME'] == frame]
        total_dist=50
        out['Distance'] = total_dist * ((out['UTCTIMESOD'] - min(out['UTCTIMESOD'])) / (max(out['UTCTIMESOD']) - min(out['UTCTIMESOD'])))
        print(out) 
        #8778, 8393,
        self.plot_col(out, 'Distance', total_dist, 0, 'winter', 'Distance (km)',g_cbar='Grounding Line', g_cmap='magma')
        

'''
# EXAMPLE USES:


#
#plot_col(gdf, 'uncert', 2, 0, 'Reds', "Elevation Trend", velocities='trend')


show_extent()

plot_col(gdf, 'trend', 1, -1, 'bwr_r', "Elevation Trend (m/yr)", velocities=None)
plot_only_vel_trend_geotiff(cmap='RdBu')


#plot_col(gdf, 'uncert', 2, 0, 'Reds', "Elevation Trend Uncertainty", velocities=None)


#plot_only_vel_trend_geotiff()
#plot_only_vel_geotiff()

'''








