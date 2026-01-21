from plotting import * 



fig, ax = plt.subplots()
plt.title("Velocity (" + str(year) + ")")
plt.xlim(extent[0], extent[1])
plt.ylim(extent[2],  extent[3])
plot_geotiff('aa', fig, ax, vmax=600, vmin=0, label = "Velocity (m/yr)", cmap='viridis')
plot_glacier_borders(fig, ax)