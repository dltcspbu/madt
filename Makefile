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

MLD:=$(MADT_LABS_DIR)

HOSTNAME:=localhost 

YUMCODE:=$(shell $(yum))

ifeq ($(YUMCODE),1)
	INSTALL_DIR+=/usr/lib/python3/site-packages
else 
	INSTALL_DIR+=/usr/lib/python3/dist-packages
endif

ifeq ($USER, "travis")
	INSTALL_DIR=/home/travis/virtualenv/python3.6.7/lib/python3.6/site-packages
endif

default:
	@echo "Installation of $(PKG_NAME) started"
	@echo "Check the requrements. Uninstalled python packages will be installed."
	@echo
	@pip3 install -q -r requirements.txt
	@if [ -d "tmpshards" ]; then rm -rf tmpshards; fi
	@git clone https://github.com/DesignRevision/shards-dashboard.git tmpshards
	@cp -r tmpshards/* madt_ui/static/
	@echo
	@sh images/build.sh
	@if [ ! -d "$(MADT_LABS_DIR)" ]; then mkdir $(MADT_LABS_DIR); fi
	@if [ ! -d "$(MADT_LABS_SOCKETS_DIR)" ]; then mkdir $(MADT_LABS_SOCKETS_DIR); fi

install:
	@cp -r $(MADT_DIR)/madt_lib $(INSTALL_DIR)
	@cp -r $(MADT_DIR)/madt_ui $(INSTALL_DIR)
	@echo "MADT dir is $(MADT_DIR)"
	@cd madt_ui && python3 models.py && cd ../
	@if grep -q 'export MADT_LABS_DIR'  ~/.bashrc ; then sed -i 's@export MADT_LABS_DIR=.*@export MADT_LABS_DIR=$(MADT_LABS_DIR)@g'  ~/.bashrc; else echo "export MADT_LABS_DIR=$(MADT_LABS_DIR)" >> ~/.bashrc; fi
	@if grep -q 'export HOSTNAME' ~/.bashrc; then sed -i 's@export HOSTNAME=.*@export HOSTNAME=$(HOSTNAME)@g' ~/.bashrc; else echo "export HOSTNAME=$(HOSTNAME)" >> ~/.bashrc; fi
	@if grep -q 'export MADT_LABS_SOCKETS_DIR'  ~/.bashrc; then sed -i 's@export MADT_LABS_SOCKETS_DIR=.*@export MADT_LABS_SOCKETS_DIR=$(MADT_LABS_SOCKETS_DIR)@g' ~/.bashrc; else echo "export MADT_LABS_SOCKETS_DIR=$(MADT_LABS_SOCKETS_DIR)" >> ~/.bashrc; fi
	@echo "Successfully installed!"

clean:
	@if [ -d "madt_ui/static/scripts/" ]; then rm -rf madt_ui/static/scripts/; fi 
	@if [ -d "madt_ui/static/styles/" ]; then  rm -rf madt_ui/static/styles/; fi 
	@if [ -d "madt_ui/madt.sqlite" ]; then rm  madt_ui/madt.sqlite; fi 
