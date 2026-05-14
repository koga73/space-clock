import asyncio
import ustruct
import time

# NTP timestamp starts Jan 1, 1900. MicroPython epoch starts Jan 1, 2000
# Difference is 3,155,673,600 seconds
EPOCH_OFFSET = 3155673600

POLL_INTERVAL = 6 # 2 ^ 6 = 64 seconds: Standard starting default interval for most Linux systems
PRECISION = -10 # 2 ^ -10 = ~1 millisecond: Standard precision for a microcontroller

async def ntp_server():
    print("\nntp_server")

    transport = await start_udp(
        NtpProtocol,
        "0.0.0.0",
        123
    )
    return transport

async def start_udp(protocol, host, port):
    loop = asyncio.get_running_loop()

    transport, _ = await loop.create_datagram_endpoint(
        lambda: protocol(),
        local_addr=(host, port)
    )
    return transport


class NtpProtocol(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport  
    
    def datagram_received(self, data, addr):
        # NTP packages are ALWAYS 48 bytes
        if (len(data) != 48):
            return
        
        self.datagram_received(data, addr)
    
    def process_packet(self, data, addr):
        print("\nntp request:\n" + str(data))

        # Extract Client Transmit Timestamp (bytes 40-47 in request)
        client_transmit_timestamp = data[40:48]

        # Get current time and convert to NTP time
        current_seconds = time.time() + EPOCH_OFFSET

        # Construct NTP Response Packet (48 bytes)
        response = bytearray(48)
        response[0] = 0x24              # LI=0 (no warning), VN=4 (IPv4), Mode=4 (server) -> 0x24
        response[1] = 1                 # Stratum 1 (Primary reference)
        response[2] = POLL_INTERVAL     # Poll interval
        response[3] = PRECISION         # Precision

        # Root Delay & Root Dispersion (4 bytes each, set to 0)
        response[12:16] = b'LOCL' # Reference ID (4 bytes, e.g., 'LOCL')

        # Reference Timestamp (last time synced, approximation)
        response[16:20] = ustruct.pack("!I", current_seconds)
        
        # Origin Timestamp from client
        response[24:32] = client_transmit_timestamp

        # Receive Timestamp (when packet arrived at server)
        response[32:36] = ustruct.pack("!I", current_seconds)

        # Transmit Timestamp (when packet leaves server)
        response[40:36 + 4] = ustruct.pack("!I", current_seconds)

        # Send packet back to client
        self.transport.sendto(data, addr)
