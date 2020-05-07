# Advandrone
## First steps of a drone

This repository holds the first steps to control a drone using ROS and specially MAVROS. This repository doesn't contain all the files to run the simulations or the real project. This project it is based on other open sources codes and in this README it will be explained how to have the environment to run it. 

The aim of this project is to finally run a real drone who will travel a little distance in an autonomous form. The real drone will be an hexacopter but the simulation will work in a quadcopter. 

## Advandrone Team

* Miguel López Delgado: miguel.lopez04@estudiant.upf.edu 
* Abdussalam alajami: Abdussalam.alajami@upf.edu

## Environment installation

This repository contains code supported on the following installation:

* Install ROS Melodic following the steps included in this [webpage](http://wiki.ros.org/melodic)
* Follow the steps of [GAAS](https://gaas.gitbook.io/guide/software-realization-build-your-own-autonomous-drone/build-your-own-autonomous-drone-e01-offboard-control-and-gazebo-simulation) (we will change files of this environment in order to make our properly simulations. 
  * Skip the installation of ROS Melodic 
  * Skip the point 2. Using Docker

## Material

* 1 PC - With Linux 18.04 
* 1 - [Pixhawk](https://pixhawk.org/) where we will install Linux 18.04
* 1 - [Raspberry](https://www.raspberrypi.org/)
* 6 - proppellers
* 6 - ESC
* 1 - battery
* 1 - drone base
* 6 - motors
* ... 

## catkin_ws

The files included in this directory have to be included in the GAAS project we have downloaded before. There are new files and there are files that have been changed. Take care to have the new files instead the older ones. 

This contains the main files to run the drone simulation. In commander.py there is the rute that the drone will take. This file can be modified depending on the desire of the user. 

## listener

This directory doesn't need to be downloaded in an exact directory.

This contains the functions to read the data of each sonar sensor. Depending on the distance the drone will evit an obstacle, will block a movement or will unblock the movement. There is also the possibility to make the drone return as much as possible to the desired position.  

## building_editor_models

Here you can find some buildings that you can use in your simulations to see what happens and how the drone react to the walls. 



   
