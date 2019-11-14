###############################################################################
# Makefile for MADT project
#  _    _    __   ___   _____
# | \  / |  /_|| || \\ |_____|  
# |_|\/|_| /_/|| ||_//   |_|
#
# Check the license: https://github.com/dltcspbu/madt/blob/master/LICENSE.md
#
# Author: DLTC
# Last change: November 13, 2019 
# email: dltc@spbu.ru
# URL: madt.io
#
###############################################################################

PKG_NAME:=madt
PKG_VERSION:=1.0
PKG_RELEASE:=1

MADT_DIR:=$(realpath $(dir $(firstword $(MAKEFILE_LIST))))

# 
# Define dirs for lab and sockets yourself.
# By default we place it in madt folder.
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
	
default:
	@echo "Installation of $(PKG_NAME) started"
	@echo "Check the requrements. Uninstalled python packages will be installed."
	@echo
	@pip3 install -q -r requirements.txt	
	@echo
	@sh images/build.sh
	@echo "export HOSTNAME=$(HOSTNAME)" >> ~/.bashrc
	@echo "export MADT_LABS_DIR=$(MADT_LABS_DIR)" >> ~/.bashrc
	@echo "export MADT_LABS_SOCKETS_DIR=$(MADT_LABS_SOCKETS_DIR)" >> ~/.bashrc
	@cp -r $(MADT_DIR)/madt_lib $(INSTALL_DIR)
	@echo "Successfully installed!"
