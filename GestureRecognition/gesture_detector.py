from os.path import curdir
import sys
import os
import IMU
import datetime
import numpy as np 
from joblib import load
from sklearn import preprocessing

CHECK_TIME_INCREMENT_MS = 200
SAMPLE_SIZE_MS = 1500

ACC_LPF_FACTOR = 0.4    # Low pass filter constant for accelerometer
MAG_LPF_FACTOR = 0.4    # Low pass filter constant magnetometer
ACC_MEDIANTABLESIZE = 9         # Median filter table size for accelerometer. Higher = smoother but a longer delay
MAG_MEDIANTABLESIZE = 9         # Median filter table size for magnetometer. Higher = smoother but a longer delay

magXmin =  0
magYmin =  0
magZmin =  0
magXmax =  0
magYmax =  0
magZmax =  0

oldXMagRawValue = 0
oldYMagRawValue = 0
oldZMagRawValue = 0
oldXAccRawValue = 0
oldYAccRawValue = 0
oldZAccRawValue = 0

#Setup the tables for the median filter. Fill them all with '1' so we dont get devide by zero error
acc_medianTable1X = [1] * ACC_MEDIANTABLESIZE
acc_medianTable1Y = [1] * ACC_MEDIANTABLESIZE
acc_medianTable1Z = [1] * ACC_MEDIANTABLESIZE
acc_medianTable2X = [1] * ACC_MEDIANTABLESIZE
acc_medianTable2Y = [1] * ACC_MEDIANTABLESIZE
acc_medianTable2Z = [1] * ACC_MEDIANTABLESIZE
mag_medianTable1X = [1] * MAG_MEDIANTABLESIZE
mag_medianTable1Y = [1] * MAG_MEDIANTABLESIZE
mag_medianTable1Z = [1] * MAG_MEDIANTABLESIZE
mag_medianTable2X = [1] * MAG_MEDIANTABLESIZE
mag_medianTable2Y = [1] * MAG_MEDIANTABLESIZE
mag_medianTable2Z = [1] * MAG_MEDIANTABLESIZE

class gestureRecognizer: 

    def __init__(self): 
        global SAMPLE_SIZE_MS

        IMU.detectIMU()     #Detect if BerryIMU is connected.
        if(IMU.BerryIMUversion == 99):
            print(" No BerryIMU found... exiting ")
            sys.exit()
        IMU.initIMU()       #Initialise the accelerometer, gyroscope and compass

        print('Starting operation')

        self.header = ["time_ms", "delta_ms"] + self.get_sensor_headers()
        self.maxlen = int(SAMPLE_SIZE_MS / 10)
        self.elapsed_ms = 0
        self.previous_elapsed_ms = 0
        self.last_classified = 0
        self.last_classification = "negative_trim"
        self.min_max_scaler = preprocessing.MinMaxScaler()
        self.model = load(os.path.join(curdir, 'models', '267pt_model.joblib')) 
        self.start = datetime.datetime.now()

    def collect(self): 
        global ACC_LPF_FACTOR, ACC_MEDIANTABLESIZE, oldXAccRawValue, oldYAccRawValue, oldZAccRawValue
        global MAG_LPF_FACTOR, MAG_MEDIANTABLESIZE, oldXMagRawValue, oldYMagRawValue, oldZMagRawValue
        global acc_medianTable1X, acc_medianTable1Y, acc_medianTable1Z, acc_medianTable2X, acc_medianTable2Y, acc_medianTable2Z
        global mag_medianTable1X, mag_medianTable1Y, mag_medianTable1Z, mag_medianTable2X, mag_medianTable2Y, mag_medianTable2Z

        #Read the accelerometer,gyroscope and magnetometer values
        ACCx = IMU.readACCx()
        ACCy = IMU.readACCy()
        ACCz = IMU.readACCz()
        GYRx = IMU.readGYRx()
        GYRy = IMU.readGYRy()
        GYRz = IMU.readGYRz()
        MAGx = IMU.readMAGx()
        MAGy = IMU.readMAGy()
        MAGz = IMU.readMAGz()

        #Apply compass calibration
        MAGx -= (magXmin + magXmax) /2
        MAGy -= (magYmin + magYmax) /2
        MAGz -= (magZmin + magZmax) /2

        ###############################################
        #### Apply low pass filter ####
        ###############################################
        ACCx =  ACCx  * ACC_LPF_FACTOR + oldXAccRawValue*(1 - ACC_LPF_FACTOR);
        ACCy =  ACCy  * ACC_LPF_FACTOR + oldYAccRawValue*(1 - ACC_LPF_FACTOR);
        ACCz =  ACCz  * ACC_LPF_FACTOR + oldZAccRawValue*(1 - ACC_LPF_FACTOR);
        MAGx =  MAGx  * MAG_LPF_FACTOR + oldXMagRawValue*(1 - MAG_LPF_FACTOR);
        MAGy =  MAGy  * MAG_LPF_FACTOR + oldYMagRawValue*(1 - MAG_LPF_FACTOR);
        MAGz =  MAGz  * MAG_LPF_FACTOR + oldZMagRawValue*(1 - MAG_LPF_FACTOR);

        oldXAccRawValue = ACCx
        oldYAccRawValue = ACCy
        oldZAccRawValue = ACCz
        oldXMagRawValue = MAGx
        oldYMagRawValue = MAGy
        oldZMagRawValue = MAGz

        #########################################
        #### Median filter for accelerometer ####
        #########################################
        # cycle the table
        for x in range (ACC_MEDIANTABLESIZE-1,0,-1 ):
            acc_medianTable1X[x] = acc_medianTable1X[x-1]
            acc_medianTable1Y[x] = acc_medianTable1Y[x-1]
            acc_medianTable1Z[x] = acc_medianTable1Z[x-1]

        # Insert the lates values
        acc_medianTable1X[0] = ACCx
        acc_medianTable1Y[0] = ACCy
        acc_medianTable1Z[0] = ACCz

        # Copy the tables
        acc_medianTable2X = acc_medianTable1X[:]
        acc_medianTable2Y = acc_medianTable1Y[:]
        acc_medianTable2Z = acc_medianTable1Z[:]

        # Sort table 2
        acc_medianTable2X.sort()
        acc_medianTable2Y.sort()
        acc_medianTable2Z.sort()

        # The middle value is the value we are interested in
        ACCx = acc_medianTable2X[int(ACC_MEDIANTABLESIZE/2)];
        ACCy = acc_medianTable2Y[int(ACC_MEDIANTABLESIZE/2)];
        ACCz = acc_medianTable2Z[int(ACC_MEDIANTABLESIZE/2)];

        #########################################
        #### Median filter for magnetometer ####
        #########################################
        # cycle the table
        for x in range (MAG_MEDIANTABLESIZE-1,0,-1 ):
            mag_medianTable1X[x] = mag_medianTable1X[x-1]
            mag_medianTable1Y[x] = mag_medianTable1Y[x-1]
            mag_medianTable1Z[x] = mag_medianTable1Z[x-1]

        # Insert the latest values
        mag_medianTable1X[0] = MAGx
        mag_medianTable1Y[0] = MAGy
        mag_medianTable1Z[0] = MAGz

        # Copy the tables
        mag_medianTable2X = mag_medianTable1X[:]
        mag_medianTable2Y = mag_medianTable1Y[:]
        mag_medianTable2Z = mag_medianTable1Z[:]

        # Sort table 2
        mag_medianTable2X.sort()
        mag_medianTable2Y.sort()
        mag_medianTable2Z.sort()

        # The middle value is the value we are interested in
        MAGx = mag_medianTable2X[int(MAG_MEDIANTABLESIZE/2)];
        MAGy = mag_medianTable2Y[int(MAG_MEDIANTABLESIZE/2)];
        MAGz = mag_medianTable2Z[int(MAG_MEDIANTABLESIZE/2)];

        ##################### END Tilt Compensation ########################
        
        accel = [ACCx, ACCy, ACCz]
        mag = [MAGx, MAGy, MAGz] 
        gyro = [GYRx, GYRy, GYRz]
        euler = [0, 0, 0]
        quaternion = [0, 0, 0, 0]
        lin_accel = [0, 0, 0]
        gravity = [0, 0, 0]

        return accel + mag + gyro + euler + quaternion + lin_accel + gravity 

    # initialize sensor column labels 
    def get_sensor_headers(self):
        header = []
        for sensor in ["accel_ms2", "mag_uT", "gyro_degs", "euler_deg",
                    "quaternion",
                    "lin_accel_ms2", "gravity_ms2"]:
            if sensor is "quaternion":
                header.append(sensor + "_w")
            header.append(sensor + "_x")
            header.append(sensor + "_y")
            header.append(sensor + "_z")
        return header
    
    def classify(self): 
        global CHECK_TIME_INCREMENT_MS
        data = [] 
        df = {}

        # collects 1.5s of data and predicts gesture based on model
        while True: 
            row = [self.elapsed_ms, int(self.elapsed_ms - self.previous_elapsed_ms)] + self.collect()
            data.append(row)
            self.previous_elapsed_ms = self.elapsed_ms
            
            if self.elapsed_ms - self.last_classified >= CHECK_TIME_INCREMENT_MS and len(data) == self.maxlen:
                # get data in columnwise fashion 
                for j in range(len(self.header)):
                    column = []
                    for i in range(len(data)):
                        column.append(data[i][j]) 
                    df[self.header[j]] = np.array(column) 
                
                features = self.get_model_features(df) + [0]
                prediction = self.model.predict([features])[0]

                if prediction != 'negative_trim' and self.last_classification != prediction:
                    print("========================>", prediction)

                self.last_classified = self.elapsed_ms
                self.last_classification = prediction 
                
                break 

            self.elapsed_ms = (datetime.datetime.now() - self.start).total_seconds() * 1000

        return str(self.last_classification)

    def get_model_features(self, trace, generate_feature_names=False):
        features = []
        trace["accel"] = np.linalg.norm(
            (trace["accel_ms2_x"], trace["accel_ms2_y"], trace["accel_ms2_z"]),
            axis=0)
        trace["gyro"] = np.linalg.norm(
            (trace['gyro_degs_x'], trace['gyro_degs_y'], trace['gyro_degs_z']),
            axis=0)

        for sensor in ['accel', 'gyro']:
            features_temp = self.get_features(trace[sensor], generate_feature_names)
            if generate_feature_names:
                features.extend([x + '_' + sensor for x in features_temp])
            else:
                features.extend(features_temp)

        if generate_feature_names:
            features.append('accel_z_peaks')
        else:
            normalized = self.min_max_scaler.fit_transform(
                trace['accel_ms2_z'].reshape(-1, 1).astype(np.float))[:, 0]  # normalize
            normalized = normalized[0:len(normalized):5]  # subsample
            normalized = np.diff(
                (normalized > 0.77).astype(int))  # convert to binary classifier
            normalized = normalized[normalized > 0]
            features.append(sum(normalized))
            normalized = self.min_max_scaler.fit_transform(
                trace['gyro_degs_z'].reshape(-1, 1).astype(np.float))[:, 0]  # normalize
            normalized = normalized[0:len(normalized):5]  # subsample
            normalized = np.diff(
                (normalized > 0.77).astype(int))  # convert to binary classifier
            normalized = normalized[normalized > 0]
            features.append(sum(normalized))

        return features

    def get_features(self, series, generate_feature_names=False):
        if generate_feature_names:
            return ['max', 'min', 'range', 'mean', 'std']
        features = []
        features.append(max(series))
        features.append(min(series))
        features.append(max(series) - min(series))
        features.append(series.mean())
        features.append(series.std())
        return features

# n = gestureRecognizer() 

# while True:
#     n.classify()