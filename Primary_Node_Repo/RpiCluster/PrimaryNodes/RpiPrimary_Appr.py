import socket
import numpy as np
import time
from threading import Thread
from RpiCluster.MainLogger import logger
from RpiCluster.RpiClusterClient import RpiClusterClient
from RpiCluster.ConnectionHandler import ConnectionHandler


class RpiPrimary:
    """Class to create a primary node which will handle connections coming in from a secondary

        This will form the basis of a general primary node which will be in charge of listening for connections
        and handling each one.

        Attributes:
            socket_bind_ip: IP address to bind the listening socket server to
            socket_port: Port number to bind the listening socket server to
            connected_clients: Dict of connected clients
    """

    def __init__(self, socket_bind_ip, socket_port, agentConfigFile): #, influxdb_host, influxdb_port, influxdb_database_prefix
        self.socket_bind_ip = socket_bind_ip
        self.socket_port = socket_port

        self.connected_clients = {}
        self.connected_client_addresses = {}
        self.connected_client_sockets = {}

        self.connected_nodeIDs = {}
        
        self.number_of_secondary_nodes = 12
        self.agentConfigFile = agentConfigFile


    def start(self):
        """Set up the primary to handle the various responsibilities"""
        logger.info("Starting primary...")



        # Start the handling of the secondary nodes
        listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening_socket.bind((self.socket_bind_ip, self.socket_port))

        
        listening_socket.listen(self.number_of_secondary_nodes)  # listen to "self.number_of_secondary_nodes" secondary node-connects

        ii = 0;

        while True:
            (clientsocket, address) = listening_socket.accept()
            logger.info("Got client at {address}".format(address=address))
            self.connected_nodeIDs[ii] = ii
            self.connected_client_addresses[ii] = address
            self.connected_client_sockets[ii] = clientsocket
            
            # agentSetup = self.agentConfigFile.get(str(self.connected_nodeIDs[ii]), "function")  # send objective function parameters to the secondary
            
            Thread(target=self.add_new_secondary, args=(ii,clientsocket, address, self.number_of_secondary_nodes)).start()
            # Thread(target=self.add_new_secondary, args=(ii,clientsocket, address, 6)).start()
        
            ii += 1
            
            if (ii == self.number_of_secondary_nodes):
                logger.info("Total secondary nodes connected to me = " +str(ii))
                break
         
        time.sleep(1)    
        self.send_Nbr_info_to_secondary()
        
    
    def add_new_secondary(self, index, clientsocket, address, networkDiam):
        rpi_client = RpiClusterClient(self, clientsocket, address, index, networkDiam) # create a channel for each secondary on your end
        self.connected_clients[rpi_client.nodeID] = rpi_client
        rpi_client.start() 
        logger.info("I connected to a new secondary node with ID", + "rpi_client.nodeID");
    

    def remove_client(self, rpi_client):
        """Removes a given client from the list of connected clients, typically called after disconnection"""
        del self.connected_clients[rpi_client.nodeID]

    
    def send_Nbr_info_to_secondary(self):
        """Allows sending info to every secondary connected to the primary"""
        # logger.info("sending nbr info to secondary nodes")
        for nodeID in self.connected_nodeIDs:
            myNbrslist = self.agentConfigFile.get(str(nodeID), "neighbors")
            # logger.info("nodeID =" + str(nodeID))
            # myNbrslist = [int(float(x)) for x in myNbrslist if x not in ['[', ',', ']']]
            numbers_str = myNbrslist[1:-1]  # Remove brackets
            number_strings = numbers_str.split(',')
            # Convert each string to a float
            myNbrslist = [int(float(x.strip())) for x in number_strings]
            # logger.info("myNbrslist = " +str(myNbrslist))
            # logger.info(self.connected_client_addresses)
            NbrAdds = [self.connected_client_addresses[key] for key in myNbrslist]
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            
            NbrInfo = {
                "NbrIDs": myNbrslist,
                "NbrAdds": NbrAdds,
            }
            # logger.info("NbrAdds = " +str(NbrAdds))
            # data = json.dumps({"type": 'NbrInfo', "payload": NbrAdds})
            myconnection_handler.send_message(NbrInfo, "NbrInfo")
            # logger.info("I sent this to the secondary")
        
        logger.info("sent neighbor info to all the secondary nodes")

  
    def get_secondary_details(self):
        """Allows retrieving some basic information of every secondary connected to the primary"""
        secondary_details = {}
        for nodeID in self.connected_nodeIDs:
            secondary_details[nodeID] = {
                "uuid": nodeID,
                "address": str(self.connected_clients[nodeID].address[0]) + ":" + str(self.connected_clients[nodeID].address[1]),
            }

        return secondary_details
    
    
    def get_sol_from_secondary(self):
        """Allows retrieving the solution of every secondary connected to the primary"""
        secondary_sols = {}
        for nodeID in self.connected_nodeIDs:
            secondary_sols[nodeID] = {
                "nodeID": nodeID,
                "avg_convgFlag": self.connected_clients[nodeID].avg_cons_conv_flag,
                "max_convgFlag": self.connected_clients[nodeID].max_cons_conv_flag,
                "max_init_convgFlag": self.connected_clients[nodeID].max_cons_init_conv_flag,
                "max_init_cons_Value": self.connected_clients[nodeID].max_cons_init_value,
                "avg_init_convgFlag": self.connected_clients[nodeID].avg_cons_init_conv_flag,
                "avg_init_num_cons_Value": self.connected_clients[nodeID].avg_cons_num_init_value,
                "avg_num_init_convgFlag": self.connected_clients[nodeID].avg_cons_num_init_conv_flag,
                "avg_init_den_cons_Value": self.connected_clients[nodeID].avg_cons_den_init_value,
                "avg_den_init_convgFlag": self.connected_clients[nodeID].avg_cons_den_init_conv_flag,
                "avg_init_cons_Value": self.connected_clients[nodeID].avg_cons_init_value,                
                "max_cons_Value": self.connected_clients[nodeID].max_cons_value,                
                "opt_completeFlag": self.connected_clients[nodeID].opt_complete_flag,
                "solution": self.connected_clients[nodeID].sol,
            } 
        return secondary_sols
   
    def send_latest_updated_info_secondary(self, latestInfo):
        """Allows sending info to every secondary connected to the primary"""
        
        for nodeID in self.connected_nodeIDs:
            mylatestparameters = latestInfo[nodeID]
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(mylatestparameters, "latest_parameters")            
        # logger.info("updated function parameters sent to all secondaries = " +str(latestInfo))
        
        
    def send_avg_cons_val_to_agents(self, avg_consensus_value):  
        for nodeID in self.connected_nodeIDs:
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(avg_consensus_value, "avg_consensus_value")            
        # logger.info("new avg consensus convgence value = " +str(avg_consensus_value))    
        
    def send_num_avg_cons_val_to_agents(self, num_avg_consensus_value):  
        for nodeID in self.connected_nodeIDs:
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(num_avg_consensus_value, "num_avg_consensus_value")            
        # logger.info("new avg consensus convgence value = " +str(avg_consensus_value))
        
    def send_den_avg_cons_val_to_agents(self, den_avg_consensus_value):  
        for nodeID in self.connected_nodeIDs:
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(den_avg_consensus_value, "den_avg_consensus_value")            
        # logger.info("new avg consensus convgence value = " +str(avg_consensus_value))     
             
    def send_avg_stop_to_agents(self):
        for nodeID in self.connected_nodeIDs:
            mystopflag = 1.0
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(mystopflag, "avg_cons_stop_flag")        
        # logger.info("sent stop communication for avg cons to all the agents")

    def send_max_stop_to_agents(self):
        for nodeID in self.connected_nodeIDs:
            mystopflag = 1.0
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(mystopflag, "max_cons_stop_flag")        
        # logger.info("sent stop communication for max cons to all the agents")
        
    def send_max_init_stop_to_agents(self):
        for nodeID in self.connected_nodeIDs:
            mystopflag = 1.0
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(mystopflag, "max_cons_init_stop_flag")        
        # logger.info("sent stop communication for max cons to all the agents")
        
    def send_avg_init_stop_to_agents(self):
        for nodeID in self.connected_nodeIDs:
            mystopflag = 1.0
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(mystopflag, "avg_cons_init_stop_flag")        
        # logger.info("sent stop communication for avg cons initialization to all the agents" +str(mystopflag))
        
    def send_num_avg_init_stop_to_agents(self):
        for nodeID in self.connected_nodeIDs:
            mystopflag = 1.0
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(mystopflag, "avg_num_cons_init_stop_flag")        
        # logger.info("sent stop communication for avg cons initialization to all the agents" +str(mystopflag))
        
    def send_den_avg_init_stop_to_agents(self):
        for nodeID in self.connected_nodeIDs:
            mystopflag = 1.0
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(mystopflag, "avg_den_cons_init_stop_flag")        
        # logger.info("sent stop communication for avg cons initialization to all the agents" +str(mystopflag))
        
        
    
    def send_opt_stop_to_agents(self):
        for nodeID in self.connected_nodeIDs:
            mystopflag = 1.0
            myconnection = self.connected_client_sockets[nodeID]
            myconnection_handler = ConnectionHandler(myconnection)
            myconnection_handler.send_message(mystopflag, "opt_complete_flag")        
        # logger.info("sent stop communication for max cons to all the agents")
        