import network
import time

import config

class Connection():
    def __init__(self):
        # Connect to Wi-Fi
        self.wifi = network.WLAN(network.STA_IF)
        self.wifi.active(True)
        self.wifi.connect(config.WIFI_SSID, config.WIFI_PWD)

        # Wait for connection
        while not self.wifi.isconnected():
            print("Not connected...")
            time.sleep(1)

        # Print success message
        print('Connected to Wi-Fi, IP address:', self.wifi.ifconfig()[0])    


if __name__ == "__main__":
    new_connection = Connection()