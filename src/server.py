import asyncio
import machine
import re

from src.clock import Clock
from src.filesystem import boot_write, wifi_write, settings_read, settings_write, delete_all

# region HTTP_STATUS
STATUS_OK_HTML = "HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n"
STATUS_OK_CSS = "HTTP/1.0 200 OK\r\nContent-type: text/css\r\n\r\n"
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
async def web_server(request_handler, reboot_handler = None):
    print("\nweb_server")

    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, request_handler, reboot_handler),
        "0.0.0.0",
        80
    )
    return server

async def handle_client(reader, writer, request_handler, reboot_handler = None):
    request = await reader.read(1024)
    print("\nhttp request:\n" + str(request))

    response, reboot = await request_handler(request)
    
    writer.write(response.encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()

    # Reboot
    if (reboot == True):
        if (reboot_handler != None):
            await reboot_handler()
#endregion

# region GATEWAY_ROUTES
async def handle_request_gateway(request, template_data):
    ip = template_data["ip"]
    networks = template_data["networks"]

    verb, path = _get_verb_path(request)
    print("\n", verb, path)

    # GET /
    if (path == "/"):
        with open("static/index.html", "r") as f:
            html = f.read()
        html = html.replace("{IP_ADDRESS}", ip)
        html = html.replace("{DESTINATION}", "connect")

        response = STATUS_OK_HTML
        response += html
        return response, False

    # GET /connect
    elif (verb == "GET" and path == "/connect"):
        options = "\n".join([f'<option value="{n["ssid"]}">{n["ssid"]}</option>' for n in networks])
        
        with open("static/connect.html", "r") as f:
            html = f.read()
        html = html.replace("{IP_ADDRESS}", ip)
        html = html.replace("{BODY_CLASS}", "state-default")
        html = html.replace("{WIFI_OPTIONS}", options)

        response = STATUS_OK_HTML
        response += html
        return response, False

    # POST /connect
    elif (verb == "POST" and path == "/connect"):
        # Parse params from body
        body = _get_body(request)
        param_ssid = _get_param(body, "ssid")
        param_password = _get_param(body, "password")

        # Ensure required params are present
        if (param_ssid == None or param_password == None):
            response = STATUS_BAD_REQUEST
            response += "Missing required parameters"
            return response, False
        # Validate params
        if (not bool(re.search(r"^[a-zA-Z0-9_ \.\-]+$", str(param_ssid)))):
            response = STATUS_BAD_REQUEST
            response += "Invalid ssid"
            return response, False
        if (not len(str(param_password)) >= 8):
            response = STATUS_BAD_REQUEST
            response += "Invalid password"
            return response, False
        
        # Write wifi credentials to file
        wifi_write(param_ssid, param_password)
        # Set boot mode to default
        boot_write("default")

        # Return HTML
        with open("static/connect.html", "r") as f:
            html = f.read()
        html = html.replace("{IP_ADDRESS}", ip)
        html = html.replace("{BODY_CLASS}", "state-reboot")

        response = STATUS_OK_HTML
        response += html
        return response, True

    # Try shared routes
    else:
        return handle_request_shared(request, template_data)
# endregion

# region STATUS_ROUTES
async def handle_request_status(request, template_data):
    satellites = template_data["satellites"]
    timestamp = template_data["timestamp"]
    lat = template_data["lat"]
    lon = template_data["lon"]
    ip = template_data["ip"]
    time_display = template_data["time_display"]
    time_display = f"{time_display[0:2]}:{time_display[2:4]}"

    verb, path = _get_verb_path(request)
    print("\n", verb, path)

    # GET /
    if (path == "/"):
        with open("static/index.html", "r") as f:
            html = f.read()
        html = html.replace("{IP_ADDRESS}", ip)
        html = html.replace("{DESTINATION}", "status")

        response = STATUS_OK_HTML
        response += html
        return response, False

    # GET /status
    elif (path == "/status"):
        with open("static/status.html", "r") as f:
            html = f.read()
        html = html.replace("{IP_ADDRESS}", ip)
        html = html.replace("{TIMESTAMP}", timestamp)
        html = html.replace("{TIME_DISPLAY}", time_display)
        html = html.replace("{SATELLITES}", str(satellites))
        html = html.replace("{LAT}", str(lat))
        html = html.replace("{LON}", str(lon))

        response = STATUS_OK_HTML
        response += html
        return response, False
    
    # Try shared routes
    else:
        return handle_request_shared(request, template_data)
# endregion

# region SHARED_ROUTES
def handle_request_shared(request, template_data):
    verb, path = _get_verb_path(request)
    ip = template_data["ip"]

    if (path == "/css/styles.css"):
        with open("static/css/styles.css", "r") as f:
            css = f.read()
        
        response = STATUS_OK_CSS
        response += css
        return response, False

    # GET /config
    elif (verb == "GET" and path == "/config"):
        with open("static/config.html", "r") as f:
            html = f.read()
        html = html.replace("{IP_ADDRESS}", ip)
        html = html.replace("{BODY_CLASS}", "state-default")

        # Sync current settings to HTML form
        f24hr, tz, dst = settings_read()
        html = html.replace(f'id="chkFormat"', f'id="chkFormat"{" checked" if f24hr else ""}')
        html = html.replace(f'option value="{tz}"', f'option value="{tz}" selected')
        html = html.replace(f'option value="{dst}"', f'option value="{dst}" selected')

        response = STATUS_OK_HTML
        response += html
        return response, False
    
    # POST /config
    elif (verb == "POST" and path == "/config"):
        # Parse params from body
        body = _get_body(request)
        param_mode = _get_param(body, "mode")

        # Validate mode param
        if (not bool(re.search(r"^(update|reboot|reset)$", str(param_mode)))):
            response = STATUS_BAD_REQUEST
            response += "Invalid mode"
            return response, False
        
        # mode: "update"
        if (param_mode == "update"):
            param_format_24hr = _get_param(body, "format24hr")
            param_tz = _get_param(body, "tz")
            param_dst = _get_param(body, "dst")

            # Ensure required params are present
            if (param_tz == None or param_dst == None):
                response = STATUS_BAD_REQUEST
                response += "Missing required parameters"
                return response, False
            # Validate params
            if (not bool(re.search(r"^[0-9\-]+$", str(param_tz)))):
                response = STATUS_BAD_REQUEST
                response += "Invalid tz"
                return response, False
            if (not bool(re.search(r"^(none|us|uk|au)$", str(param_dst)))):
                response = STATUS_BAD_REQUEST
                response += "Invalid dst"
                return response, False

            # Write settings to file
            settings_write(param_format_24hr, int(param_tz), param_dst)
            f24hr, tz, dst = settings_read()

            # Update clock without reboot
            clock = Clock.get_instance()
            clock.init_localtime(f24hr, tz, dst)

            # Return HTML
            with open("static/config.html", "r") as f:
                html = f.read()
            html = html.replace("{IP_ADDRESS}", ip)
            html = html.replace("{BODY_CLASS}", "state-updated")

            response = STATUS_OK_HTML
            response += html
            return response, False
        
        # mode: "reboot"
        elif (param_mode == "reboot"):
            # Return HTML
            with open("static/config.html", "r") as f:
                html = f.read()
            html = html.replace("{IP_ADDRESS}", ip)
            html = html.replace("{BODY_CLASS}", "state-reboot")

            response = STATUS_OK_HTML
            response += html
            return response, True

        # mode: "reset"
        elif (param_mode == "reset"):
            # Return HTML
            with open("static/config.html", "r") as f:
                html = f.read()
            html = html.replace("{IP_ADDRESS}", ip)
            html = html.replace("{BODY_CLASS}", "state-reset")

            # Delete all config files
            delete_all()

            response = STATUS_OK_HTML
            response += html
            return response, True

        # Default
        else:
            response = STATUS_BAD_REQUEST
            response += "Invalid mode"
            return response, False
    
    # Default
    else:
        response = STATUS_NOT_FOUND
        return response, False
# endregion

# region HELPERS

# Get path from request
def _get_verb_path(request):
    request_str = request.decode("utf-8")
    headers = request_str.split("\n")
    verb_path = headers[0].split(" ")
    return verb_path[0].upper(), verb_path[1]

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
        val = _url_decode(keyval.split("=")[1])
        if (val == "true"):
            return True
        elif (val == "false"):
            return False
        return val
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