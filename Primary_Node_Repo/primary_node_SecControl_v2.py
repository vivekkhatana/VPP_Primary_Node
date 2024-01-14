# -*- coding: utf-8 -*-
"""
Created on Tue Dec 19 16:23:38 2023

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
from RpiCluster.PrimaryNodes.RpiPrimary_SecControl import RpiPrimary
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
    global oldmeasVec
    global Qmeas
    global Vmeas
    global avgConvFlag
    global avgInitConvFlag 
    global maxConvFlag
    global maxInitConvFlag 
    global OptConvFlag
    global beta
    global gamma
    global send_to_agents

    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mastercluster_opal_SecControl.txt'))
    
    NodeConfig.load(config)
    
    agentConfigFile = configparser.ConfigParser()
    agentConfigFile.read(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'agentConfig_SecControl.txt'))
    
    
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
    Estar = 480*np.sqrt(2/3)*np.ones(NumNodes);
    measVec = np.zeros(NumNodes);
    oldmeasVec = np.zeros(NumNodes);
    Qmeas = np.zeros(NumNodes);
    Vmeas = np.zeros(NumNodes);
    # droop coeff of the generators
    droopCoeff = np.array([0.000391918,	0.000195959, 0.000130639, 0.000391918, 0.000195959, 0.000130639, 0.000391918, 0.000195959,0.000130639,0.000391918,0.000195959, 0.000130639, 0.000391918, 0.000195959, 0.000130639]);
    # droopCoeff = np.array([0.000391918,	0.000195959, 0.000130639]);
    avgConvFlag = 0;
    avgInitConvFlag = 0
    maxConvFlag = 0;
    maxInitConvFlag = 0
    OptConvFlag = 0
    send_to_agents = 0
    
    beta = np.array([np.zeros(NumNodes)])
    gamma = np.array([np.zeros(NumNodes)])


def determine_conv_of_secondary():
    
    global primary
    global NumNodes 
    global avgConvFlag 
    global maxConvFlag
    global avgInitConvFlag
    global maxInitConvFlag 
    global OptConvFlag 
    global send_to_agents
        
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
                # max_flag = 0
                # max_init_flag = 0
                opt_conv_flag = 0 
            else:   
                avg_agentflag = str(dummy['avg_convgFlag'])
                avg_agentflag = avg_agentflag.strip('.]').strip('.[')
                avg_agentflag = float(avg_agentflag)
                avg_flag = avg_flag + avg_agentflag
                
                # max_agentflag = str(dummy['max_convgFlag'])
                # max_agentflag = max_agentflag.strip('.]').strip('.[')
                # max_agentflag = float(max_agentflag)
                # max_flag = max_flag + max_agentflag
                
                # max_init_agentflag = str(dummy['max_init_convgFlag'])
                # max_init_agentflag = max_init_agentflag.strip('.]').strip('.[')
                # max_init_agentflag = float(max_init_agentflag)
                # max_init_flag = max_init_flag + max_init_agentflag
                
                opt_conv_agentflag = str(dummy['opt_completeFlag'])
                opt_conv_agentflag = opt_conv_agentflag.strip('.]').strip('.[')
                opt_conv_agentflag = float(opt_conv_agentflag)
                opt_conv_flag = opt_conv_flag + opt_conv_agentflag
                            
        if (avg_flag == NumNodes):
            avgConvFlag = 1
            primary.send_avg_stop_to_agents()
         
            
        if (opt_conv_flag == NumNodes):
            OptConvFlag = 1
            primary.send_opt_stop_to_agents()
        # else:
        #     send_to_agents = 0

        time.sleep(0.01)   # slow sampling checks are more robust


def max_cons_for_secondary():
    
    # global primary
    # global NumNodes  
    # global maxInitConvFlag 
        
    while threadGo:    
        
        # max_flag = 0
        max_init_flag = 0

        # dispatch_json = primary.get_sol_from_secondary()  
        
        # # logger.info("dispatch_json = " +str(dispatch_json))     
    
        # for k in range(NumNodes):
        #     dummy = dispatch_json[k]
        #     value_check = float(dummy['max_init_convgFlag']) 
        #     if np.isnan(value_check):
        #         max_flag = 0
        #         max_init_flag = 0
        #     else:   
        #         max_agentflag = str(dummy['max_convgFlag'])
        #         max_agentflag = max_agentflag.strip('.]').strip('.[')
        #         max_agentflag = float(max_agentflag)
        #         max_flag = max_flag + max_agentflag
                
        #         max_init_agentflag = str(dummy['max_init_convgFlag'])
        #         max_init_agentflag = max_init_agentflag.strip('.]').strip('.[')
        #         max_init_agentflag = float(max_init_agentflag)
        #         max_init_flag = max_init_flag + max_init_agentflag 
            
        # max_cons_vec_init_nodes = np.zeros(NumNodes)
        
        # if (max_init_flag == NumNodes):
        #     maxInitConvFlag = 1            
            
        #     for k in range(NumNodes):
        #         dummy = dispatch_json[k]   
        #         max_init_value_rec_val = str(dummy['max_init_cons_Value'])
        #         max_init_value_rec_val = max_init_value_rec_val.strip('.]').strip('.[')
        #         max_init_value_rec_val = float(max_init_value_rec_val)
        #         max_cons_vec_init_nodes[k] = max_init_value_rec_val

        #     primary.send_max_init_stop_to_agents()
        #     max_cons_init = primary.max_cons_init(max_cons_vec_init_nodes)
        #     max_among_all_nodes = max(max_cons_init)
        #     primary.send_max_cons_val_to_agents(max_among_all_nodes)
    

def avg_cons_for_secondary():
    
    global primary
    global NumNodes  
    global avgInitConvFlag
        
    while threadGo:    
    
        avg_init_flag = 0

        dispatch_json = primary.get_sol_from_secondary()  
        
        # logger.info("dispatch_json = " +str(dispatch_json))     
    
        for k in range(NumNodes):
            dummy = dispatch_json[k]
            value_check = float(dummy['avg_init_convgFlag']) 
            if np.isnan(value_check):
                avg_init_flag = 0
            else:   
                avg_init_agentflag = str(dummy['avg_init_convgFlag'])
                avg_init_agentflag = avg_init_agentflag.strip('.]').strip('.[')
                avg_init_agentflag = float(avg_init_agentflag)
                avg_init_flag = avg_init_flag + avg_init_agentflag 
            
        avg_cons_vec_init_nodes = np.zeros(NumNodes)
        
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


def get_updates_from_secondary():  
    
    global dispatch_matrix
    global primary
    global NumNodes
    global measVec  
    global Qmeas
    global Vmeas
    global OptConvFlag    
    global beta
    global gamma
    global send_to_agents
    global maxInitConvFlag 
    global avgInitConvFlag
    
    # toprint = np.zeros(NumNodes)
    
    while threadGo:  
        
        max_flag = 0
        max_init_flag = 0

        dispatch_json = primary.get_sol_from_secondary()  
        
        # logger.info("dispatch_json = " +str(dispatch_json))     
    
        for k in range(NumNodes):
            dummy = dispatch_json[k]
            value_check = float(dummy['max_init_convgFlag']) 
            if np.isnan(value_check):
                max_flag = 0
                max_init_flag = 0
            else:   
                max_agentflag = str(dummy['max_convgFlag'])
                max_agentflag = max_agentflag.strip('.]').strip('.[')
                max_agentflag = float(max_agentflag)
                max_flag = max_flag + max_agentflag
                
                max_init_agentflag = str(dummy['max_init_convgFlag'])
                max_init_agentflag = max_init_agentflag.strip('.]').strip('.[')
                max_init_agentflag = float(max_init_agentflag)
                max_init_flag = max_init_flag + max_init_agentflag 
            
        max_cons_vec_init_nodes = np.zeros(NumNodes)
        
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
        
        
        
        avg_init_flag = 0

        # dispatch_json = primary.get_sol_from_secondary()  
        
        # logger.info("dispatch_json = " +str(dispatch_json))     
    
        for k in range(NumNodes):
            dummy = dispatch_json[k]
            value_check = float(dummy['avg_init_convgFlag']) 
            if np.isnan(value_check):
                avg_init_flag = 0
            else:   
                avg_init_agentflag = str(dummy['avg_init_convgFlag'])
                avg_init_agentflag = avg_init_agentflag.strip('.]').strip('.[')
                avg_init_agentflag = float(avg_init_agentflag)
                avg_init_flag = avg_init_flag + avg_init_agentflag 
            
        avg_cons_vec_init_nodes = np.zeros(NumNodes)
        
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
        
        
        
        
        # dispatch_json = primary.get_sol_from_secondary()
        beta_vec = beta.squeeze()
        gamma_vec = gamma.squeeze()
        
        Qmeas_vec = Qmeas.squeeze()
        Vmeas_vec = Vmeas.squeeze()
        Estar_vec = np.array(Estar)    
         
        dummy_dispatch = np.zeros(NumNodes)

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

                if (Epsilon_val < 1):
                    correction_fac2 = (Estar_vec - Vmeas_vec) 
                    logger.info("Epsilon_val = " +str(Epsilon_val))
                    logger.info("dummy_dispatch = " +str(dummy_dispatch))
                    logger.info("correction_fac2 = " +str(correction_fac2))

                    for k in range(NumNodes):                    
                        # logger.info("Qmeas_vec[node] =" +str(Qmeas_vec[node]))
                        # logger.info("droopCoeff[node] =" +str(droopCoeff[node]))
                        # correction_fac1 = beta_vec[k]*(droopCoeff[k]*Qmeas_vec[k])
                        # correction_fac2 = gamma_vec[k]*(Estar_vec[k] - Vmeas_vec[k]) 
        
                        # correction_fac = correction_fac1 - correction_fac2
                        dispatch_matrix[k] = dummy_dispatch[k] - correction_fac2[k]  
                    
                    send_dispatch_to_OPAL(dispatch_matrix)  
                    

def send_dispatch_to_OPAL(outVec):
    
    global opal_ip
    global opal_port
    global OptConvFlag
    
    #send via UDP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Use UDP sockets
    p = len(outVec) #determine how many floats we are sending\n",
    msgBytes = struct.pack('<{}'.format('f'*p),*outVec.tolist()) #bytepack numpy row vector - use little Endian format (required by Opal-RT)\n",
    REMOTE_HOST_ADDR = (opal_ip, opal_port)
    s.sendto(msgBytes, REMOTE_HOST_ADDR)
    logger.info("sent UDP packets to OPAL =" +str(outVec))
    OptConvFlag = 0
    # time.sleep(1)

    
def receive_meas_OPAL():
    """
    Listen for measurements provided by the real-time simulated power system model
    Upon receipt of a measurement, send the latest info to the secondary nodes 
    """    
    global primary
    global NumNodes
    global measVec
    global oldmeasVec
    global Qmeas
    global Vmeas
    global beta
    global gamma
    global send_to_agents
       
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Use UDP sockets
    LOCAL_UDP_ADDR = (listen_latestInfo_ip, listen_latestInfo_port)
    s.bind(LOCAL_UDP_ADDR) #IP:Port here is for the computer running this script
    logger.info('Bound to ' + str(LOCAL_UDP_ADDR) + ' and waiting for UDP packet-based measurements')
    
    while threadGo:        
        
        data,addr = s.recvfrom(1000) #buffer size can be smaller if needed, but this works fine
        l = len(data)
        p = int(l/4) # get number of floats sent: OPAL
        # p = int(l/8) # get number of floats sent : Simulink

        vector = np.array(struct.unpack('<{}'.format('f'*p),data)) # For OPAL RT
        # vector = np.array(struct.unpack('<{}'.format('d'*p),data)) # For simulink simulations
        # logger.info("vector = " +str(vector[0]))

        if len(vector) == 2*NumNodes:  
            
            measvec_diff = np.abs(vector[0:NumNodes] - oldmeasVec)

            Qmeas = np.array([vector[0:NumNodes]])
            Vmeas = np.array([vector[NumNodes:2*NumNodes]])
                        
            # beta = 0; gamma = 1; a1 = 1; a2 = 1; # reactive power sharing
            # beta = 1; gamma = 0; a1 = 0; a2 = 0; # voltage regulation
            
            a1 = np.array([np.ones(NumNodes)])
            a2 = np.array([np.ones(NumNodes)])
            
            beta = np.array([np.zeros(NumNodes)])
            gamma = np.array([np.ones(NumNodes)])
            
            # droopCoeff = np.array([np.array([0.000391918,	0.000195959, 0.000130639])]);
            droopCoeff = np.array([np.array([0.000391918,	0.000195959, 0.000130639, 0.000391918, 0.000195959, 0.000130639, 0.000391918, 0.000195959,0.000130639,0.000391918,0.000195959, 0.000130639, 0.000391918, 0.000195959, 0.000130639])]);
            
            measVec = np.concatenate((Vmeas.T, Qmeas.T), axis=1)            
            measVec = np.concatenate((measVec, a1.T), axis=1)
            measVec = np.concatenate((measVec, a2.T), axis=1)
            measVec = np.concatenate((measVec, beta.T), axis=1)
            measVec = np.concatenate((measVec, gamma.T), axis=1)
            measVec = np.concatenate((measVec, droopCoeff.T), axis=1)

            measVec = np.asarray(measVec)
            
            to_display = np.concatenate((Vmeas.T, Qmeas.T), axis=1)
            
            newVec = measVec
            newVec = np.array(newVec).tolist()
            # logger.info("latest measurements= " +str(to_display))
            # logger.info("vector = " +str(vector))
            primary.send_latest_updated_info_secondary(newVec)  
            oldmeasVec = vector[0:NumNodes]
            # time.sleep(1)


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
    
    # start a new thread to receive measurements from OPAL RT                    
    # thread4 = Thread(target=max_cons_for_secondary)
    # thread4.daemon = True
    # thread4.start()
    
    # start a new thread to receive measurements from OPAL RT                    
    # thread5 = Thread(target=avg_cons_for_secondary)
    # thread5.daemon = True
    # thread5.start()
    
    ## do infinite while to keep main alive so that logging from threads shows in console
    try:
        while True:
            time.sleep(0.001)
    except KeyboardInterrupt:
        sys.exit()
        logger.info("cleaning up threads and exiting...")
        threadGo = False
        logger.info("done.")
