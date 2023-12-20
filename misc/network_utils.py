import subprocess
import platform


def get_local_ip() -> str:
    os_name = platform.system()
    if os_name.lower() == "windows":
        try:
            result = subprocess.run(
                    ["powershell", "(Get-NetIPAddress -AddressFamily IPv4 -AddressState Preferred) | Where-Object { "
                                   "$_.IPAddress -like '192.*' } | Select-Object -ExpandProperty IPAddress"],
                    capture_output=True,
                    text=True,
                    check=True
                    )
            local_ip_address = result.stdout.strip()
            return local_ip_address
        except subprocess.CalledProcessError as e:
            print(f"Error running powershell {e}")
            return "Unknown"
    elif os_name.lower() == "darwin" or os_name.lower() == "linux":
        try:
            result = subprocess.run(
                    ["ifconfig | grep -Eo 'inet (addr:)?([0-9]*\\.)+[0-9]*' | awk '$1 == \"inet\" {print $2}' | grep "
                     "'^192\\.'"],
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True
                    )
            local_ip_address = result.stdout.strip()
            return local_ip_address
        except subprocess.CalledProcessError as e:
            print(f"Error running powershell {e}")
            return "Unknown"

    else:
        return "Unknown"
