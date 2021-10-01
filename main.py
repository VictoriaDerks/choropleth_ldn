"""
Script to clean LFB animal rescue data and create an animated map over time of the most frequently rescued animals per
borough.
"""

import imageio as imageio
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
import geopandas as gpd

# colourmap settings
# the map is matplotlib's Dark2, with one fewer colour.
norm = matplotlib.colors.Normalize(vmin=0, vmax=7)

cm = matplotlib.colors.ListedColormap(((0.10588235294117647, 0.6196078431372549, 0.4666666666666667),
                                       (0.8509803921568627, 0.37254901960784315, 0.00784313725490196),
                                       (0.4588235294117647, 0.4392156862745098, 0.7019607843137254),
                                       (0.9058823529411765, 0.1607843137254902, 0.5411764705882353),
                                       (0.4, 0.6509803921568628, 0.11764705882352941),
                                       (0.9019607843137255, 0.6705882352941176, 0.00784313725490196),
                                       (0.6509803921568628, 0.4627450980392157, 0.11372549019607843)))


def run():
    """
    Call the two functions.
    :return:
    """
    geometry_df, grouped_df = data_cleaning_and_loading()
    make_plots_and_gif(geometry_df, grouped_df)  # make the plots


def data_cleaning_and_loading():
    """
    Load the data into dataframes and clean them.
    * convert borough names to lower case
    * remove entries with boroughs that aren't part of Greater London (excluding City of London)
    * remove entries without a borough
    * shorted "Unknown - ..." entries
    * calculate centre coordinates of boroughs
    * normalise number of hectares to be between -1 and 1.
    :return:
    """
    # DATA CLEANING AND LOADING
    df = pd.read_csv("Animal Rescue incidents attended by LFB from Jan 2009.csv", encoding="mbcs")
    df["Borough"] = df.Borough.str.lower()
    # filter out boroughs that aren't in Greater London
    df = df[~df.Borough.isin(["brentwood", "broxbourne", "epping forest", "tandridge"])]
    # drop entries where borough isn't available
    df.dropna(subset=["Borough"], inplace=True)
    # shorten "Unknown - ...." animal entries to just "Unknown"
    df.loc[df['AnimalGroupParent'].str.contains('Unknown'), 'AnimalGroupParent'] = 'Unknown'

    fp = "statistical-gis-boundaries-london/ESRI/London_Borough_Excluding_MHW.shp"
    map_df = gpd.read_file(fp)
    map_df["NAME"] = map_df.NAME.str.lower()
    # get the center of each borough
    map_df["centroids"] = map_df["geometry"].apply(lambda row: tuple([row.centroid.coords]))
    # normalise the number of hectares
    map_df["hectares_norm"] = 2 * (map_df.HECTARES - map_df.HECTARES.min()) / (
                map_df.HECTARES.max() - map_df.HECTARES.min()) - 1

    # only select relevant fields
    filtered_df = df.filter(["CalYear", "Borough", "AnimalGroupParent"])

    agg_df = filtered_df.groupby(["CalYear", "Borough"]).agg(lambda x: x.value_counts().index[0])
    # from animal names to integers per category
    agg_df["AnimalCodes"] = pd.factorize(agg_df.AnimalGroupParent)[0]

    return map_df, agg_df


def make_plots_and_gif(map_df, data_df):
    """
    Create the individual frames and final gif. Save them all down in fig/
    :param map_df: dataframe with London mapping info
    :param data_df: dataframe with animal type info
    :return:
    """
    gif_img = []
    merged = data_df.join(map_df.set_index('NAME'), on=['Borough'])  # combined dfs

    for year_idx in range(data_df.index.get_level_values(0).nunique()):
        year = data_df.index.get_level_values(0).unique()[year_idx]

        # create plot with shapes
        fig, ax = plt.subplots()
        current_gdf = gpd.GeoDataFrame(merged.loc[year])
        # colour of borough depends on animal
        current_gdf.plot(column="AnimalCodes", cmap=cm, norm=norm, linewidth=0.4, edgecolor="#737373", ax=ax)

        plt.title(f"Most frequent animal rescues by the London Fire Brigade")
        plt.axis("off")
        # source annotation
        plt.annotate("Source: London Datastore, 2021", xy=(0.60, .85), xycoords='figure fraction',
                     horizontalalignment='left', verticalalignment='top',
                     fontsize=8, color='#555555')
        # year annotations
        plt.annotate(f"{year}", xy=(0.75, .25), xycoords='figure fraction',
                     horizontalalignment='left', verticalalignment='top',
                     fontsize=20, color='black')

        # add annotation of animal per borough
        for borough in merged.loc[year].index:
            plt.annotate(merged.AnimalGroupParent.loc[year, borough],
                         (merged.centroids.loc[year, borough][0][0][0], merged.centroids.loc[year, borough][0][0][1]),
                         ha="center",
                         fontsize=10 + 3 * merged.hectares_norm.loc[year, borough])  # scale annotation by borough size
        # plt.show()
        file_name = f"fig/rescues_{year}.png"
        fig.savefig(file_name, dpi=300)
        gif_img.append(imageio.imread(file_name))

    # durations of each frame
    durations = [0.5]*12
    durations.append(2)
    # create GIF
    imageio.mimsave("fig/final.gif", gif_img, format='GIF', duration=durations)


if __name__ == '__main__':
    run()
