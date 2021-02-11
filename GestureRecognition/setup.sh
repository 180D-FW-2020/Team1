#!/usr/bin/env bash 

#list name of packages
echo "installing base packages"
conda create -y -n hitw python=3.6 numpy pandas joblib smbus2 paho-mqtt scikit-learn=0.23.2 -c conda-forge
conda activate hitw 
echo "finished" 