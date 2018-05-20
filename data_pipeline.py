import tensorflow as tf
from params import *
import numpy as np


# https://cs230-stanford.github.io/tensorflow-input-data.html
# https://www.tensorflow.org/versions/master/performance/datasets_performance
def build_train_input_pipeline(images_labels_files, mb_size):
    # TODO I/O interleaving?
    dataset = tf.data.Dataset.from_tensor_slices(images_labels_files)
    dataset = dataset.shuffle(len(images_labels_files))
    dataset = dataset.map(load_train_data, num_parallel_calls=PARALLEL_CALLS)
    dataset = dataset.map(train_data_augmentation, num_parallel_calls=PARALLEL_CALLS)
    dataset = dataset.batch(mb_size)
    dataset = dataset.prefetch(HOW_MANY_PREFETCH)
    return dataset


def build_evaluate_input_pipeline(images_labels_files, for_validation=False):
    # TODO I/O interleaving?
    dataset = tf.data.Dataset.from_tensor_slices(images_labels_files)
    dataset = dataset.shuffle(len(images_labels_files))
    if for_validation:
        dataset = dataset.map(load_validation_data, num_parallel_calls=PARALLEL_CALLS)
        dataset = dataset.map(validation_data_augmentation, num_parallel_calls=PARALLEL_CALLS)
    else:
        dataset = dataset.map(load_evaluation_data, num_parallel_calls=PARALLEL_CALLS)
    dataset = dataset.batch(1)
    dataset = dataset.prefetch(HOW_MANY_PREFETCH)
    return dataset


def load_train_data(image_label_file):
    image_string = tf.read_file(image_label_file[0])
    label_string = tf.read_file(image_label_file[1])

    # Don't use tf.image.decode_image, or the output shape will be undefined
    image = tf.image.decode_jpeg(image_string, channels=IMAGE_CHANNELS, ratio=1)
    label = tf.image.decode_png(label_string, channels=LABEL_CHANNELS)

    def scale_up(img, lbl, min_edge_val):
        shape = tf.cast(tf.shape(img), tf.float64)
        ratio = TRAIN_IMG_EDGE_SIZE / min_edge_val
        new_height = tf.maximum(TRAIN_IMG_EDGE_SIZE, tf.cast(shape[0] * ratio, tf.int32))
        new_width = tf.maximum(TRAIN_IMG_EDGE_SIZE, tf.cast(shape[1] * ratio, tf.int32))
        new_size = [new_height, new_width]
        img = tf.image.resize_images(img, new_size, method=tf.image.ResizeMethod.BILINEAR, align_corners=True)
        lbl = tf.image.resize_images(lbl, new_size, method=tf.image.ResizeMethod.NEAREST_NEIGHBOR, align_corners=True)
        return tf.cast(img, tf.uint8), lbl

    min_edge = tf.minimum(tf.shape(image)[0], tf.shape(image)[1])
    image, label = tf.cond(min_edge < TRAIN_IMG_EDGE_SIZE,
                           lambda: scale_up(image, label, min_edge),
                           lambda: (image, label))

    image_label = tf.concat([image, label], axis=2)
    image_label = tf.random_crop(image_label,
                                 [TRAIN_IMG_EDGE_SIZE, TRAIN_IMG_EDGE_SIZE, IMAGE_CHANNELS + LABEL_CHANNELS])
    image, label = tf.split(image_label, [IMAGE_CHANNELS, LABEL_CHANNELS], axis=2)

    # This will convert to float values in [0, 1]
    image = tf.image.convert_image_dtype(image, tf.float32)

    return image, label


def train_data_augmentation(image, label):
    rand = tf.random_uniform([], 0, 1.0)
    image, label = tf.cond(rand < 0.5,
                           lambda: (flip_left_right(image), flip_left_right(label)),
                           lambda: (image, label))
    # TODO scaling
    # TODO rotation
    return image, label


def validation_data_augmentation(image, label):
    image2, label2 = flip_left_right(image), flip_left_right(label)
    return [(image, label), (image2, label2)]


def flip_left_right(image):
    # image is [height x width x channels]
    return tf.reverse(image, axis=[1])  # reverse columns


def load_validation_data(image_label_file):
    image_string = tf.read_file(image_label_file[0])
    image = tf.image.decode_jpeg(image_string, channels=IMAGE_CHANNELS, ratio=1)
    image = tf.image.convert_image_dtype(image, tf.float32)

    label_string = tf.read_file(image_label_file[1])
    label = tf.image.decode_png(label_string, channels=LABEL_CHANNELS)

    return image, label


def load_evaluation_data(image_file):
    image_string = tf.read_file(image_file[0])
    image = tf.image.decode_jpeg(image_string, channels=IMAGE_CHANNELS, ratio=1)
    image = tf.image.convert_image_dtype(image, tf.float32)

    basename = image_file[1]

    return image, basename


def encode_and_save_to_file(filename, preds):
    data_str = tf.image.encode_png(preds)
    return tf.write_file(filename, data_str)


def split_into_chunks(image):
    # shape is [batch x height x width x channels]
    hi, wi = image.shape[1:3]
    hw, ww = EVAL_IMG_SIZE
    slices = []

    for row in range(0, hi, hw):
        for col in range(0, wi, ww):
            r1 = max(0, row-EVAL_MARGIN)
            r2 = min(hi, row+hw+EVAL_MARGIN)
            c1 = max(0, col-EVAL_MARGIN)
            c2 = min(wi, col+ww+EVAL_MARGIN)
            slices.append(image[:, r1:r2, c1:c2])
    return slices


def merge_chunks(chunks, shape):
    image = np.zeros(shape, dtype=np.uint8)
    hi, wi = shape[1:3]
    hw, ww = EVAL_IMG_SIZE

    ch_it = iter(chunks)
    for row in range(0, hi, hw):
        for col in range(0, wi, ww):
            r1 = 0 if row == 0 else EVAL_MARGIN
            c1 = 0 if col == 0 else EVAL_MARGIN
            ch = next(ch_it)
            image[:, row:row+hw, col:col+ww] = ch[:, r1:r1+hw, c1:c1+ww]
    return image


def color_labels(labels):
    sh = list(labels.shape)
    sh[3] = 3
    colored = np.array([palette[c] for c in np.nditer(labels)])
    return np.reshape(colored, sh)


palette = np.array([
   [165,  42,  42],
   [  0, 192,   0],
   [196, 196, 196],
   [190, 153, 153],
   [180, 165, 180],
   [102, 102, 156],
   [102, 102, 156],
   [128,  64, 255],
   [140, 140, 200],
   [170, 170, 170],
   [250, 170, 160],
   [ 96,  96,  96],
   [230, 150, 140],
   [128,  64, 128],
   [110, 110, 110],
   [244,  35, 232],
   [150, 100, 100],
   [ 70,  70,  70],
   [150, 120,  90],
   [220,  20,  60],
   [255,   0,   0],
   [255,   0,   0],
   [255,   0,   0],
   [200, 128, 128],
   [255, 255, 255],
   [ 64, 170,  64],
   [128,  64,  64],
   [ 70, 130, 180],
   [255, 255, 255],
   [152, 251, 152],
   [107, 142,  35],
   [  0, 170,  30],
   [255, 255, 128],
   [250,   0,  30],
   [  0,   0,   0],
   [220, 220, 220],
   [170, 170, 170],
   [222,  40,  40],
   [100, 170,  30],
   [ 40,  40,  40],
   [ 33,  33,  33],
   [170, 170, 170],
   [  0,   0, 142],
   [170, 170, 170],
   [210, 170, 100],
   [153, 153, 153],
   [128, 128, 128],
   [  0,   0, 142],
   [250, 170,  30],
   [192, 192, 192],
   [220, 220,   0],
   [180, 165, 180],
   [119,  11,  32],
   [  0,   0, 142],
   [  0,  60, 100],
   [  0,   0, 142],
   [  0,   0,  90],
   [  0,   0, 230],
   [  0,  80, 100],
   [128,  64,  64],
   [  0,   0, 110],
   [  0,   0,  70],
   [  0,   0, 192],
   [ 32,  32,  32],
   [  0,   0,   0],
   [  0,   0,   0]
])
