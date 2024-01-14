# -*- coding: utf-8 -*-
"""
Created on Thu Jan 11 13:44:36 2024

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
    global oldSetpointVec
    global rhoD
    global PI_max
    global PI_min
    global avgConvFlag
    global avgInitConvFlag 
    global NumavgInitConvFlag
    global DenavgInitConvFlag
    global maxConvFlag
    global maxInitConvFlag 
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
    oldSetpointVec = 10*np.ones(NumNodes);
    PI_max = np.array([100000,25000,25000,25000,25000,100000,200000,300000,25000,25000,25000,25000]);
    # PI_max = np.array([100000,25000,25000]);
    PI_min = np.zeros(NumNodes);
    avgConvFlag = 0;
    avgInitConvFlag = 0
    NumavgInitConvFlag = 0
    DenavgInitConvFlag = 0
    maxConvFlag = 0;
    maxInitConvFlag = 0
    OptConvFlag = 0
    

def get_updates_from_secondary():  
    
    global dispatch_matrix
    global primary
    global NumNodes
    global PI_max
    global PI_min
    global oldSetpointVec
    global maxInitConvFlag 
    global avgInitConvFlag
    global NumavgInitConvFlag
    global DenavgInitConvFlag
    global OptConvFlag
    global avgConvFlag   

    
    while threadGo:  
        
        max_flag = 0
        max_init_flag = 0
        avg_init_flag = 0
        num_avg_init_flag = 0
        den_avg_init_flag = 0
        avg_flag = 0
        opt_conv_flag = 0 

        max_cons_vec_init_nodes = np.zeros(NumNodes)     
        avg_cons_vec_init_nodes = np.zeros(NumNodes)
        num_avg_cons_vec_init_nodes = np.zeros(NumNodes)
        den_avg_cons_vec_init_nodes = np.zeros(NumNodes)
         
        dummy_dispatch = np.zeros(NumNodes)
        
        PI_max_vec = PI_max.squeeze()
        PI_min_vec = PI_min.squeeze()
        
        dispatch_json = primary.get_sol_from_secondary()
        
        # logger.info("dispatch_json = " +str(dispatch_json))     
    
        for k in range(NumNodes):
            dummy = dispatch_json[k]
            value_check = float(dummy['avg_init_convgFlag']) 
            if np.isnan(value_check):
                max_flag = 0
                max_init_flag = 0
                avg_init_flag = 0
                num_avg_init_flag = 0
                den_avg_init_flag = 0
                avg_flag = 0
                opt_conv_flag = 0 
            else:   
                max_agentflag = str(dummy['max_convgFlag'])
                max_agentflag = max_agentflag.strip('.]').strip('.[')
                max_agentflag = float(max_agentflag)
                max_flag = max_flag + max_agentflag
                
                max_init_agentflag = str(dummy['max_init_convgFlag'])
                max_init_agentflag = max_init_agentflag.strip('.]').strip('.[')
                max_init_agentflag = float(max_init_agentflag)
                max_init_flag = max_init_flag + max_init_agentflag 
                
                num_avg_init_agentflag = str(dummy['avg_num_init_convgFlag'])
                num_avg_init_agentflag = num_avg_init_agentflag.strip('.]').strip('.[')
                num_avg_init_agentflag = float(num_avg_init_agentflag)
                num_avg_init_flag = num_avg_init_flag + num_avg_init_agentflag 
                
                den_avg_init_agentflag = str(dummy['avg_den_init_convgFlag'])
                den_avg_init_agentflag = den_avg_init_agentflag.strip('.]').strip('.[')
                den_avg_init_agentflag = float(den_avg_init_agentflag)
                den_avg_init_flag = den_avg_init_flag + den_avg_init_agentflag 
                
                avg_init_agentflag = str(dummy['avg_init_convgFlag'])
                avg_init_agentflag = avg_init_agentflag.strip('.]').strip('.[')
                avg_init_agentflag = float(avg_init_agentflag)
                avg_init_flag = avg_init_flag + avg_init_agentflag 
                
                avg_agentflag = str(dummy['avg_convgFlag'])
                avg_agentflag = avg_agentflag.strip('.]').strip('.[')
                avg_agentflag = float(avg_agentflag)
                avg_flag = avg_flag + avg_agentflag

                opt_conv_agentflag = str(dummy['opt_completeFlag'])
                opt_conv_agentflag = opt_conv_agentflag.strip('.]').strip('.[')
                opt_conv_agentflag = float(opt_conv_agentflag)
                opt_conv_flag = opt_conv_flag + opt_conv_agentflag

        
        if (max_init_flag == NumNodes):
            maxInitConvFlag = 1            
            
            for k in range(NumNodes):
                dummy = dispatch_json[k]   
                max_init_value_rec_val = str(dummy['max_init_cons_Value'])
                max_init_value_rec_val = max_init_value_rec_val.strip('.]').strip('.[')
                max_init_value_rec_val = float(max_init_value_rec_val)
                max_cons_vec_init_nodes[k] = max_init_value_rec_val

            primary.send_max_init_stop_to_agents()
            max_cons_init = primary.max_cons_init(max_cons_vec_init_nodes)
            max_among_all_nodes = max(max_cons_init)
            primary.send_max_cons_val_to_agents(max_among_all_nodes)   

        
        if (num_avg_init_flag == NumNodes):
            NumavgInitConvFlag = 1            
            
            for k in range(NumNodes):
                dummy = dispatch_json[k]   
                num_avg_init_value_rec_val = str(dummy['avg_init_num_cons_Value'])
                num_avg_init_value_rec_val = num_avg_init_value_rec_val.strip('.]').strip('.[')
                num_avg_init_value_rec_val = float(num_avg_init_value_rec_val)
                num_avg_cons_vec_init_nodes[k] = num_avg_init_value_rec_val

            primary.send_num_avg_init_stop_to_agents()
            num_avg_of_all_nodes = np.sum(num_avg_cons_vec_init_nodes)/NumNodes
            # logger.info("avg_of_all_nodes = " +str(avg_of_all_nodes))     
            primary.send_num_avg_cons_val_to_agents(num_avg_of_all_nodes)
            
        if (den_avg_init_flag == NumNodes):
            DenavgInitConvFlag = 1            
            
            for k in range(NumNodes):
                dummy = dispatch_json[k]   
                den_avg_init_value_rec_val = str(dummy['avg_init_den_cons_Value'])
                den_avg_init_value_rec_val = den_avg_init_value_rec_val.strip('.]').strip('.[')
                den_avg_init_value_rec_val = float(den_avg_init_value_rec_val)
                den_avg_cons_vec_init_nodes[k] = den_avg_init_value_rec_val

            primary.send_den_avg_init_stop_to_agents()
            den_avg_of_all_nodes = np.sum(den_avg_cons_vec_init_nodes)/NumNodes
            # logger.info("avg_of_all_nodes = " +str(avg_of_all_nodes))     
            primary.send_den_avg_cons_val_to_agents(den_avg_of_all_nodes)
            
        if (avg_init_flag == NumNodes):
            avgInitConvFlag = 1            
            
            for k in range(NumNodes):
                dummy = dispatch_json[k]   
                avg_init_value_rec_val = str(dummy['avg_init_cons_Value'])
                avg_init_value_rec_val = avg_init_value_rec_val.strip('.]').strip('.[')
                avg_init_value_rec_val = float(avg_init_value_rec_val)
                avg_cons_vec_init_nodes[k] = avg_init_value_rec_val

            primary.send_avg_init_stop_to_agents()
            avg_of_all_nodes = np.sum(avg_cons_vec_init_nodes)/NumNodes
            # logger.info("avg_of_all_nodes = " +str(avg_of_all_nodes))     
            primary.send_avg_cons_val_to_agents(avg_of_all_nodes)
            
            
        if (avg_flag == NumNodes):
            avgConvFlag = 1
            primary.send_avg_stop_to_agents()
         
            
        if (opt_conv_flag == NumNodes):
            OptConvFlag = 1
            primary.send_opt_stop_to_agents()
 
        if (OptConvFlag == 1):
            
            for k in range(NumNodes):
                dummy = dispatch_json[k]
                node = dummy['nodeID']                 
                dum = str(dummy['solution'])
                dum = dum.strip('.]').strip('.[')
                dum = float(dum)
                
                dummy_dispatch[node] = np.array(dum)
                
            if (dummy_dispatch.all() == True):  
                
                Epsilon_val = np.max(dummy_dispatch) - np.min(dummy_dispatch)
                # logger.info("Epsilon_val_1 = " +str(Epsilon_val))

                if (Epsilon_val < 0.01):
                    
                    setpt_diff = dummy_dispatch - oldSetpointVec
 
                    # logger.info("Epsilon_val = " +str(Epsilon_val))
                    # logger.info("dummy_dispatch = " +str(dummy_dispatch))
                    
                    if (np.sum(np.abs(setpt_diff)) > 0.25*np.max(oldSetpointVec) ):

                        for k in range(NumNodes):                    
                            dispatch_matrix[k] = 1000*( PI_min_vec[k] + dummy_dispatch[k]*(PI_max_vec[k] - PI_min_vec[k]) ) 
                        
                        oldSetpointVec = dummy_dispatch
                        send_dispatch_to_OPAL(dispatch_matrix)
                    else:
                        pass
                elif (Epsilon_val > 0.01) and (Epsilon_val < 1):
                    
                    adjusted_dummy_dispatch = np.sum(dummy_dispatch)/NumNodes
                    
                    setpt_diff = adjusted_dummy_dispatch*np.ones(NumNodes) - oldSetpointVec
                    
                    # logger.info("setpt_diff = " +str(setpt_diff))
                    
                    if (np.sum(np.abs(setpt_diff)) > 0.25*np.max(oldSetpointVec) ):

                        # logger.info("Epsilon_val = " +str(Epsilon_val))
                        # logger.info("Epsilon_val is high sending adjusted setpoints =" +str(adjusted_dummy_dispatch))
    
                        for k in range(NumNodes):                    
                            dispatch_matrix[k] = 1000*( PI_min_vec[k] + adjusted_dummy_dispatch*(PI_max_vec[k] - PI_min_vec[k]) ) 
                        
                        oldSetpointVec = adjusted_dummy_dispatch*np.ones(NumNodes)
                        send_dispatch_to_OPAL(dispatch_matrix)
                    else:
                        pass
                    
        
        # time.sleep(1) 
        

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
    logger.info("sum of the sent UDP packets to OPAL =" +str(sum(outVec)))
    # time.sleep(1)        
        
   
    
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
        p = int(l/4) # get number of floats sent: OPAL
        # p = int(l/8) # get number of floats sent : Simulink
        
        vector = np.array(struct.unpack('<{}'.format('f'*p),data)) # For OPAL RT
        # vector = np.array(struct.unpack('<{}'.format('d'*p),data)) # For simulink simulations
        
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
       
    # start a new thread to receive measurements from OPAL RT                    
    thread1 = Thread(target=receive_meas_OPAL)
    thread1.daemon = True
    thread1.start()
    
    
    # start a new thread to receive messages from the secondary nodes                
    thread2 = Thread(target=get_updates_from_secondary)
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
