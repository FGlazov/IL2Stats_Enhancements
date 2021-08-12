import json
import random

import numpy as np

SAMPLE = 'SAMPLE'  # A sample of ammo breakdowns. Holds up to SAMPLE_SIZE many elements.
SAMPLE_SIZE = 50
RESERVOIR_COUNTER = 'RESERVOIR_COUNTER'  # Helper int that is used for "reservoir sampling", single pass fair sampling.


# https://stackoverflow.com/a/47626762
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def update_reservoir(sample_dict, reservoir_dict):
    """
    reservoir_dict has SAMPLE and RESERVOIR values. The SAMPLE is a json of a numpy array, where each row corresponds to
    a single sample. The columns correspond to the keys in sample_dict, sorted alphabetically. The values in each row
    then correspond to the values of a sample dict. In effect the reservoir_dict contains  a sample of size
    <= SAMPLE_SIZE, which stores some selected sample_dicts for later use.

    We only see each sample_dict once for performance reasons. So we use an online sampling algorithm. Reservoir
    sampling is used, this code is based on https://stackoverflow.com/a/42532968.
    """
    new_row = np.empty([1, len(sample_dict)])

    for i, ammo_key in enumerate(sorted(list(sample_dict))):
        new_row[0, i] = sample_dict[ammo_key]

    reservoir = get_samples(reservoir_dict, len(sample_dict))

    reservoir_updated = False
    if reservoir_dict[RESERVOIR_COUNTER] < SAMPLE_SIZE:
        reservoir = np.append(reservoir, new_row, axis=0)
        reservoir_updated = True
    else:
        n = random.randint(0, reservoir_dict[RESERVOIR_COUNTER])
        if n < SAMPLE_SIZE:
            reservoir[n] = new_row
            reservoir_updated = True

    reservoir_dict[RESERVOIR_COUNTER] += 1
    if reservoir_updated:
        reservoir_dict[SAMPLE] = json.dumps(reservoir, cls=NumpyEncoder)


def get_samples(reservoir_dict, nr_ammo_types):
    if SAMPLE not in reservoir_dict:
        return []

    if reservoir_dict[SAMPLE] is not None:
        json_load = json.loads(reservoir_dict[SAMPLE])
        reservoir = np.asarray(json_load)
    else:
        reservoir = np.empty((0, nr_ammo_types))
    return reservoir
