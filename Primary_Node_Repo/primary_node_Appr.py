# -*- coding: utf-8 -*-
"""
Created on Tue Nov  7 18:31:29 2023

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
from RpiCluster.PrimaryNodes.RpiPrimary_Appr import RpiPrimary
from RpiCluster.NodeConfig import NodeConfig



def start_primary():
    
    global dispatch_matrix
    global solution
    global listen_latestInfo_port
    global listen_latestInfo_ip
    global opal_ip
    global opal_port
    global primary
    global NumNodes
    global rhoD
    global PI_max
    global PI_min
    global avgConvFlag
    global OptConvFlag

    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mastercluster_opal_Appr.txt'))
    
    NodeConfig.load(config)
    
    agentConfigFile = configparser.ConfigParser()
    agentConfigFile.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'agentConfig_Appr.txt'))
    
    
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
    solution = np.zeros(NumNodes);
    rhoD = np.zeros(NumNodes);
    PI_max = np.array([100000,25000,25000,25000,25000,100000,200000,300000,25000,25000,25000,25000]);
    # PI_max = np.array([100000,25000,25000,25000,25000,100000,200000,300000]);
    PI_min = np.zeros(NumNodes);
    avgConvFlag = 0;
    OptConvFlag = 0
    


def send_dispatch_to_OPAL(outVec):
    
    global opal_ip
    global opal_port
    
    #send via UDP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Use UDP sockets
    p = len(outVec) #determine how many floats we are sending\n",
    msgBytes = struct.pack('<{}'.format('f'*p),*outVec.tolist()) #bytepack numpy row vector - use little Endian format (required by Opal-RT)\n",
    REMOTE_HOST_ADDR = (opal_ip, opal_port)
    s.sendto(msgBytes, REMOTE_HOST_ADDR)
    logger.info("sent UDP packets to OPAL =" +str(sum(outVec)))
    # time.sleep(1)


def determine_conv_of_secondary():
    
    global primary
    global NumNodes 
    global avgConvFlag 
    global OptConvFlag 
        
    while threadGo:    
        
        avg_flag = 0
        opt_conv_flag = 0 
        
        
        dispatch_json = primary.get_sol_from_secondary()  
        
        # logger.info("dispatch_json = " +str(dispatch_json))     
    
        for k in range(NumNodes):
            dummy = dispatch_json[k]
            flag_check = float(dummy['avg_convgFlag'])
            if np.isnan(flag_check):
                avg_flag = 0
                opt_conv_flag = 0 
            else:   
                avg_agentflag = str(dummy['avg_convgFlag'])
                avg_agentflag = avg_agentflag.strip('.]').strip('.[')
                avg_agentflag = float(avg_agentflag)
                avg_flag = avg_flag + avg_agentflag

                opt_conv_agentflag = str(dummy['opt_completeFlag'])
                opt_conv_agentflag = opt_conv_agentflag.strip('.]').strip('.[')
                opt_conv_agentflag = float(opt_conv_agentflag)
                opt_conv_flag = opt_conv_flag + opt_conv_agentflag       
                            
        if (avg_flag == NumNodes):
            avgConvFlag = 1
            # logger.info("avg_flag =" +str(avg_flag)) 
            primary.send_avg_stop_to_agents()
        else:
            if (avg_flag >= 1):
                conv_percentage = (avg_flag/NumNodes)*100
                logger.info("avg_flag =" +str(conv_percentage))
            avgConvFlag = 0
            
        if (opt_conv_flag == NumNodes):
            OptConvFlag = 1
            primary.send_opt_stop_to_agents()  
            OptConvFlag = 0
        
        time.sleep(0.1)    # slow sampling checks are more robust

def get_updates_from_secondary():  
    
    global dispatch_matrix
    global solution
    global primary
    global NumNodes
    global PI_max
    global PI_min
    global OptConvFlag    
    
    # toprint = np.zeros(NumNodes)
    
    while threadGo:  
        
        dispatch_json = primary.get_sol_from_secondary()
        
        PI_max_vec = PI_max.squeeze()
        PI_min_vec = PI_min.squeeze()     
        
        if (OptConvFlag == 1):
            # logger.info("dispatch_json =" +str(dispatch_json))
            for k in range(NumNodes):
                dummy = dispatch_json[k]
                node = dummy['nodeID']                 
                dum = str(dummy['solution'])
                dum = dum.strip('.]').strip('.[')
                dum = float(dum)
                # toprint[node] = dum
                
                dispatch_matrix[node] = 1000*( PI_min_vec[node] + np.array(dum)*(PI_max_vec[node] - PI_min_vec[node]) )
                solution[node] = np.array(dum)
               
            # logger.info("cons_sol = " +str(solution))
            send_dispatch_to_OPAL(dispatch_matrix)  
            OptConvFlag = 0                                                  
        time.sleep(0.1)

    
def receive_meas_OPAL():
    """
    Listen for measurements provided by the real-time simulated power system model
    Upon receipt of a measurement, send the latest info to the secondary nodes 
    """    
    global primary
    global NumNodes
    global rhoD
    global PI_max
    global PI_min
       
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
        
        if len(vector) == 1:  
            
            rhoD = vector/1000
            # rhoD = rhoD/(primary.number_of_secondary_nodes)
            dummy_vec =  np.zeros(NumNodes - 1)
            measVec = np.concatenate((rhoD, dummy_vec.T), axis=0)
            measVec = np.array([measVec])
            # measVec = np.array([np.array([float(rhoD), 23, 38], dtype=object)], dtype=object)
            # measVec = rhoD*np.array([np.ones(NumNodes)])
            # PI_max = 0.001*np.array([np.array([100000,25000,25000])]);
            PI_max = 0.001*np.array([np.array([100000,25000,25000,25000,25000,100000,200000,300000,25000,25000,25000,25000])]);
            # PI_max = 0.001*np.array([np.array([100000,25000,25000,25000,25000,100000,200000,300000])]);
            PI_min = np.array([np.zeros(NumNodes)]);

            measVec = np.concatenate((measVec.T, PI_max.T), axis=1)            
            measVec = np.concatenate((measVec, PI_min.T), axis=1)            
            
            # measVec = a1*(Estar - vector[0:NumNodes]) + a2*vector[NumNodes:2*NumNodes].T;
            
            measVec = np.asarray(measVec)
            
            newVec = measVec
            # logger.info("sending new updates to all secondaries= " +str(newVec))
            newVec = np.array(newVec).tolist()
            
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
    
    # start a new thread to receive measurements from OPAL RT                    
    thread3 = Thread(target=determine_conv_of_secondary)
    thread3.daemon = True
    thread3.start()
    
    
    ## do infinite while to keep main alive so that logging from threads shows in console
    try:
        while True:
            time.sleep(0.001)
    except KeyboardInterrupt:
        sys.exit()
        logger.info("cleaning up threads and exiting...")
        threadGo = False
        logger.info("done.")
