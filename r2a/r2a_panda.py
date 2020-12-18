from r2a.ir2a import IR2A
from player.parser import *
import time
from statistics import mean

class R2A_Panda(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)

        self.throughput_list = [] # lista de throughtputs

        self.request_time = 0 # para medir o tempo de requisicao

        self.download_time = [] # Lista que registra os tempos de download

        self.bandwidth_share_list = [1] 

        self.datarate_list = []

        self.bit_length_list = [] # Lista de tamanho das mensagens

        self.qi = [] # lista de qualidade

    def handle_xml_request(self, msg):
        # Primeira função a ser requisitada
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        # Definição dos valores do player e do vídeo a ser executado
        parsed_mpd = parse_mpd(msg.get_payload()) #Divisão dos valores presentes no arquivo .xml

        # lista de qualidades
        self.qi = parsed_mpd.get_qi()

        timing = time.perf_counter() - self.request_time
        self.throughput_list.append(msg.get_bit_length() / timing)

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter() #Registro do tempo de requisição
        self.download_time.append(time.time()) #Registro do tempo de download

        # Etapa de compartilhamento de largura de banda
        segment_download_time = self.download_time[-1] - self.download_time[len(self.download_time)-2]
        last_throughput = self.throughput_list[-1] # Taxa de transferência da última requisição
        interquest_request_time = max(segment_download_time, self.bandwidth_share_list[-1]) # Tempo da última requisição

        if(len(self.bandwidth_share_list) == 0):
            self.bandwidth_share_list.append(last_throughput)
        else:
            bandwidth_share = ((last_throughput - self.bandwidth_share_list[-1]) / interquest_request_time)
            self.bandwidth_share_list.append(bandwidth_share)

        # Etapa de suavização do compartilhamento da largura de banda
        # smoothed_version = sum(list(map(lambda x: 1/x, self.bandwidth_share_list)))
        # smoothed_version = len(self.bandwidth_share_list) / smoothed_version

        #Suavização de proteção a picos inesperados ou errados de largura de banda
        smoothed_version = self.bandwidth_share_list[-2:] 
        smoothed_version = sum(smoothed_version)/len(smoothed_version)

        # Etapa quantificação dos valores suavizados
        selected_quality = self.qi[0]
        for quality in self.qi:
            if smoothed_version < quality:
                selected_quality = quality

        # Etapa de Marcação
        B = 0.2
        buffer_min = 20

        buffer_size_tuple = self.whiteboard.get_playback_buffer_size()

        if(len(buffer_size_tuple) > 0):
            buffer_size = buffer_size_tuple[-1][1]
        else:
            buffer_size = 0

        self.bandwidth_share_list.append((selected_quality/smoothed_version)+(B*(buffer_min - buffer_size)))
        
        msg.add_quality_id(selected_quality)
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        timing = time.perf_counter() - self.request_time
        self.throughput_list.append(msg.get_bit_length() / timing)
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
