# Pull Python Base Image
FROM arm32v7/python:3


# Define working directory
WORKDIR /app


# Copy the folder containg codes for the secondary node
#COPY Secondary_Node_Repo ./

COPY . /app


# Install dependencies
RUN sudo apt-get install python3-numpy 
RUN sudo apt-get install configparser 



# Define default command
CMD ["python3", "secondary_node_v2.py"]
