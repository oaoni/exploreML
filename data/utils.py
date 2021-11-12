import os
import pandas as pd

def saveActiveH5(data_dict, sampling_dict, fname='exploreML/exploreML/data/active_data.h5'):
    s = pd.HDFStore(fname) # ideally, check if exists first

    for key, value in data_dict.items():
        name = os.path.join('data',key)
        try:
            s[name] = value
        except TypeError:
            s[name] = pd.DataFrame(value)

    for key, value in sampling_dict.items():
        name = os.path.join('samples',key)
        try:
            s[name] = value
        except TypeError:
            s[name] = pd.DataFrame(value)

    print('Pandas h5py file saved to {}'.format(fname))
    s.close()

def loadActiveH5(fname='exploreML/exploreML/data/active_data.h5'):
    data_dicts = {'samples':{},'data':{}}

    s = pd.HDFStore(fname)
    h5data = [x.split('/')[1:] for x in s.keys()]

    for group,key in h5data:
        name = os.path.join(group, key)
        data_dicts[group][key] = s.get(name)

    s.close()
    return data_dicts['data'], data_dicts['samples']
