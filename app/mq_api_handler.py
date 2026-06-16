import atexit
import ipaddress
import json
import os
import re
import subprocess
import threading
from itertools import combinations
from time import sleep

from src.network_simulation import NetworkSimulation


class NetworkAPIHandler:
    def __init__(self, mq_sender):
        self.ns = NetworkSimulation()
        self.is_starting = False
        self.is_started = False
        self.is_sender_started = False

        self.node_info = []
        self.edges = []
        self.mq_sender = mq_sender
        self.forward_process = None

    def cleanup(self):
        self.ns.cleanup()

    def start_simulation(self):
        if self.is_starting or self.is_started:
            print('环境已启动或在启动中，请勿重复启动')
            return
        if not self.node_info or not self.edges:
            print('未满足启动条件')
            return
        self.is_starting = True
        self.ns.create_custom_topology(nodes=self.node_info, edges=self.edges)
        # self.ns.create_lisp_topology(num_xtr=2, num_msmr=1)

        xtr_eid_map = {}
        xtr_edges = []
        for node in self.node_info:
            subnet =  node.get("subnet")
            if not subnet:
                continue
            subnet_cidr = ipaddress.IPv4Network(f"{subnet}", strict=False)
            xtr_name = f"{node.get('name')}_xTR"
            xtr_eid_map[xtr_name] = str(subnet_cidr)
            xtr_edges.append([node.get('name'), xtr_name])

        print(xtr_eid_map)
        print(xtr_edges)
        self.ns.create_lisp_topology_from_map(
            xtr_edges=xtr_edges,
            xtr_eid_map=xtr_eid_map
        )

        self.ns.display_network_topology()
        self.ns.start_simulation()

        binary_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../docker/socket/udp_forward')
        log_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../output/forward.log')
        map_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../output/forward_targets.json')
        self.forward_process = self.start_binary(binary_path, log_file_path, "5132", "5132", "0", map_file_path)
        print(f"转发进程{self.forward_process.pid}已启动，日志路径：{log_file_path}")

        self.is_started = True
        self.is_starting = False

        self.ns.apply_tc_on_edges(edges=self.edges, delay='1ms', jitter='1ms')

        if not self.is_sender_started:
            threading.Thread(target=self.send_network_info).start()
            self.is_sender_started = True

    def stop_simulation(self):
        # self.ns.stop_simulation()
        self.cleanup()
        self.reset_info()
        if self.forward_process:
            self.forward_process.terminate()
            print(f"进程{self.forward_process}已停止")

    def restart_simulation(self):
        self.ns.stop_simulation()
        self.cleanup()
        self.start_simulation()

    def config_nodes(self, nodes):
        processed_nodes = []
        for node in nodes:
            processed_node = {
                "name": node.get("name"),
                "type": node.get("type"),
                "subnet": node.get("subnet"),
                "coordinates": {
                    "latitude": node.get("latitude"),
                    "longitude": node.get("longitude")
                }
            }
            processed_nodes.append(processed_node)
        self.node_info = processed_nodes
        print('已更新节点配置')

    def config_topo(self, topo_data):
        nodes = []
        edges = set()
        for node in topo_data:
            node_name = node["name"]
            nodes.append(node_name)  # 添加节点到集合中
            for neighbor in node["topo"]:
                # 添加双向边，但只存储单一方向
                edge = tuple(sorted([node_name, neighbor]))
                edges.add(edge)

        edges = [list(edge) for edge in edges]
        self.edges = edges
        print('已更新拓扑配置')

    @staticmethod
    def create_mapping(mapping_info):
        js_list = []
        for mapping in mapping_info:
            source = mapping.get("ExternalIP")
            destination = mapping.get("SimIP")
            js_list.append({"source": source, "destination": destination})
        js = {"forward_targets": js_list}
        js_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../output/forward_targets.json')
        with open(js_path, 'w') as f:
            f.write(json.dumps(js))
        print('映射文件保存成功')

    def remove_mapping(self):
        # 暂不使用
        pass

    def reset_info(self):
        self.node_info.clear()
        self.edges.clear()
        self.is_starting = False
        self.is_started = False
        self.is_sender_started = False

    @staticmethod
    def get_instant_traffic(interface: str):
        try:
            # 调用 ifstat 命令并获取第三行的第一列（瞬时流量值）
            result = subprocess.check_output(["ifstat", "-i", interface, "1", "1"], text=True)
            instant_traffic = result.splitlines()[2].split()[0]
            print(f"入口流量：{instant_traffic} KB/s")
            return instant_traffic
        except Exception as e:
            print(f"流量获取错误：{e}")
            return None

    @staticmethod
    def get_ss_udp_total(protocol='UDP'):
        try:
            # 执行 `ss -s` 命令并获取输出
            result = subprocess.run(['ss', '-s'], capture_output=True, text=True, check=True)
            # 使用正则表达式提取 UDP Total 值
            match = re.search(rf'{protocol}\s+(\d+)', result.stdout)
            if match:
                return int(match.group(1))  # 提取并转换为整数
            else:
                return None  # 如果没有匹配到，返回 None
        except Exception as e:
            print(f"队列获取错误：{e}")
            return None

    def send_network_info(self):
        print('信息发送线程已开始')
        while True:
            if not self.is_started:
                break
            # ping_res_list = self.ns.ping_all()
            # trace_res_list = self.ns.traceroute_all()
            # throughput = self.get_instant_traffic('ens33')
            # waiting_len = self.get_ss_udp_total()

            # merged_list = []
            # for item1 in ping_res_list:
            #     for item2 in trace_res_list:
            #         if item1['src_node'] == item2['src_node'] and item1['dst_node'] == item2['dst_node']:
            #             merged_item = {**item1, **item2}
            #             merged_list.append(merged_item)
            #
            # if not ping_res_list:
            #     continue
            # for ping_res in merged_list:
            #     delay = ping_res.get("avg_delay")
            #     if not delay:
            #         continue
            #     delay = delay/2
            #     data = {
            #         "src_ip": ping_res.get("src_ip"),
            #         "dst_ip": ping_res.get("dst_ip"),
            #         "total_delay": delay,
            #         "loss_rate": ping_res.get("loss_rate"),
            #         "throughput": throughput,
            #         "waiting_len": waiting_len,
            #         "route_path": ping_res.get("route_path")[:-1],
            #         "name": "gr"
            #     }
            #     self.mq_sender(data)
            # sleep(10)

            for pair in combinations(self.ns.xtr_nodes, 2):
                if not self.is_started:
                    break
                sleep(5)
                print(f'-> Test {pair[0].name} to {pair[-1].name}...')
                trace_res = self.ns.get_pair_traceroute(*pair)
                ping_res = self.ns.get_pair_delay(*pair)
                merged_item = {**trace_res, **ping_res}
                delay = merged_item.get("avg_delay")
                route_path = merged_item.get("route_path")
                if not delay:
                    continue
                if not route_path or '*' in route_path:
                    continue
                delay = delay/2
                throughput = self.get_instant_traffic('ens33')
                waiting_len = self.get_ss_udp_total()
                data = {
                    "src_ip": ping_res.get("src_ip"),
                    "dst_ip": ping_res.get("dst_ip"),
                    "total_delay": delay,
                    "loss_rate": ping_res.get("loss_rate"),
                    "throughput": throughput,
                    "waiting_len": waiting_len,
                    "route_path": route_path[:-1],
                    "name": "gr"
                }
                self.mq_sender(data)
        print('信息发送线程已停止')

    @staticmethod
    def start_binary(binary_path, log_file_path, *args):
        log_file = open(log_file_path, "w")
        # 使用 stdbuf 禁用缓冲
        process = subprocess.Popen(
            ["stdbuf", "-oL", "-eL", binary_path, *args],  # -oL 禁用标准输出缓冲，-eL 禁用标准错误缓冲
            stdout=log_file,  # 重定向标准输出到文件
            stderr=log_file  # 重定向标准错误到文件
        )

        # 注册退出时清理的函数
        def cleanup():
            try:
                process.terminate()  # 终止进程
                process.wait(timeout=5)  # 等待进程结束
            except Exception as e:
                print(f"Error cleaning up process: {e}")
            finally:
                log_file.close()  # 确保关闭日志文件

        atexit.register(cleanup)
        return process


if __name__ == '__main__':
    na = NetworkAPIHandler('')
    na.cleanup()
    na.get_instant_traffic('ens33')
