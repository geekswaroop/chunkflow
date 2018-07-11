ARG BACKEND=pznet

FROM jingpengw/chunkflow:backend-${BACKEND}


LABEL maintainer = "Jingpeng Wu" \
    email = "jingpeng@princeton.edu"

WORKDIR /root 
RUN mkdir chunkflow
ADD . chunkflow/ 

RUN git clone https://github.com/seung-lab/emirt.git 
ENV PYTHONPATH /root:$PATHONPATH
ENV PYTHONPATH /opt/znnphi_interface/code/znet/src/python:$PYTHONPATH
ENV PYTHONPATH /root/chunkflow/python:$PYTHONPATH

WORKDIR ./chunkflow 

RUN pip3 install --upgrade pip
RUN pip3 install --upgrade setuptools
RUN pip3 install -r requirements.txt 

ENV PYTHONPATH /root/chunkflow/python:$PYTHONPATH 
