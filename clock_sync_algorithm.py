"""
Author       : Li Qingbing(3263109808@qq.com)
Version      : V0.0
Date         : 2024-11-04 13:50:22
Description  : 
"""

from abc import ABC, abstractmethod
import socket
import time


class ClockSyncAlgorithm(ABC):
    def __init__(self):
        # cumulated time offset, simulating time elapse in system.
        self.cumulative_offset = 0.0
        self.cumulative_offset_server = 0.0

    @abstractmethod
    def server_process(self, name, sock: socket.socket, num_client: int = 3) -> None:
        """
        Server processing logic for the algorithm.
        :param name: node name
        :param sock: UDP socket bound to server address
        :return: None
        """
        pass

    @abstractmethod
    def client_process(
        self, name, sock: socket.socket, server_ip: str, server_port: int
    ) -> dict:
        """
        Client processing logic for the algorithm.
        :param name: node name
        :param sock: UDP socket for sending requests
        :param server_ip: Server IP address
        :param server_port: Server port
        :return: dict for t1, t2, t3, t4, offset, rtt
        """
        pass

    @abstractmethod
    def get_name(self):
        '''
        Get the name of the algorithm
        '''
        pass
    
    def accumulate_offset(self, offset: float):
        """
        Accumulate offset to the system time.
        :param offset: offset to accumulate
        """
        self.cumulative_offset += offset
        
    def accumulate_offset_server(self, offset: float):
        """
        Accumulate offset to the system time.
        :param offset: offset to accumulate
        """
        self.cumulative_offset_server += offset

    def get_simulated_time(self) -> float:
        """
        Get current time of the system.
        Takes cumulated offset into consideration, which makes simulation more reality.
        """
        return time.time() + self.cumulative_offset

    def get_simulated_time_server(self) -> float:
        """
        Get current time of the system.
        Takes cumulated offset into consideration, which makes simulation more reality.
        """
        return time.time() + self.cumulative_offset_server
