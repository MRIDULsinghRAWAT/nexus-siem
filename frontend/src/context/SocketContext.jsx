// Global WebSocket connection context and state provider
import React, { createContext, useContext } from 'react';
import { io } from 'socket.io-client';

const socket = io("http://127.0.0.1:5000");
const SocketContext = createContext();

export const useSocket = () => useContext(SocketContext);

export const SocketProvider = ({ children }) => {
  return (
    <SocketContext.Provider value={socket}>
      {children}
    </SocketContext.Provider>
  );
};