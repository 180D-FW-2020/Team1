#!/usr/bin/env bash 

#list name of packages
<<<<<<< HEAD
conda env create
echo "installing base packages"
conda create -y -n hitw python=3.6 numpy pandas joblib smbus2 paho-mqtt scikit-learn=0.23.2 -c conda-forge
conda activate hitw 
echo "finished" 
=======
echo "installing base packages"
conda create -y -n hitw python=3.6 numpy pandas joblib smbus2 paho-mqtt scikit-learn=0.23.2 -c conda-forge
conda activate hitw 
echo "finished" 
>>>>>>> 337036507a0e8eb0dec3eb840b30eae70b326c45
