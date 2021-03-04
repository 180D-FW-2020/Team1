#!/usr/bin/env bash 

#list name of packages
echo "installing base packages"
conda create -y -n hitw python numpy pandas joblib smbus2 paho-mqtt scikit-learn opencv speechrecognition boto3 paramiko -c conda-forge
# conda activate hitw 
echo "finished" 
