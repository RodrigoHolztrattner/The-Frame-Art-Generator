import webuiapi

class StableDiffusionConnector:
    def __init__(self):
        self.client = None
        self.models = []
        self.loras = []
        
    def is_connected(self):
        return self.client != None

    def connect(self, ip: str, port: str):

        if not ip or not port:
            raise ValueError("IP and port must be provided")

        try:
            self.client = webuiapi.WebUIApi(host=ip, port=port)
        except Exception as e:
            raise ConnectionError(f"Failed to initialize Stable Diffusion client: {e}")

        # Test connection by fetching models
        try:
            self.models = self.query_models()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Stable Diffusion: {e}")
        
    def refresh(self):
        if not self.client:
            raise RuntimeError("Not connected to Stable Diffusion. Please connect first.")        

        self.client.refresh_checkpoints()

    def query_models(self):
        if not self.client:
            raise RuntimeError("Not connected to Stable Diffusion. Please connect first.")

        try:
            self.models = self.client.util_get_model_names()
            # self.models = jsonify([models.dict() for models in self.client.util_get_model_names()])
            return self.models
        except Exception as e:
            raise RuntimeError(f"Failed to query models: {e}")

    def query_loras(self):
        if not self.client:
            raise RuntimeError("Not connected to Stable Diffusion. Please connect first.")

        try:
            lora_infos = self.client.get_loras()
            self.loras = [lora['name'] for lora in lora_infos]
            return self.loras
        except Exception as e:
            raise RuntimeError(f"Failed to query models: {e}")
        
    def get_progress(self):
        if not self.client:
            raise RuntimeError("Not connected to Stable Diffusion. Please connect first.")

        try:
            progress = self.client.get_progress()
            return progress
        except Exception as e:
            raise RuntimeError(f"Failed to query progress: {e}")
        
    def set_model(self, model: str):
        if not self.client:
            raise RuntimeError("Not connected to Stable Diffusion. Please connect first.")        
        
        options = {}
        options['sd_model_checkpoint'] = model
        self.client.set_options(options)

    def txt2img(self, prompt: str, negative_prompt: str, width: int, height: int, steps: int, seed: int, lora: str, sampler_name: str, cfg_scale: float, upscale: int):
        if not self.client:
            raise RuntimeError("Not connected to Stable Diffusion. Please connect first.")
        
        try:
            # Default options for high-resolution settings
            enable_hr = False
            hr_upscaler = webuiapi.HiResUpscaler.Latent
            hr_scale = 1

            # Adjust settings if upscale is active
            if int(upscale) > 0 and False:
                enable_hr = True
                hr_upscaler = webuiapi.HiResUpscaler.ESRGAN_4x
                hr_scale = upscale

            if lora and lora.lower() != "none":
                lora_factor = 0.75
                prompt = f"{prompt} <lora:{lora}:{lora_factor}>"

            print(f"Generating image with prompt: {prompt}")

            # Call the Stable Diffusion API with the appropriate settings
            sd_response = self.client.txt2img(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                seed=seed,
                sampler_name=sampler_name,
                cfg_scale=cfg_scale,
                enable_hr=enable_hr,
                hr_upscaler=hr_upscaler,
                hr_scale=hr_scale
            )
            
            return sd_response
        except Exception as e:
            raise RuntimeError(f"Failed to generate image: {e}")
        
    def upscale_image(self, image, upscale_factor: int, original_width: int, original_height: int):
        if not self.client:
            raise RuntimeError("Not connected to Stable Diffusion. Please connect first.")
        
        if int(upscale_factor) <= 0:
            return image
        
        try:
            sd_response = self.client.extra_single_image(
                image=image,
                resize_mode=0,
                show_extras_results=False,
                upscaling_resize=4,
                upscaling_resize_w=original_width * upscale_factor,
                upscaling_resize_h=original_height * upscale_factor,
                upscaling_crop=False,
                upscaler_1=webuiapi.Upscaler.ESRGAN_4x,
                #upscaler_2="None",
                extras_upscaler_2_visibility=0,
                upscale_first=False
            )
            
            return sd_response
        except Exception as e:
            raise RuntimeError(f"Failed to upscale image: {e}")