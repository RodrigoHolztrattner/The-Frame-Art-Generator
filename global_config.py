import json
from typing import Optional

class GlobalConfig:
    def __init__(self):
        self.ollama_ip = "127.0.0.1"
        self.ollama_port = 11434
        self.ollama_model = None

        self.sd_ip = "127.0.0.1"
        self.sd_port = 9000
        self.sd_model = None
        self.sd_lora = None
        self.sd_lora_weight = 0.75

        self.the_frame_ip = ""
        self.the_frame_port = 8001
        self.the_frame_auto_upload = False
        self.the_frame_clear_old_art = False
        self.the_frame_force_art_mode = True
        self.the_frame_matte = None

        self.auto_connect = False

        self.image_width = 1920
        self.image_height = 1080
        self.image_upscale = 0

        self.generation_positive_instruction = ""
        self.generation_negative_prompt = ""
        self.generation_steps = 20
        self.generation_seed = -1
        self.generation_auto_generate = False
        self.generation_auto_generate_minutes = 120

        self.mqtt_enable = False
        self.mqtt_broker_ip = "127.0.0.1"
        self.mqtt_port = 1883
        self.mqtt_user = ""
        self.mqtt_password = ""

        self.mqtt_ha_prefix = "homeassistant"
        self.mqtt_client_id = "mqtt_client"
        self.mqtt_discovery_prefix = f"{self.mqtt_ha_prefix}"
        self.mqtt_device_unique_ids = {
            "image_trigger": "image_generation_text_trigger",
            "progress_sensor": "current_progress_sensor",
            "image_sensor": "generated_image_sensor",
            "status_sensor": "current_status_sensor"
        }
        self.mqtt_positive_instruction = ""
        self.mqtt_positive_command = "" # Runtime generated

    def load_from_json(self, json):
        self.ollama_ip = json.get("ollama_ip", "")
        self.ollama_port = json.get("ollama_port", 8000)
        self.ollama_model = json.get("ollama_model", None)

        self.sd_ip = json.get("sd_ip", "")
        self.sd_port = json.get("sd_port", 7860)
        self.sd_model = json.get("sd_model", None)
        self.sd_lora = json.get("sd_lora", None)
        self.sd_lora_weight = json.get("sd_lora_weight", 0.75)

        self.the_frame_ip = json.get("the_frame_ip", "")
        self.the_frame_port = json.get("the_frame_port", 8001)
        self.the_frame_auto_upload = json.get("the_frame_auto_upload", False)
        self.the_frame_clear_old_art = json.get("the_frame_clear_old_art", False)
        self.the_frame_force_art_mode = json.get("the_frame_force_art_mode", False)
        self.the_frame_matte = json.get("the_frame_matte", "none")

        self.auto_connect = json.get("auto_connect", False)

        self.image_width = json.get("image_width", 1920)
        self.image_height = json.get("image_height", 1080)
        self.image_upscale = json.get("image_upscale", 0)

        self.generation_positive_instruction = json.get("generation_positive_instruction", "")
        self.generation_negative_prompt = json.get("generation_negative_prompt", "")
        self.generation_steps = json.get("generation_steps", 20)
        self.generation_seed = json.get("generation_seed", -1)
        self.generation_auto_generate = json.get("generation_auto_generate", False)
        self.generation_auto_generate_minutes = json.get("generation_auto_generate_minutes", 120)

        self.mqtt_enable = json.get("mqtt_enable", False)
        self.mqtt_broker_ip = json.get("mqtt_broker_ip", "")
        self.mqtt_port = json.get("mqtt_port", 1883)
        self.mqtt_user = json.get("mqtt_user", "")
        self.mqtt_password = json.get("mqtt_password", "")

        self.mqtt_ha_prefix = json.get("mqtt_ha_prefix", "homeassistant")
        self.mqtt_client_id = json.get("mqtt_client_id", "mqtt_client")
        self.mqtt_discovery_prefix = json.get("mqtt_discovery_prefix", f"{self.mqtt_ha_prefix}")
        self.mqtt_device_unique_ids = json.get("mqtt_device_unique_ids", {
            "image_trigger": "image_generation_text_trigger",
            "progress_sensor": "current_progress_sensor",
            "image_sensor": "generated_image_sensor",
            "status_sensor": "current_status_sensor"
        })
        self.mqtt_positive_instruction = json.get("mqtt_positive_instruction", "")

    def get_as_json(self):
        return {
            "ollama_ip": self.ollama_ip,
            "ollama_port": self.ollama_port,
            "ollama_model": self.ollama_model,
            "sd_ip": self.sd_ip,
            "sd_port": self.sd_port,
            "sd_model": self.sd_model,
            "sd_lora": self.sd_lora,
            "sd_lora_weight": self.sd_lora_weight,
            "the_frame_ip": self.the_frame_ip,
            "the_frame_port": self.the_frame_port,
            "the_frame_auto_upload": self.the_frame_auto_upload,
            "the_frame_clear_old_art": self.the_frame_clear_old_art,
            "the_frame_force_art_mode": self.the_frame_force_art_mode,
            "the_frame_matte": self.the_frame_matte,
            "auto_connect": self.auto_connect,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "image_upscale": self.image_upscale,
            "generation_positive_instruction": self.generation_positive_instruction,
            "generation_negative_prompt": self.generation_negative_prompt,
            "generation_steps": self.generation_steps,
            "generation_seed": self.generation_seed,
            "generation_auto_generate": self.generation_auto_generate,
            "generation_auto_generate_minutes": self.generation_auto_generate_minutes,
            "mqtt_enable": self.mqtt_enable,
            "mqtt_broker_ip": self.mqtt_broker_ip,
            "mqtt_port": self.mqtt_port,
            "mqtt_user": self.mqtt_user,
            "mqtt_password": self.mqtt_password,
            "mqtt_ha_prefix": self.mqtt_ha_prefix,
            "mqtt_client_id": self.mqtt_client_id,
            "mqtt_discovery_prefix": self.mqtt_discovery_prefix,
            "mqtt_device_unique_ids": self.mqtt_device_unique_ids,
            "mqtt_positive_instruction": self.mqtt_positive_instruction
        }

    def save_as_json(self, filename):
        with open(filename, "w") as f:
            json.dump(self.get_as_json(), f)
