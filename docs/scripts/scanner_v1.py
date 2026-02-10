import socket
import sys

def check_vulnerability(target_ip, port):
    """
    Sample Vulnerability Scanner v1.0
    Description: Checks if specific ports are open and banner identification.
    THIS IS FOR EDUCATIONAL PURPOSES ONLY.
    """
    print(f"[*] Initializing scan for: {target_ip} on port {port}")
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        
        # Attempt to connect
        result = s.connect_ex((target_ip, port))
        
        if result == 0:
            print(f"[!] ALERT: Port {port} is OPEN on {target_ip}")
            print("[*] Recommendation: Check if this service needs to be exposed. Apply latest patches.")
        else:
            print(f"[+] SUCCESS: Port {port} is closed or filtered.")
            
        s.close()
    except Exception as e:
        print(f"[-] Error during scan: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scanner_v1.py <target_ip>")
    else:
        target = sys.argv[1]
        # Common ports associated with recent vulnerabilities
        ports_to_check = [8080, 443, 445]
        for p in ports_to_check:
            check_vulnerability(target, p)
