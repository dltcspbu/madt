###############################################################################
# Makefile for MADT project
#  _    _    __   ___   _____
# | \  / |  /_|| || \\ |_____|  
# |_|\/|_| /_/|| ||_//   |_|
#
# \TODO Write copyright
#
# Author: DLTC
# Last change: November 13, 2019 
# URL: madt.io
###############################################################################

PKG_NAME:=madt
PKG_VERSION:=1.0
PKG_RELEASE:=1

MADT_DIR:=$(realpath $(dir $(firstword $(MAKEFILE_LIST))))

# 
# Define dirs for lab and sockets yourself
#
MADT_LABS_DIR:=$(MADT_DIR)/labs
MADT_LABS_SOCKETS_DIR:=$(MADT_DIR)/sockets

HOSTNAME:=localhost 

YUMCODE:=$(shell $(yum))

INSTALL_DIR:= 
ifeq ($(YUMCODE),1)
	INSTALL_DIR+=/usr/lib/python3/site-packages
else 
	INSTALL_DIR+=/usr/lib/python3/dist-packages
endif
	
# \TODO  check debian

default:
	@echo "Installation of $(PKG_NAME) started"
	@echo "Now run:"
	@echo "		sudo make install"
	@echo 

install: 
	@echo "export HOSTNAME=$(HOSTNAME)" >> ~/.bashrc
	@echo "export MADT_LABS_DIR=$(MADT_LABS_DIR)" >> ~/.bashrc
	@echo "export MADT_LABS_SOCKETS_DIR=$(MADT_LABS_SOCKETS_DIR)" >> ~/.bashrc
	@cp -r $(MADT_DIR)/madt_lib $(INSTALL_DIR)
	@echo "Successfully installed!"
