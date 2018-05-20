import model as m
import train_valid_split as tvs
import logging


# TODO multiple handlers, including file with datetime in its name
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger('train_eval')


def train_validate():
    mb_size = 1  #2  # as meta params?
    epochs = 1
    channels_sf = 1  #2
    model_name = "test"
    model_load = None  # 'm1'
    model_save = 'm2-x'
    data_split = 'data-split.json'
    data_split_part = 0

    unet = m.create_model(model_name, channels_sf, training=True)
    dataset = tvs.select_part_for_training(tvs.load_from_file(data_split), data_split_part)
    for i in range(epochs):
        log.info('------- Training: NEW EPOCH #{} (of {}) ---------'.format(i+1, epochs))
        load_path = ('models/{}.ckpt'.format(model_load) if model_load else None) \
                    if i == 0 else 'models/{}-e{}.ckpt'.format(model_save, i - 1)
        save_path = 'models/{}.ckpt'.format(model_save) if i == epochs - 1 \
                    else 'models/{}-e{}.ckpt'.format(model_save, i)
        save_config = {
            'initial_load': load_path,
            'emergency_save': 'models/{}-emergency.ckpt'.format(model_save),
            'emergency_after_batches': 100,
            'final_save': save_path,
        }
        unet.train(dataset, mb_size, save_config)
        # unet.validate(dataset, 'models/m2-emergency.ckpt')  # TODO put here głód staff
        unet.validate(dataset, save_path)


def evaluate():
    channels_sf = 1  #2
    model_name = "test"
    model_load = 'm2-emergency'
    data_dir = 'D:/students/dnn/assignment2/test/images'

    unet = m.create_model(model_name, channels_sf)
    dataset = tvs.get_evaluation_set(data_dir)
    log.info('------- Evaluation ({} images) ---------'.format(len(dataset)))
    unet.evaluate(dataset, 'models/{}.ckpt'.format(model_load))


if __name__ == '__main__':
    train_validate()
    # evaluate()