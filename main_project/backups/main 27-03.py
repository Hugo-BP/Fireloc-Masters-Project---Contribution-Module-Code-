"""
#### Import Libs
"""

import random
import tensorflow as tf
from sklearn.metrics import pairwise_distances, euclidean_distances

keras = tf.keras
from keras.layers import Input, Dense, LSTM, Embedding, Concatenate, Flatten
from keras.models import Model
from keras.utils import pad_sequences
from keras.preprocessing.text import Tokenizer

import numpy as np
import pandas as pd

from sklearn.cluster import DBSCAN

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D

"""
#### Define MACROS and Globals
"""

FILE_PATH = "C:\\Users\\Hugo\\Desktop\\test_project\\test_input.txt"
DBSCAN_DISTANCE = 30
DBSCAN_MIN_SIZE = 2
COORD_THRESHOLD = 20
UNIQUE_KEY_THRESHOLD = 15

keyword_dictionary = {
    "smoke": 0,
    "fire": 1,
    "explosive": 2,
    "gas": 3,
    "oil": 4,
    "petrol": 5,
    "urban": 6,
    "hospital": 7,
    "houses": 8,
    "population": 9,
}

"""
#### Read & Format Input
"""


# encodes keyword_dictionary keys into integers based on the key values
# this function defines the "index" of each keyword in the array using the value of the key.
def encode_keywords(keywords):
    encoder = {}
    for keyword, index in keywords.items():
        encoder[keyword] = index

    return encoder


# encodes keyword_dictionary keys into integers based on the key values
# the output is a 1D array of 0s and 1s. 1 = keyword_dictionary key is present in the inputted text
def encode_submission_keywords(keywords, keyword_encoder):
    n_keywords = len(keyword_encoder)
    keywords_encoded = np.zeros(n_keywords)

    for keyword in keywords:
        if keyword in keyword_encoder:
            keyword_index = keyword_encoder[keyword]
            keywords_encoded[keyword_index] = 1

        elif keyword != '':
            print(" UNKNOWN KEYWORD WARNING: " + keyword)

    return keywords_encoded


# it might be more efficient to simply re-encode the entire thing from scratch if new words are added
# this function goes through all the processed lines of input and updates the array, as well as updating the dictionary
def encode_and_update_submission_keywords(keywords, keyword_encoder):
    n_keywords = len(keyword_encoder)
    keywords_encoded = np.zeros(n_keywords)
    max_index = max(keyword_encoder.values()) + 1

    for keyword in keywords:
        if keyword in keyword_encoder:
            keyword_index = keyword_encoder[keyword]
            keywords_encoded[keyword_index] = 1
        else:
            keyword_encoder[keyword] = max_index
            keywords_encoded = np.append(keywords_encoded, 1)
            n_keywords += 1
            max_index += 1

    return keywords_encoded


# read input saved in PATH file
# expected func input: 1;185;99;1;0; (no keyword)
# expected func output: (1, 185.0, 99.0, 1, 0, array([0., 0., 0., 0., 0., 0., 0., 0., 0., 0.]))
# expected func input: 4;58;75;0;0;explosive-houses-urban
# expected func output: (4, 58.0, 75.0, 0, 0, array([0., 0., 1., 0., 0., 0., 1., 0., 1., 0.]))
def read_input(file_path, keyword_dict):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # list of numpy arrays
    data = []
    keyword_encoder = encode_keywords(keyword_dict)

    # go over each line and partition its data
    for line in lines:
        line = line.strip().split(';')
        submission_id = int(line[0])
        x = float(line[1])
        y = float(line[2])
        has_fire = int(line[3])
        has_smoke = int(line[4])
        # keywords are split based on the "-" char to include keywords with spaces ex. "toxic gas" (not in use)
        keywords = line[5].split("-")

        # encode the keywords into numeric arrays
        keywords_encoded = encode_submission_keywords(keywords, keyword_encoder)
        # join current iteration line into the input array
        data.append((submission_id, x, y, has_fire, has_smoke, keywords_encoded))

    return data


"""
#### Cluster Inputs based on similarity of each submission
"""


# this receives the raw but formatted input from "read_input" and the encoding func, and applies DBSCAN clustering
# this should result in a rough estimation of which event each submission belongs to
# the expected output is a dictionary of the following format:
# { key : [ data point, data point, data point, ...]
# where the key is the cluster label, and the value is an array
# of data points of the same format as the output from read_input()
def apply_DBSCAN_clustering(data):
    # get the x and y coordinates of the events
    coordinates = np.array([(d[1], d[2]) for d in data])

    # perform DBSCAN clustering
    db = DBSCAN(eps=DBSCAN_DISTANCE, min_samples=DBSCAN_MIN_SIZE).fit(coordinates)

    # get the labels assigned to each event by the clustering algorithm and
    # create a dictionary to store the data of each cluster along with their respective label
    clusters = {}
    for i, label in enumerate(db.labels_):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(data[i])

    return clusters


# simple plot clusters function for testing
def plot_clusters(clusters):
    for label, cluster in clusters.items():
        # Get x, y coordinates of the cluster members
        x = [event[1] for event in cluster]
        y = [event[2] for event in cluster]

        # Plot the cluster
        plt.scatter(x, y, label=f"Cluster {label}")

    # Add axis labels and legend
    plt.xlabel("X coordinate")
    plt.ylabel("Y coordinate")
    plt.legend()
    plt.show()


def plot_clusters2(clusters1, clusters2):
    fig, axs = plt.subplots(1, 2, figsize=(10, 5))

    # Plot the first set of clusters
    for label, cluster in clusters1.items():
        # Get x, y coordinates of the cluster members
        x = [event[1] for event in cluster]
        y = [event[2] for event in cluster]

        # Plot the cluster
        axs[0].scatter(x, y, label=f"Cluster {label}")

    # Add axis labels and legend to the first plot
    axs[0].set_xlabel("X coordinate")
    axs[0].set_ylabel("Y coordinate")
    #axs[0].legend()

    # Plot the second set of clusters
    for label2, cluster2 in clusters2.items():
        # Get x, y coordinates of the cluster members
        x = [event2[1] for event2 in cluster2]
        y = [event2[2] for event2 in cluster2]

        # Plot the cluster
        axs[1].scatter(x, y, label=f"Cluster {label2}")

    # Add axis labels and legend to the second plot
    axs[1].set_xlabel("X coordinate")
    axs[1].set_ylabel("Y coordinate")
    #axs[1].legend()

    # Show the plot
    plt.show()


"""
#### Apply Data Fusion to the clustered input data
"""


def apply_data_fusion(clusters):
    # Initialize an empty dictionary to store fused clusters
    fused_clusters = {}

    # Loop through each cluster
    for cluster_label, cluster_data_points in clusters.items():
        # Initialize a dictionary to store fused data points for the current cluster
        fused_data_points = {}

        # Loop through each data point in the cluster
        for data_point in cluster_data_points:
            # Extract the ID, x, y, has_fire, has_smoke, and keyword array from the data point
            dp_id, x, y, has_fire, has_smoke, key_arr = data_point

            # Flag to check whether to create a new fused data point
            create_new_fused_point = True

            # Loop through already existing fused data points in the cluster
            for fused_point_id, fused_point_data in fused_data_points.items():
                # Extract the fused x, y, and keyword array from the fused data point
                fused_x, fused_y, fused_fire, fused_smoke, fused_arr = fused_point_data

                # Check if the current data point is close enough to the current fused data point
                if euclidean_distances([[x, y]], [[fused_x, fused_y]])[0][0] < COORD_THRESHOLD:
                    # If the current data point has at least one matching keyword with the fused data point,
                    # merge the two points into the fused data point
                    if np.any(np.logical_and(key_arr, fused_arr)):
                        # Update the fused data point with the new information
                        fused_fire = fused_fire or has_fire
                        fused_smoke = fused_smoke or has_smoke
                        fused_arr = np.logical_or(key_arr, fused_arr).astype(int)
                        fused_x = (fused_x + x) / 2
                        fused_y = (fused_y + y) / 2

                        fused_point_data = (fused_x, fused_y, fused_fire, fused_smoke, fused_arr)

                        fused_data_points[fused_point_id] = fused_point_data
                        create_new_fused_point = False

                        break

                    # If the current data point has no matching keywords with the fused data point,
                    # check if it is close enough to be considered part of the same event
                    elif euclidean_distances([[x, y]], [[fused_x, fused_y]])[0][0] < UNIQUE_KEY_THRESHOLD:
                        # Merge the two points into the fused data point
                        fused_fire = fused_fire or has_fire
                        fused_smoke = fused_smoke or has_smoke
                        fused_arr = np.logical_or(key_arr, fused_arr).astype(int)
                        fused_x = (fused_x + x) / 2
                        fused_y = (fused_y + y) / 2

                        fused_point_data = (fused_x, fused_y, fused_fire, fused_smoke, fused_arr)

                        fused_data_points[fused_point_id] = fused_point_data
                        create_new_fused_point = False

                        break

            # If there's no existing fused data point to merge with, start a new one
            if create_new_fused_point:
                fused_data_points[dp_id] = (x, y, has_fire, has_smoke, key_arr.astype(int))

        # Add the fused data points to the fused clusters dictionary
        fused_clusters[cluster_label] = [(k, v[0], v[1], v[2], v[3], v[4]) for k, v in fused_data_points.items()]

    return fused_clusters


if __name__ == '__main__':
    data_input = read_input(FILE_PATH, keyword_dictionary)
    # 1;185;99;1;0;
    # 2;39;276;0;1;smoke
    # 3;158;113;1;1;fire-urban
    # 4;58;75;0;0;explosive-houses-urban
    # print(data_input[0])
    # print(data_input[1])
    # print(data_input[2])
    # print(data_input[3])
    # print(' ')

    clustered_data = apply_DBSCAN_clustering(data_input)

    # plot_clusters(clustered_data)

    # print(next(iter((clustered_data.items()))))  # print first key-value pair just for testing

    fused_data = apply_data_fusion(clustered_data)

    plot_clusters2(clustered_data, fused_data)

    # print(next(iter((fused_data.items()))))  # print first key-value pair just for testing
