#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading,queue
import logging, logging.config
from .DDModbus import DDModbus
import time,datetime,pytz
from enum import IntEnum
from .Diematic import Diematic, DDREGISTER

#This class allows to read data from Diematic Delta regulator with the help of a RS485/TCPIP converter
#This is a read only version (no support to update boiler settings)
class DiematicDeltaPanel(Diematic):
	def __init__(self,ip,port,regulatorAddress,interfaceAddress,boilerTimezone='',syncTime=False):
		
		super().__init__(ip,port,0,interfaceAddress,boilerTimezone,syncTime)
  


#modbus loop, shall run in a specific thread. Allow to exchange register values with the Dielatic regulator
	def loop(self):
		#parameter validity duration in seconds after expiration of period
		#after this timeout, interface is reset
		VALIDITY_TIME=30
		try:
			self.run=True;
			#reset timeout
			self.lastSynchroTimestamp=time.time();
			#initialize the register table with -1 - avoid crashes if registers are expected by the Diematic class but not supported dy the Delta Panel implementation
			indexes = list(range(1,737));
			self.registers = dict.fromkeys(indexes, -1);
			while self.run:
				#wait for a frame to be received
				frame=self.modBusInterface.slaveRx(self.interfaceAddress);
				
				#if a frame has been received
				if (frame):
					if ((frame.valid) and (frame.modbusAddress==self.interfaceAddress) and (frame.modbusFunctionCode==DDModbus.WRITE_MULTIPLE_REGISTERS)):
						self.logger.debug('A Diematic Delta valid frame has been received');
						self.logger.debug('Register data :'+ str(frame.data))

						#reset timeout
						self.lastSynchroTimestamp=time.time();

						#update the register table with the values just received
						self.registers.update(frame.data)
						
						#refresh regulator attribute
						self.refreshAttributes();
					
			self.logger.critical('Modbus Thread stopped');
		except BaseException as exc:		
			self.logger.exception(exc)
