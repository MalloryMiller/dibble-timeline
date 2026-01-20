
import geopandas as gpd
import shapefile as shp
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.lines import Line2D
import rasterio as rs

from utils import *


gpgk_folder_name = 'gpkg_progress'

velocity_trends_tif = "shapefiles/velocities_measures.tif"#"shapefiles/velocity_trends.tif"

extent = [1.78e6, 1.92e6, -1.91e6,  -1.75e6]
basin_extent = [1, 2.1e6, -2.1e6, -0.75]

'''
class Plotting:
    def __init__(self, extent) 


'''

print("Reading trend file...")

gdf = gpd.read_file(ELEVATION_LOCATION)#'ATL11_trends_APS.gpkg')
##print(gdf.columns.tolist())


def plot_velocity(fname, year):
    fig, ax = plt.subplots()
    plt.title("Velocity (" + str(year) + ")")
    plt.xlim(extent[0], extent[1])
    plt.ylim(extent[2],  extent[3])
    plot_geotiff(fname, fig, ax, vmax=600, vmin=0, label = "Velocity (m/yr)", cmap='viridis')
    plot_glacier_borders(fig, ax)

def plot_elevation(fname, year):
    fig, ax = plt.subplots()
    plt.title("Elevation (" + str(year) + ")")
    plt.xlim(extent[0], extent[1])
    plt.ylim(extent[2],  extent[3])
    plot_geotiff(fname, fig, ax, vmax=2500, vmin=0, label = "Elevation (m)", cmap='copper')
    plot_glacier_borders(fig, ax)

def plot_geotiff(fname, fig, ax, vmax=600, vmin=0, label = "Velocity Trend Slope (m/yr)", cmap='viridis', alpha=0.5):
    with rs.open(fname) as f:
        img = f.read(1)
        minx, miny, maxx, maxy = f.bounds.left, f.bounds.bottom, f.bounds.right, f.bounds.top
        extent = [minx, maxx, miny, maxy]
        
    vmin = vmin
    vmax = vmax
    cmap = cmap
    
    colorb = plt.cm.ScalarMappable(cmap=cmap, norm=colors.Normalize(vmin=vmin, vmax=vmax))
    fig.colorbar(colorb, orientation='vertical', label=label, ax=ax)
    
    
    plt.imshow(img, cmap=cmap, extent = extent, origin='upper', vmin=vmin, vmax=vmax, alpha=alpha, zorder=-10)
    
    
def plot_shapefile(fname, color, z_order = 15, fill=False, extra_xs=[], extra_ys=[]):
    sf = shp.Reader(fname)
    for shape in sf.shapeRecords():
        x = [i[0] for i in shape.shape.points[:]] + extra_xs
        y = [i[1] for i in shape.shape.points[:]] + extra_ys
        if fill:
            plt.fill(x, y, color=color)
        else:
            plt.plot(x, y, color=color, zorder=z_order)
    
    
def plot_glacier_borders(fig, ax, grounding_color='black', glacial_color='blue', basin_color="red", fill=False, legend=True, basins=False):
    if basins:
        plot_shapefile(SHAPEFILES['basins'], basin_color, fill=fill)
    plot_shapefile(SHAPEFILES['iceshelf'], glacial_color, z_order = 15, fill=fill) # old: https://usicecenter.gov/Products/AntarcData
    plot_shapefile(SHAPEFILES['grounding'], grounding_color, z_order = 20, fill=fill) # Qantarctica
    
    if legend:
       leg = ax.legend([Line2D([0], [0], color=grounding_color, lw=1),
               Line2D([0], [0], color=glacial_color, lw=1)], 
              ['Grounding Line (Mouginot)', 'Ice Shelf Extent (Bindschadler)'], framealpha=1, loc='lower right')
       leg.set_zorder(100)
    
    
def mask_outside(mask_color='white', extent=extent):
    plot_shapefile(SHAPEFILES['oceanmask'], mask_color, fill=True, )
    
    
def plot_only_vel_geotiff(grounding_color='red', glacial_color='slategrey', extent=extent):
    fig, ax = plt.subplots()
    
    plot_geotiff("shapefiles/qantarctica_velocities.tif", fig, ax, alpha=1, color="RdYlBu")
    plot_glacier_borders(fig, ax, grounding_color=grounding_color, glacial_color=glacial_color)
    if extent:
       plt.xlim(extent[0], extent[1])
       plt.ylim(extent[2],  extent[3])
    
    print("Saving image...")
    plt.savefig("velocity_reading.png", dpi=200)
    print("velocity_reading.png")
    
    plt.close('all')


def plot_only_vel_trend_geotiff(grounding_color='black', glacial_color='slategrey', extent=extent, cmap="RdYlGn"):
    fig, ax = plt.subplots()
    plt.title("Velocity Trend (2010-2020)")
    
    plot_geotiff(velocity_trends_tif, fig, ax, vmax=10, vmin=-10,  label = "Velocity Trend (m/yr²)", cmap=cmap, alpha=1)
    plot_glacier_borders(fig, ax, grounding_color=grounding_color, glacial_color=glacial_color)
    mask_outside(extent=extent)
    
    if extent:
       plt.xlim(extent[0], extent[1])
       plt.ylim(extent[2],  extent[3])
    
    print("Saving image...")
    plt.savefig("velocity_trend_reading.png", dpi=200)
    print("velocity_trend_reading.png")
    
    plt.close('all')
    
    
def show_extent(extent=extent, glacial_color='black', extent_color='r', extent_line_color='r', linewidth=5):
    fig, ax = plt.subplots()
    plot_glacier_borders(fig, ax, grounding_color=(1, 0, 0, 0), glacial_color=glacial_color, basin_color=(1, 0, 0, 0), fill=True, legend=False)
    x_pos = [ extent[1],extent[0], extent[0], extent[1]]
    y_pos = [extent[2], extent[2], extent[3], extent[3]]
    plt.fill(x_pos, y_pos, color=extent_color, edgecolor=extent_line_color, linewidth=linewidth)
    
    print("Saving image...")
    plt.savefig("extent.png", dpi=200)
    print("extent.png")
    
    plt.close('all')



def plot_col(gdf, colm, vmax, vmin, cmap, color_label, grounding_color='black', glacial_color='slategrey', velocities=None, extent=extent):
    print("Plotting ATL11_" + colm + ".png")
    
    
    fig, ax = plt.subplots()
    
    plot_glacier_borders(fig, ax, grounding_color=grounding_color, glacial_color=glacial_color)
    
    colorb = plt.cm.ScalarMappable(cmap=cmap, norm=colors.Normalize(vmin=vmin, vmax=vmax))
    plt.title(' '.join(color_label.split(' ')[:-2] + ["(2010-2020)"]))
    
    gdf.to_crs("EPSG:3031")
    
    
    if velocities == 'trend':
       print("Plotting velocity trends...")
       plot_geotiff("shapefiles/velocity_trends.tif", fig, ax, vmax=10, vmin=-10,  label = "Velocity Trend Slope (m/yr²)", cmap=cmap)
    elif velocities:
       print("Plotting velocities...")
       plot_geotiff("shapefiles/qantarctica_velocities.tif", fig, ax, cmap=cmap)
    
    
    mask_outside(extent=extent)
    
    if extent:
       plt.xlim(extent[0], extent[1])
       plt.ylim(extent[2],  extent[3])
    
    
    # Smith
    #plt.ylim(-0.7e6, -0.5e6)
    #plt.xlim(-1.65e6, -1.3e6)
    
        
    fig.colorbar(colorb, orientation='vertical', label=color_label, ax=ax)
        
    print("Saving image...")
    plt.savefig(str(velocities) + "ATL11_" + colm + ".png", dpi=200)
    print("ATL11_" + colm + ".png")
    
    plt.close('all')

'''

#plot_col(gdf, 'trend', 1, -1, 'bwr_r', "Elevation Trend", velocities='trend')
#plot_col(gdf, 'uncert', 2, 0, 'Reds', "Elevation Trend", velocities='trend')


show_extent()

plot_col(gdf, 'trend', 1, -1, 'bwr_r', "Elevation Trend (m/yr)", velocities=None)
plot_only_vel_trend_geotiff(cmap='RdBu')


#plot_col(gdf, 'uncert', 2, 0, 'Reds', "Elevation Trend Uncertainty", velocities=None)


#plot_only_vel_trend_geotiff()
#plot_only_vel_geotiff()

'''














