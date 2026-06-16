from src.network_simulation import NetworkSimulation

if __name__ == "__main__":
    # 清理仿真程序生成的容器、网络、配置文件
    network_simulation = NetworkSimulation()
    network_simulation.cleanup()
