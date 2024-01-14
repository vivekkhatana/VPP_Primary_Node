# -*- coding: utf-8 -*-
"""
Created on Sun Mar  5 15:10:23 2023

@author: khata010
"""

# !/usr/bin/env python3

import os
import numpy as np
import struct
import socket
import sys
import time
from threading import Thread
import configparser
from RpiCluster.MainLogger import logger
from RpiCluster.PrimaryNodes.RpiPrimary import RpiPrimary
from RpiCluster.NodeConfig import NodeConfig



def start_primary():
    
    global dispatch_matrix
    global listen_latestInfo_port
    global listen_latestInfo_ip
    global opal_ip
    global opal_port
    global primary
    global NumNodes
    global Estar
    global droopCoeff
    global measVec
    global Qmeas
    global Vmeas

    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mastercluster_opal.txt'))
    
    NodeConfig.load(config)
    
    agentConfigFile = configparser.ConfigParser()
    agentConfigFile.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'agentConfig_10nodes_v2.txt'))
    
    
    socket_bind_ip = config.get("primary", "socket_bind_ip")
    socket_port = config.getint("primary", "socket_port")

    listen_latestInfo_ip = config.get("primary", "listen_opal_ip")
    listen_latestInfo_port = config.getint("primary", "listen_opal_port")
   
    opal_ip = config.get("opalrt", "opal_ip")
    opal_port = config.getint("opalrt", "opal_port")
    
    
    # add_file_logger("primary.log")
    
    # The RpiPrimary class handles all of the interesting bits of work that the primary performs
    primary = RpiPrimary(socket_bind_ip, socket_port, agentConfigFile) # socket_bind_ip and socket_port give the primary node address
                                                                        # and agentConfigFile sent to the secondary to make its neighbor connections
    
    # start the primary node and send the secondary nodes their configuration and neighbor information
    primary.start()
    primary.send_Nbr_info_to_secondary()
    
    solDim = 1;
    NumNodes = primary.number_of_secondary_nodes;
    dispatch_matrix = np.zeros(NumNodes);
    Estar = 240*np.sqrt(2)*np.ones(NumNodes);
    measVec = np.zeros(NumNodes);
    Qmeas = np.zeros(NumNodes);
    Vmeas = np.zeros(NumNodes);
    # droop coeff of the generators
    droopCoeff = 2e-4*np.ones(NumNodes);



def send_dispatch_to_OPAL(outVec):
    
    global opal_ip
    global opal_port
    
    #send via UDP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Use UDP sockets
    p = len(outVec) #determine how many floats we are sending\n",
    msgBytes = struct.pack('<{}'.format('f'*p),*outVec.tolist()) #bytepack numpy row vector - use little Endian format (required by Opal-RT)\n",
    REMOTE_HOST_ADDR = (opal_ip, opal_port)
    s.sendto(msgBytes, REMOTE_HOST_ADDR)
    logger.info("sent UDP packets to OPAL =" +str(outVec))
    # time.sleep(1)


def get_updates_from_secondary():  
    
    global dispatch_matrix
    global primary
    global NumNodes
    global measVec  
    global Qmeas
    global Vmeas
    
 
    toprint = np.zeros(NumNodes)
    
    while threadGo:    
        
        flag = 0
        
        dispatch_json = primary.get_sol_from_secondary()  
    
        
        for k in range(NumNodes):
            dummy = dispatch_json[k]
            node = dummy['nodeID']
            if np.isnan(dispatch_matrix[node]):
                flag = 0  
            else:   
                agentflag = str(dummy['convgFlag'])
                agentflag = agentflag.strip('.]').strip('.[')
                agentflag = float(agentflag)            
                flag = flag + agentflag                
                
        
        beta = 0
        gamma = 1
        
        
        # logger.info("flag = "+str(flag))
        if (flag == NumNodes):
            for k in range(NumNodes):
                dummy = dispatch_json[k]
                node = dummy['nodeID']                 
                dum = str(dummy['solution'])
                dum = dum.strip('.]').strip('.[')
                dum = float(dum)
                toprint[node] = dum
               
                dispatch_matrix[node] = dum + beta*Qmeas[node] - gamma*(Estar[node] - Vmeas[node]);       
               
            
            logger.info("cons_sol = " +str(toprint))
            send_dispatch_to_OPAL(dispatch_matrix)                                                    
            primary.send_stop_to_agents()
        time.sleep(0.1)
        
    
    
def receive_meas_OPAL():
    """
    Listen for measurements provided by the real-time simulated power system model
    Upon receipt of a measurement, send the latest info to the secondary nodes 
    """    
    global primary
    global NumNodes
    global measVec
    global Qmeas
    global Vmeas
       
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Use UDP sockets
    LOCAL_UDP_ADDR = (listen_latestInfo_ip, listen_latestInfo_port)
    s.bind(LOCAL_UDP_ADDR) #IP:Port here is for the computer running this script
    logger.info('Bound to ' + str(LOCAL_UDP_ADDR) + ' and waiting for UDP packet-based measurements')
    
    while threadGo:        
        
        data,addr = s.recvfrom(10000) #buffer size can be smaller if needed, but this works fine
        l = len(data)
        # p = int(l/4) # get number of floats sent: OPAL
        p = int(l/8) # get number of floats sent : Simulink
        
        # vector = np.array(struct.unpack('<{}'.format('f'*p),data)) # For OPAL RT
        vector = np.array(struct.unpack('<{}'.format('d'*p),data)) # For simulink simulations
        
        if len(vector) == 2*NumNodes:  
            
            a1 = 1
            a2 = 0
            
            Qmeas = vector[NumNodes:2*NumNodes]
            Vmeas = vector[0:NumNodes]
            
            measVec = a1*(Estar - vector[0:NumNodes]) + a2*vector[NumNodes:2*NumNodes].T;
            
            measVec = np.asarray(measVec)
            
            newVec = measVec
            newVec = np.array(newVec).tolist()
            # # logger.info("sending new updates to all secondaries= " +str(newVec))
            primary.send_latest_updated_info_secondary(newVec)  
            # time.sleep(10)


# main program begin...
if __name__ == "__main__":
    
    initSuccess = start_primary()
    
    threadGo = True #set to false to quit threads
    
    # start a new thread to receive messages from the secondary nodes                
    thread1 = Thread(target=get_updates_from_secondary)
    thread1.daemon = True
    thread1.start()
    
    # start a new thread to receive measurements from OPAL RT                    
    thread2 = Thread(target=receive_meas_OPAL)
    thread2.daemon = True
    thread2.start()
    
    
    ## do infinite while to keep main alive so that logging from threads shows in console
    try:
        while True:
            time.sleep(0.001)
    except KeyboardInterrupt:
        sys.exit()
        logger.info("cleaning up threads and exiting...")
        threadGo = False
        logger.info("done.")
