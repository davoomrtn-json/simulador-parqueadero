#!/bin/bash

echo "Iniciando VNC..."
vncserver :1

sleep 3

echo "Iniciando noVNC..."
websockify --web=/usr/share/novnc/ 6080 localhost:5901 > /tmp/novnc.log 2>&1 &

sleep 3

echo "Iniciando simulador..."
export DISPLAY=:1
python3 "Proyecto final.py"
