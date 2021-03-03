#!/usr/bin/env bash 

#list name of packages
echo "installing base packages"
conda create -y -n hitw python=3.6 numpy joblib smbus2 paho-mqtt scikit-learn=0.19.0 -c conda-forge
conda activate hitw 
echo "finished" 
