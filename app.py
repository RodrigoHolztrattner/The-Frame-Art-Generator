from enum import Enum
from colorama import init, Fore
import asyncio
import base64
from enum import Enum
from io import BytesIO
import random
import sys
import threading
from flask import Flask, request, jsonify, render_template
import json
import os
from threading import Thread, Event
import time
from ollama_connector import OllamaConnector
from sd_connector import StableDiffusionConnector
from global_config import GlobalConfig
import websockets
from samsungtvws import SamsungTVWS
import paho.mqtt.client as mqtt

###########
# GLOBALS #
###########

# Config
global_config = GlobalConfig()

# App
app = Flask(__name__)
generate_task_thread = None
generate_stop_event = threading.Event()
frontend_clients = set()
block_requests = False

# Connectors
ollama_connector = OllamaConnector()
sd_connector = StableDiffusionConnector()
the_frame_connector = None

# MQTT
mqtt_client = None

###########
# BACKEND #
###########

# Initialize colorama for Windows color support
init()

class LogType(Enum):
    VERBOSE = "VERBOSE"
    INFO = "INFO"
    WARNING = "WARNING" 
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_string(cls, level_str: str) -> 'LogType':
        try:
            return cls[level_str.upper()]
        except KeyError:
            return cls.WARNING

def log(type: LogType, domain: str, message: str):
    current_level = LogType.from_string(os.getenv('LOG_LEVEL', 'VERBOSE'))
    
    if type.value >= current_level.value:
        colors = {
            LogType.VERBOSE: Fore.WHITE,
            LogType.INFO: Fore.BLUE,
            LogType.WARNING: Fore.YELLOW,
            LogType.ERROR: Fore.RED,
            LogType.CRITICAL: Fore.MAGENTA
        }
        color = colors.get(type, Fore.WHITE)
        print(f"{color}[{type.name}] {domain} - {message}{Fore.RESET}")

def try_load_global_config():
    global global_config
    try:
        with open("config/config.json", "r") as f:
            global_config.load_from_json(json.load(f))
            log(LogType.VERBOSE, "System", f"Global config loaded from existing JSON file, contents: {global_config.get_as_json()}")
            return True
    except Exception as e:
        log(LogType.VERBOSE, "System", f"try_load_global_config() failed with exception: {e}")
        return False
    
def try_save_global_config():
    global global_config
    try:
        with open("config/config.json", "w") as f:
            json.dump(global_config.get_as_json(), f, indent=4)
            log(LogType.VERBOSE, "System", f"Global config saved to JSON file, contents: {global_config.get_as_json()}")
            return True
    except Exception as e:
        log(LogType.VERBOSE, "System", f"try_save_global_config() failed with exception: {e}")
        return False
    
def create_default_global_config():
    local_global_config = GlobalConfig()
    try:
        with open("config/config.json", "w") as f:
            json.dump(local_global_config.get_as_json(), f, indent=4)
            log(LogType.VERBOSE, "System", "Empty global config file created")
            return True
    except Exception as e:
        log(LogType.VERBOSE, "System", f"create_default_global_config() failed with exception: {e}")
        return False
    
def disconnect_backend():
    global global_config, ollama_connector, sd_connector, the_frame_connector
    global_config.auto_connect = False
    global_config.generation_auto_generate = False
    refresh_periodic_generate()    
    ollama_connector = OllamaConnector()
    sd_connector = StableDiffusionConnector()
    the_frame_connector = None
    log(LogType.VERBOSE, "System", "Backend disconnected")

def disconnect_mqtt():
    global global_config, mqtt_client
    if mqtt_client:
        mqtt_client.publish(f"{global_config.mqtt_ha_prefix}/availability", "offline", retain=True)
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        mqtt_client = None
        log(LogType.VERBOSE, "System", "MQTT disconnected")

def try_connect(force_refresh: bool):
    global global_config, ollama_connector, sd_connector, the_frame_connector

    if force_refresh:
        disconnect_backend()

    if not ollama_connector.is_connected():
        ollama_connector.connect(global_config.ollama_ip, str(global_config.ollama_port))
        log(LogType.VERBOSE, "System", f"Ollama connect attempt, new status: {ollama_connector.is_connected()}")
        
    if not sd_connector.is_connected():
        sd_connector.connect(global_config.sd_ip, str(global_config.sd_port))
        log(LogType.VERBOSE, "System", f"SD connect attempt, new status: {sd_connector.is_connected()}")

    if global_config.the_frame_ip and not the_frame_connector:
        token_file = os.path.dirname(os.path.realpath(__file__)) + '/temp/tv-token.txt'
        the_frame_connector = SamsungTVWS(host=global_config.the_frame_ip, port=global_config.the_frame_port, token_file=token_file) # 8001 for unsecured websocket
        log(LogType.VERBOSE, "System", f"The Frame connect attempt, new status: {bool(not global_config.the_frame_ip or the_frame_connector)}")

    log(LogType.VERBOSE, "System", f"Connecting backend, force refresh is set to {force_refresh}, Ollama status: {ollama_connector.is_connected()}, SD status: {sd_connector.is_connected()}, The Frame status: {bool(not global_config.the_frame_ip or the_frame_connector)}")

    return ollama_connector.is_connected() and sd_connector.is_connected() and bool(not global_config.the_frame_ip or the_frame_connector)

def try_connect_mqtt(force_refresh: bool):
    global mqtt_client, global_config

    if force_refresh or not global_config.mqtt_enable:
        log(LogType.INFO, "MQTT", "Reseting...")
        disconnect_mqtt()

    are_configs_valid = global_config.mqtt_broker_ip and global_config.mqtt_port

    if not mqtt_client and global_config.mqtt_enable and are_configs_valid:
        mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=global_config.mqtt_client_id)

        if global_config.mqtt_user and global_config.mqtt_password:
            mqtt_client.username_pw_set(global_config.mqtt_user, global_config.mqtt_password)

        mqtt_client.on_connect = mqtt_on_connect
        mqtt_client.on_message = mqtt_on_message

        log(LogType.INFO, "MQTT", "Connecting...")
        mqtt_client.connect(global_config.mqtt_broker_ip, global_config.mqtt_port, 60)

        log(LogType.INFO, "MQTT", "Starting loop...")
        mqtt_client.loop_start()

    log(LogType.VERBOSE, "System", f"Connecting MQTT, force refresh is set to {force_refresh}, MQTT status: {bool(mqtt_client)}")

def try_generate_image(use_mqtt_prompt=False):
    global global_config, ollama_connector, sd_connector

    mqtt_update_sensor("status", "Generating Image Prompt")

    # Determine which prompt instruction we should use
    ollama_message = global_config.generation_positive_instruction
    if use_mqtt_prompt and global_config.mqtt_positive_instruction:
        if global_config.mqtt_positive_command:
            ollama_message = global_config.mqtt_positive_instruction.replace("{command}", global_config.mqtt_positive_command)
        else:
            log(LogType.WARNING, "MQTT", "No positive command given by the substring {command} was found, using default prompt instructions")
    elif use_mqtt_prompt:
        log(LogType.WARNING, "MQTT", "No positive instruction given, using default prompt instructions")
        
    # Generate positive prompt using Ollama
    generated_prompt = ollama_connector.send_message(
        model=global_config.ollama_model, 
        message=ollama_message)

    mqtt_update_sensor("status", "Generating Image")

    # Generate image using Stable Diffusion
    log(LogType.VERBOSE, "System", f"Setting SD model to {global_config.sd_model}")
    sd_connector.set_model(global_config.sd_model)
    log(LogType.VERBOSE, "System", "Issuing SD request for txt2img")
    sd_generate_response = sd_connector.txt2img(
        prompt=generated_prompt,
        negative_prompt=global_config.generation_negative_prompt,
        width=global_config.image_width,
        height=global_config.image_height,
        steps=global_config.generation_steps,
        seed=global_config.generation_seed,
        lora=global_config.sd_lora,
        sampler_name="Euler",
        cfg_scale=7.0, 
        upscale=global_config.image_upscale
    )

    if global_config.image_upscale and global_config.image_upscale > 0:
        log(LogType.VERBOSE, "System", "Image upscaling requested, issuing SD request")
        sd_generate_response = sd_connector.upscale_image(
            sd_generate_response.image, 
            global_config.image_upscale, 
            global_config.image_width, 
            global_config.image_height)

    return sd_generate_response.image

def try_upload_image(image_buffer):
    global the_frame_connector, global_config

    # tv.shortcuts().power()
    # wakeonlan.send_magic_packet('CC:6E:A4:xx:xx:xx')

    target_content_id = None

    if the_frame_connector.art().supported():

        if global_config.the_frame_force_art_mode and not the_frame_connector.art().get_artmode():
            log(LogType.INFO, "The Frame", "Forcing art mode")
            the_frame_connector.art().set_artmode(True)

        def try_get_current_art_content(tv):
            try:
                art_available = tv.art().available()
                log(LogType.VERBOSE, "The Frame", f"try_get_current_art_content() non filtered contents are: {art_available}")
                filtered_art_content = [item['content_id'] for item in art_available if item.get('content_type') == 'mobile']
                log(LogType.VERBOSE, "The Frame", f"try_get_current_art_content() filtered contents are: {filtered_art_content}")
                return filtered_art_content
            except Exception as e:
                log(LogType.ERROR, "The Frame", f"try_get_current_art_content() resulted in exception: {e}")
                return []
            
        def try_delete_previous_images(previous_image_list):
            global global_config
            if not global_config.the_frame_clear_old_art:
                return
            
            try:
                if previous_image_list:
                    log(LogType.INFO, "The Frame", f"Filtering existing art to be deleted: {previous_image_list}")
                    the_frame_connector.art().delete_list(previous_image_list)
            except Exception as e:
                log(LogType.WARNING, "The Frame", f"Failed to delete old art, this shouldn't cause any issues but previous images will linger til next art update, exception: {e}")
                
        def try_select_art_image(entry_id):
            if entry_id:
                try:
                    the_frame_connector.art().select_image(entry_id)
                    log(LogType.INFO, "The Frame", f"Image {entry_id} selected")
                except Exception as e:
                    log(LogType.ERROR, "The Frame", f"Failed to select image {entry_id}, exception: {e}")
                    pass

        log(LogType.INFO, "The Frame", "Uploading image to TV")

        previous_mobile_content_ids = try_get_current_art_content(the_frame_connector)

        try:
            log(LogType.VERBOSE, "The Frame", "Begin first upload attempt")
            
            target_content_id = the_frame_connector.art().upload(image_buffer.getvalue(), matte='none', portrait_matte='none')

            log(LogType.VERBOSE, "The Frame", f"After upload content ID: {target_content_id}")

            try_select_art_image(target_content_id)
            try_delete_previous_images(previous_mobile_content_ids)

        except Exception as e:

            log(LogType.VERBOSE, "The Frame", f"Upload, art selection or old art deletion failed with exception: {e}")

            # Sometimes the upload is successfull but it still throws an error, in that case see if we can get the image ID
            # and set it directly
            new_mobile_content_ids = try_get_current_art_content(the_frame_connector)
            remainder_mobile_content_ids = [item for item in new_mobile_content_ids if item not in previous_mobile_content_ids]

            log(LogType.WARNING, "The Frame", f"Trying to recover from error, current image contents: {new_mobile_content_ids} - New content: {remainder_mobile_content_ids}")

            if remainder_mobile_content_ids:
                target_content_id = str(remainder_mobile_content_ids[0])
                try_select_art_image(target_content_id)
                try_delete_previous_images(previous_mobile_content_ids)
            else:
                return None

        log(LogType.INFO, "The Frame", "TV upload done")
    else:
        log(LogType.VERBOSE, "The Frame", "Art mode not supported")

    return target_content_id

def try_change_matte(content_id = None):
    global global_config, the_frame_connector

    if not content_id:
        content_id = str(the_frame_connector.art().get_current().get('content_id', None))

    log(LogType.INFO, "The Frame", f"Changing matte for current selection: {content_id}")

    if content_id and (global_config.the_frame_matte and global_config.the_frame_matte != "none"):
        # target_the_frame_matte = global_config.the_frame_matte

        target_the_frame_matte = f"{global_config.the_frame_matte}_polar" if global_config.the_frame_matte != "none" else global_config.the_frame_matte
        
        try:
            log(LogType.INFO, f"The Frame", f"Matte selection: matte[{target_the_frame_matte}]")

            the_frame_connector.art().change_matte(content_id, matte_id = target_the_frame_matte, portrait_matte='none')

            return True
        except Exception as e:
            try:
                the_frame_connector.art().change_matte(content_id, matte_id='none', portrait_matte='none')
                return False
            except Exception as e:
                log(LogType.WARNING, f"The Frame", "Failed to change matte (this will not prevent any previous upload, but your image might be using the wrong matte option)")
    return False

def try_change_photo_filter(content_id = None):   

    global global_config, the_frame_connector

    if not content_id:
        content_id = str(the_frame_connector.art().get_current().get('content_id', None))

    log(LogType.INFO, "The Frame", f"Changing photo filter for current selection: {content_id}")

    return False

def process_image_request(use_mqtt_prompt=False):
    global global_config, ollama_connector, sd_connector, the_frame_connector, block_requests

    are_connectors_valid = ollama_connector and sd_connector
    are_models_valid = global_config.ollama_model and global_config.sd_model
    are_prompts_valid = global_config.generation_positive_instruction

    if not are_connectors_valid or not are_models_valid or not are_prompts_valid:
        return None
    
    if block_requests:
        return None
    
    block_requests = True

    mqtt_update_sensor("status", "Processing Request")

    try:
        mqtt_update_sensor("progress", {"progress": 0})
        generated_image = try_generate_image(use_mqtt_prompt)
        mqtt_update_sensor("progress", {"progress": 100})

        image_buffer = BytesIO()
        generated_image.save(image_buffer, format="PNG")
        base64_image = base64.b64encode(image_buffer.getvalue()).decode("utf-8")

        if the_frame_connector and global_config.the_frame_auto_upload:

            mqtt_update_sensor("status", "Uploading Image")

            def handle_upload_failure(error_msg="Unknown error"):
                log(LogType.ERROR, "System", f"Failed to upload image with error: {error_msg}, refreshing all connections and attempting for a second time after 6 seconds")
                time.sleep(2)
                try_connect(True)
                time.sleep(2)
                refresh_periodic_generate()
                time.sleep(2)
                return try_upload_image(image_buffer)

            uploaded_content_id = None
            try:
                uploaded_content_id = try_upload_image(image_buffer)
                if uploaded_content_id is None:
                    uploaded_content_id = handle_upload_failure("First upload attempt failed (returned None)")
            except Exception as e:
                uploaded_content_id = handle_upload_failure(str(e))

            if uploaded_content_id:
                mqtt_update_sensor("status", "Changing Image Matte")
                try_change_matte(uploaded_content_id)
            
        mqtt_update_sensor("image", {"image": base64_image})

        mqtt_update_sensor("status", "Idle")

        block_requests = False

        return base64_image
    except Exception as e:
        log(LogType.ERROR, "System", f"Failed to process image request with error {e}")
        mqtt_update_sensor("status", "Error")
        block_requests = False
        return None
    
def periodic_generate(minutes, stop_event):
    while not stop_event.is_set():
        generate_result = process_image_request()
        if generate_result:
            asyncio.run(send_to_clients(generate_result))
        stop_event.wait(minutes * 60)

def refresh_periodic_generate():
    global global_config, generate_task_thread, generate_stop_event

    # If we're being called from within the generate task thread
    if threading.current_thread() is generate_task_thread:
        if global_config.generation_auto_generate:
            # Reset stop event for next execution
            generate_stop_event.clear()
            # Start new thread for next periodic execution
            generate_task_thread = threading.Thread(target=periodic_generate, 
                args=(global_config.generation_auto_generate_minutes, generate_stop_event))
            generate_task_thread.daemon = True
            generate_task_thread.start()
        return
    
    # If a thread is already running, stop it
    if generate_task_thread and generate_task_thread.is_alive():
        generate_stop_event.set()  # Signal the thread to stop
        generate_task_thread.join()  # Wait for the thread to finish

    if global_config.generation_auto_generate:
        # Reset the stop event for the new thread
        generate_stop_event.clear()
        # Create and start a new thread for periodic execution
        generate_task_thread = threading.Thread(target=periodic_generate, args=(global_config.generation_auto_generate_minutes, generate_stop_event))
        generate_task_thread.daemon = True  # Allows the program to exit when the main thread ends
        generate_task_thread.start()

def apply_updated_global_config(new_global_config: GlobalConfig):
    global global_config

    global_config = new_global_config

    try_save_global_config()
    refresh_periodic_generate()

async def websocket_handler(websocket):
    global frontend_clients
    frontend_clients.add(websocket)
    try:
        async for _ in websocket:
            pass
    finally:
        frontend_clients.remove(websocket)

async def send_to_clients(image_base64):
    global frontend_clients
    if frontend_clients:
        await asyncio.gather(*[client.send(image_base64) for client in frontend_clients])

async def start_websocket_server():
    server = await websockets.serve(websocket_handler, "localhost", 8765)
    await server.wait_closed()

def start_server():
    loop = asyncio.new_event_loop()  # Create a new event loop for the thread
    asyncio.set_event_loop(loop)  # Set the new loop as the current loop for this thread
    loop.run_until_complete(start_websocket_server())  # Run the WebSocket server

############
# FRONTEND #
############

@app.route("/")
def index():
    log(LogType.VERBOSE, "Frontend", "index()")
    return render_template("index.html")

@app.route("/config", methods=["GET", "POST"])
def config_handler():
    global global_config
    if request.method == "GET": 
        log(LogType.VERBOSE, "Frontend", "config_handler() - GET")
        return jsonify(global_config.get_as_json())
    elif request.method == "POST":
        log(LogType.VERBOSE, "Frontend", "config_handler() - POST")
        new_global_config = GlobalConfig()
        new_global_config.load_from_json(request.json)
        apply_updated_global_config(new_global_config)
        return jsonify({"status": "success", "message": "Config updated successfully!"})

@app.route("/progress", methods=["GET"])
def get_current_progress():
    global sd_connector
    log(LogType.VERBOSE, "Frontend", "get_current_progress()")
    try:
        current_progress = sd_connector.get_progress()
        return jsonify({"progress": current_progress})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/status/ollama", methods=["GET"])
def ollama_status():
    global ollama_connector
    log(LogType.VERBOSE, "Frontend", "ollama_status()")
    return jsonify({"status": "connected"}) if ollama_connector and ollama_connector.is_connected() else (jsonify({"status": "disconnected"}), 400)

@app.route("/status/sd", methods=["GET"])
def sd_status():
    global sd_connector
    log(LogType.VERBOSE, "Frontend", "sd_status()")
    return jsonify({"status": "connected"}) if sd_connector and sd_connector.is_connected() else (jsonify({"status": "disconnected"}), 400)

@app.route("/status/the_frame", methods=["GET"])
def the_frame_status():
    global the_frame_connector
    log(LogType.VERBOSE, "Frontend", "the_frame_status()")
    return jsonify({"status": "connected"}) if the_frame_connector else (jsonify({"status": "disconnected"}), 400)

@app.route("/status/mqtt", methods=["GET"])
def mqtt_status():
    global mqtt_client
    log(LogType.VERBOSE, "Frontend", "mqtt_status()")
    return jsonify({"status": "connected"}) if mqtt_client else (jsonify({"status": "disconnected"}), 400)

@app.route("/ollama/models", methods=["GET"])
def get_ollama_models():
    global ollama_connector
    log(LogType.VERBOSE, "Frontend", "get_ollama_models()")
    try:
        models = ollama_connector.query_models()
        return jsonify({"models": models})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sd/models", methods=["GET"])
def get_sd_models():
    global sd_connector
    log(LogType.VERBOSE, "Frontend", "get_sd_models()")
    try:
        models = sd_connector.query_models()
        return jsonify({"models": models})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sd/loras", methods=["GET"])
def get_sd_loras():
    global sd_connector
    log(LogType.VERBOSE, "Frontend", "get_sd_loras()")
    try:
        loras = sd_connector.query_loras()
        return jsonify({"loras": loras})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/the_frame/matte", methods=["GET", "POST"])
def the_frame_matte():
    global the_frame_connector
    if request.method == "GET":
        log(LogType.VERBOSE, "Frontend", "the_frame_matte() - GET")
        try:
            return jsonify({"mattes": [matte["matte_type"] for matte in the_frame_connector.art().get_matte_list()]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    elif request.method == "POST":
        log(LogType.VERBOSE, "Frontend", "the_frame_matte() - POST")

        if try_change_matte():
            return jsonify({"status": "success"})
        else:
            return jsonify({"error": "failed to change matte"}), 500
        
@app.route("/the_frame/photo_filter", methods=["GET", "POST"])
def the_frame_photo_filter():
    global the_frame_connector
    if request.method == "GET":
        log(LogType.VERBOSE, "Frontend", "the_frame_photo_filter() - GET")
        try:
            return jsonify({"filters": [filter["filter_id"] for filter in the_frame_connector.art().get_photo_filter_list()]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    elif request.method == "POST":
        log(LogType.VERBOSE, "Frontend", "the_frame_photo_filter() - POST")

        if try_change_photo_filter():
            return jsonify({"status": "success"})
        else:
            return jsonify({"error": "failed to change color"}), 500

@app.route("/generate", methods=["POST"])
def generate():
    log(LogType.VERBOSE, "Frontend", "generate()")
    try:
        # First, reset any periodic generate to avoid performing multiple requests at once
        refresh_periodic_generate()

        # Now generate the image, fulfilling the request
        process_image_request()
        
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/connect_backend", methods=["POST"])
def connect_backend_providers():
    global ollama_connector, sd_connector
    log(LogType.VERBOSE, "Frontend", "connect_backend_providers()")
    try:
        if not ollama_connector or not sd_connector or not ollama_connector.is_connected() or not sd_connector.is_connected():
            if try_connect(True):
                refresh_periodic_generate()
            else:
                return jsonify({"error": "One or more connections failed"}), 500
        return jsonify({"status": "success"})            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/connect_mqtt", methods=["POST"])
def connect_mqtt_provider():
    global mqtt_client
    log(LogType.VERBOSE, "Frontend", "connect_mqtt_provider()")
    try:
        if not mqtt_client:
            try_connect_mqtt(True)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/disconnect_backend", methods=["POST"])
def disconnect_backend_providers():
    log(LogType.VERBOSE, "Frontend", "disconnect_backend_providers()")
    try:
        disconnect_backend()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/disconnect_mqtt", methods=["POST"])
def disconnect_mqtt_provider():
    log(LogType.VERBOSE, "Frontend", "disconnect_mqtt_provider()")
    try:
        disconnect_mqtt()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
     
########
# MQTT #
########

def mqtt_publish_discovery():
    global global_config

    """Publish MQTT discovery payloads for Home Assistant."""
    discovery_payloads = {
        "image_trigger": {
            "topic": f"{global_config.mqtt_discovery_prefix}/text/image_generation/config",
            "payload": json.dumps({
                "name": "TFAG Trigger Image Generation",
                "command_topic": f"{global_config.mqtt_ha_prefix}/text/image_generation/set",
                "unique_id": global_config.mqtt_device_unique_ids["image_trigger"],
                "icon": "mdi:text-box-outline"
            })
        },
        "progress_sensor": {
            "topic": f"{global_config.mqtt_discovery_prefix}/sensor/current_progress/config",
            "payload": json.dumps({
                "name": "TFAG Current Progress",
                "state_topic": f"{global_config.mqtt_ha_prefix}/sensor/current_progress/state",
                "unit_of_measurement": "%",
                "device_class": "progress",
                "unique_id": global_config.mqtt_device_unique_ids["progress_sensor"]
            })
        },
        "image_sensor": {
            "topic": f"{global_config.mqtt_discovery_prefix}/sensor/generated_image/config",
            "payload": json.dumps({
                "name": "TFAG Generated Image",
                "state_topic": f"{global_config.mqtt_ha_prefix}/sensor/generated_image/state",
                "unique_id": global_config.mqtt_device_unique_ids["image_sensor"],
                "value_template": "{{ value_json.image }}"
            })
        },
        "status_sensor": {
            "topic": f"{global_config.mqtt_discovery_prefix}/sensor/current_status/config",
            "payload": json.dumps({
                "name": "TFAG Current Status",
                "state_topic": f"{global_config.mqtt_ha_prefix}/sensor/current_status/state",
                "unique_id": global_config.mqtt_device_unique_ids["status_sensor"]
            })
        }
    }

    for key, config in discovery_payloads.items():
        mqtt_client.publish(config["topic"], config["payload"], retain=True)

def mqtt_update_sensor(sensor_id, value):
    global global_config, mqtt_client
    log(LogType.VERBOSE, "MQTT", "mqtt_update_sensor()")

    if not mqtt_client:
        return
    
    """Publish state updates to the appropriate sensor."""
    topic_map = {
        "progress": f"{global_config.mqtt_ha_prefix}/sensor/current_progress/state",
        "image": f"{global_config.mqtt_ha_prefix}/sensor/generated_image/state",
        "status": f"{global_config.mqtt_ha_prefix}/sensor/current_status/state"
    }
    if sensor_id in topic_map:
        mqtt_client.publish(topic_map[sensor_id], json.dumps(value))
        log(LogType.VERBOSE, "MQTT", f"Updated sensor with ID: {sensor_id}")

def mqtt_handle_image_generation(text):
    global global_config
    log(LogType.VERBOSE, "MQTT", "mqtt_handle_image_generation()")
    global_config.mqtt_positive_command = text
    process_image_request(True)

# MQTT Callbacks
def mqtt_on_connect(client, userdata, flags, rc, properties=None):
    global global_config
    log(LogType.VERBOSE, "MQTT", "mqtt_on_connect()")
    log(LogType.INFO, "MQTT", f"Connected to broker with result code {rc}")
    client.subscribe(f"{global_config.mqtt_ha_prefix}/text/image_generation/set")
    mqtt_publish_discovery()
    mqtt_update_sensor("status", "Idle")  # Initial status
    mqtt_update_sensor("progress", {"progress": 100}) # Initial status
    log(LogType.INFO, "MQTT", "Discovery messages published and ready")

def mqtt_on_message(client, userdata, msg):
    global global_config
    log(LogType.VERBOSE, "MQTT", "mqtt_on_message()")
    log(LogType.INFO, "MQTT", f"Message received: {msg.topic} -> {msg.payload.decode()}")
    if msg.topic == f"{global_config.mqtt_ha_prefix}/text/image_generation/set":
        text = msg.payload.decode()
        threading.Thread(target=mqtt_handle_image_generation, args=(text,)).start()

########
# MAIN #
########

def initialize_app():
    # Try loading global config, if it fails, create a default one
    if(not try_load_global_config()):
        log(LogType.WARNING, "MQTT", "Failed to load global config, creating default config")
        if(not create_default_global_config()):
            log(LogType.ERROR, "MQTT", "Failed to create default config")
    # On successful load, try to connect to the services if auto_connect was enabled
    elif global_config.auto_connect:
        if try_connect(True):
            try_connect_mqtt(True)
            refresh_periodic_generate()

def create_app():
    initialize_app()
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)