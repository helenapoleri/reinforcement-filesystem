import threading
import numpy as np

from datetime import datetime, timedelta
from src.metadata.cloud_managment import CloudManagement
from src.exceptions.exceptions import InsufficientSpaceException
from multiprocessing import Process, Manager

CUT_TIME_SECONDS = 60


class Metadata():

    def __init__(self):
        self.manager = Manager()
        self.files = self.manager.dict()
        self.clouds = CloudManagement()
        self.lock = threading.RLock()

    def reset(self):
        for file in self.files.keys():
            self.files[file]['accesses'] = 0

    # def __init__(self, *args, **kwargs):
    #     self.files = dict(*args, **kwargs)
    #     self.clouds = CloudManagement()
    #     self.lock = threading.RLock()

    def __getitem__(self, key):
        return self.files.get(key, None)

    def __len__(self):
        return len(self.files)

    def __repr__(self):
        return "metadata = " + self.files.__repr__()

    def acquire_lock(self):
        self.lock.acquire()

    def release_lock(self):
        self.lock.release()

    def add_read(self, file):
        if(file in self.files):
            # print("PPPPPPPPP")
            # print(self.files[file]['accesses'])
            self.files[file]['accesses'] += 1
            # print(self.files[file]['accesses'])

    def add_file(self, file_name, file_length):
        cloud_id, cloud_name = self.choose_cloud_for_insertion(file_length)
        # self.files[file_name] = [0, file_length, cloud_name]
        self.files[file_name] = self.manager.dict({
            'cloud': cloud_name,
            'length': file_length,
            'accesses': 0})
        self.clouds.inc_dec_used_space(cloud_id, file_length)

    def del_file(self, file_name):
        file = self.files.pop(file_name)
        # cloud_id = self.clouds.get_cloud_id_by_name(file[2])
        cloud_id = self.clouds.get_cloud_id_by_name(file['cloud'])
        # self.clouds.inc_dec_used_space(cloud_id, -file[1])
        self.clouds.inc_dec_used_space(cloud_id, -file['length'])

    def rename_file(self, old, new):
        file = self.files.pop(old)
        self.files[new] = file

    def add_file_to_cloud(self, file_name, file_length, cloud_name):
        # print(cloud_name)
        if file_name not in self.files:
            self.files[file_name] = self.manager.dict({
                'cloud': cloud_name,
                'length': file_length,
                'accesses': 0})
            cloud_id = self.clouds.get_cloud_id_by_name(cloud_name)
            self.clouds.inc_dec_used_space(cloud_id, file_length)

    def get_last_reads(self, file):
        if(file in self.files):
            return file['accesses']
        else:
            return None

    def get_all_file_names(self):
        return list(self.files.keys())

    def get_file_cloud_name(self, file_name):
        if file_name in self.files:
            return self.files[file_name]['cloud']
        else:
            return None

    def inc_dec_file_length(self, file_name, diff):
        file = self.files[file_name]
        cloud_id = self.clouds.get_cloud_id_by_name(file['cloud'])
        self.clouds.inc_dec_used_space(cloud_id, diff)
        file['length'] += diff

    # def update_file_reads(self, file):
    #     if(file in self.files):
    #         now = datetime.now()
    #         f = self.files.get(file)
    #         #isto
    #         accesses = [ocorr for ocorr in f.accesses if (now - ocorr < timedelta(seconds = CUT_TIME_SECONDS))]
    #         f.accesses = accesses
    #         # ou isto (otimizacao para listas muito grandes)
    #         # i = 0
    #         # for ocorr in f.accesses:
    #         #     if now - ocorr >= timedelta(seconds = 60*1):
    #         #         i+=1
    #         #     else: break
    #         # f.accesses = f.accesses[i:]

    # def update_all(self):
    #     for file in self.files:
    #         self.update_file_reads(file)

    def choose_cloud_for_insertion(self, file_length):
        return self.clouds.choose_cloud_for_insertion(file_length)

    def cloud_outliers(self, cloud_name):
        # cloud_files_info = [(file.name, len(file.accesses)) for file in self.files.values() if file.provider == cloud_name]
        cloud_files_info = [(file_name, file['accesses'])
                            for file_name, file in self.files.items()
                            if file['cloud'] == cloud_name]
        sorted(cloud_files_info, key=lambda x: x[1])
        # print(cloud_files_info)
        accesses = [x[1] for x in cloud_files_info]
        lower_outliers = []
        upper_outliers = []
        if accesses != []:
            q1, q3 = np.percentile(accesses, [25, 75])
            avg = np.mean(accesses)
            iqr = q3 - q1
            lower_bound = q1 - (1.5 * iqr) 
            upper_bound = q3 + (1.5 * iqr) 
            # print((lower_bound, upper_bound))
            lower_outliers = [x[0] for x in cloud_files_info
                              if x[1] < lower_bound]
            upper_outliers = [x[0] for x in cloud_files_info
                              if x[1] > upper_bound]
        # print((lower_outliers, upper_outliers))
        return (lower_outliers, upper_outliers)

    def migration_data(self, clouds_migration_data):
        # self.update_all()
        for cloud_id in range(0, len(self.clouds)):
            (lower_outliers, upper_outliers) = self.cloud_outliers(
                self.clouds[cloud_id]["name"])
            if cloud_id != 0 and lower_outliers != []:
                for file_name in lower_outliers:
                    clouds_migration_data.append((file_name, cloud_id,
                                                  cloud_id - 1))
            if cloud_id < len(self.clouds) - 1 and upper_outliers != []:
                for file_name in upper_outliers:
                    clouds_migration_data.append((file_name, cloud_id,
                                                  cloud_id + 1))

        return clouds_migration_data

    # def migration_data(self):
    #     # self.update_all()
    #     clouds_migration_data = []
    #     for cloud_id in range(0, len(self.clouds)):
    #         (lower_outliers, upper_outliers) = self.cloud_outliers(self.clouds[cloud_id]["name"])
    #         clouds_migration_data.append((cloud_id, lower_outliers, upper_outliers))
    #     return clouds_migration_data

    def migrate(self, name, frm, to):
        file = self.files[name]
        to_cloud = self.clouds[to]
        # from_cloud = self.clouds[frm]
        if(to_cloud['used'] + file['length'] > to_cloud['total']):
            raise InsufficientSpaceException
        else:
            self.clouds.inc_dec_used_space(to, file['length'])
            self.clouds.inc_dec_used_space(frm, -file['length'])
            file['cloud'] = to_cloud['name']
