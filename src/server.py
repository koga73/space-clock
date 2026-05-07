import socket
import json
import re

MAX_CLIENTS = 3

# region HTTP_STATUS
STATUS_OK = "HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n"
STATUS_BAD_REQUEST = """HTTP/1.1 400 Bad Request
Content-Type: text/plain
\r\n
"Bad Request"
"""
STATUS_NOT_FOUND = """HTTP/1.1 404 Not Found
Content-Type: text/plain
\r\n
"Not Found"
"""
# endregion

# region WEB_SERVER
# Handle incoming HTTP requests and send to the appropriate handler
def web_server(request_handler):
    print("\nweb_server")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 80))
    s.listen(MAX_CLIENTS)

    print("listening on port 80...")

    break_flag = False
    while True:
        conn, addr = s.accept()
        print(json.dumps({"client": addr}))

        request = conn.recv(1024)
        print("\nrequest:\n" + str(request))

        break_flag = request_handler(conn, request)
        conn.close()
        
        if (break_flag == True):
            break

#endregion

# region ROUTES_GATEWAY
def handle_request_gateway(conn, request, template_data):
    path = _get_path(request)

    # GET /
    if (path == "/"):
        title = template_data["title"]
        networks = template_data["networks"]
        options = "\n".join([f'<option value="{n["ssid"]}">{n["ssid"]}</option>' for n in networks])
        
        with open("static/gateway/index.html", "r") as f:
            html = f.read()
        html = html.replace("{TITLE}", title)
        html = html.replace("{WIFI_OPTIONS}", options)
        html = html.replace("{IP_ADDRESS}", template_data["ip"])

        conn.send(STATUS_OK)
        conn.send(html)
        conn.close()
        return

    # POST /connect
    elif (path == "/connect"):
        # Parse params from body
        body = _get_body(request)
        param_ssid = _get_param(body, "ssid")
        param_password = _get_param(body, "password")

        # Ensure required params are present
        if (param_ssid == None or param_password == None):
            conn.send(STATUS_BAD_REQUEST)
            conn.send("Missing required parameters")
            conn.close()
            return
        # Validate params
        if (not bool(re.search(r"^[a-zA-Z0-9_ \.\-]+$", str(param_ssid)))):
            conn.send(STATUS_BAD_REQUEST)
            conn.send("Invalid ssid")
            conn.close()
            return
        if (not len(str(param_password)) >= 8):
            conn.send(STATUS_BAD_REQUEST)
            conn.send("Invalid password")
            conn.close()
            return
        
        # Write wifi credentials to file
        wifi = {"ssid":param_ssid, "password":param_password}
        print("\n", wifi)
        with open("wifi.txt", "w") as f:
            f.write(json.dumps(wifi))

        # Return HTML
        title = template_data["title"]
        with open("static/gateway/connect.html", "r") as f:
            html = f.read()
        html = html.replace("{TITLE}", title)

        conn.send(STATUS_OK)
        conn.send(html)
        conn.close()
        # Signal to break the server loop and reboot
        return True

    # Default
    else:
        conn.send(STATUS_NOT_FOUND)
        conn.close()
        return
# endregion

# region ROUTES_STATUS
def handle_request_status(conn, request, template_data):
    path = _get_path(request)

    # GET /
    if (path == "/"):
        title = template_data["title"]
        
        with open("static/status/index.html", "r") as f:
            html = f.read()
        html = html.replace("{TITLE}", title)

        conn.send(STATUS_OK)
        conn.send(html)
        conn.close()
        return
    
    # Default
    else:
        conn.send(STATUS_NOT_FOUND)
        conn.close()
        return
# endregion

# region HELPERS 

# Get path from request
def _get_path(request):
    request_str = request.decode("utf-8")
    headers = request_str.split("\n")
    path = headers[0].split(" ")[1]
    return path

# Get body from request
def _get_body(request):
    requestStr = request.decode("utf-8")
    headers = requestStr.split("\n")
    body = headers[-1]
    return body

# Get param value from query string or body
def _get_param(str, param):
    params = (str.split("?")[1] if "?" in str else str).split("&")
    keyval = next(filter(lambda p: p.startswith(param), params), None)
    if (keyval == None):
        return None
    if ("=" in keyval):
        return _url_decode(keyval.split("=")[1])
    else:
        return True

# URL decode a string
def _url_decode(value):
    value = value.replace("+", " ")
    result = ""
    i = 0
    while i < len(value):
        if value[i] == "%" and i + 2 < len(value):
            result += chr(int(value[i+1:i+3], 16))
            i += 3
        else:
            result += value[i]
            i += 1
    return result

#endregion