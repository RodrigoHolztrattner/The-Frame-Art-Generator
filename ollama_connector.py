from ollama import Client, ResponseError, ListResponse


class OllamaConnector:
    def __init__(self):
        self.client = None
        self.models = []

    def is_connected(self):
        return self.client != None

    def connect(self, ip: str, port: str):
        """
        Establish connection to the Ollama instance.

        :param ip: IP address of the Ollama instance
        :param port: Port number of the Ollama instance
        :raises ValueError: If IP or port is invalid
        :raises ConnectionError: If connection fails
        """
        if not ip or not port:
            raise ValueError("IP and port must be provided")

        try:
            self.client = Client(host=f"http://{ip}:{port}")
        except Exception as e:
            raise ConnectionError(f"Failed to initialize Ollama client: {e}")

        # Test connection by fetching models
        try:
            self.models = self.query_models()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Ollama: {e}")
        
    def refresh(self):
        if not self.client:
            raise RuntimeError("Not connected to Ollama. Please connect first.")        

        # TODO

    def query_models(self):
        """
        Fetch a list of available models from the Ollama instance.

        :return: List of model names
        :raises RuntimeError: If fetching models fails
        """
        if not self.client:
            raise RuntimeError("Not connected to Ollama. Please connect first.")

        try:
            response: ListResponse = self.client.list()
            self.models = [model.model for model in response.models]
            return self.models
        except ResponseError as e:
            raise RuntimeError(f"Error querying models: {e.error}")
        except Exception as e:
            raise RuntimeError(f"Failed to query models: {e}")

    def send_message(self, model: str, message: str):
        """
        Send a message to the specified model.

        :param model: Model name
        :param message: User input
        :return: Model response
        :raises RuntimeError: If the message cannot be sent
        """
        if not self.client:
            raise RuntimeError("Not connected to Ollama. Please connect first.")
        if model not in self.models:
            raise ValueError(f"Model '{model}' is not available. Query models first.")

        try:
            """
            response = self.client.chat(
                model=model,
                messages=[{"role": "user", "content": message}],
                keep_alive='0'
            )
            return response.message.content
            """

            response = self.client.generate(
                model=model,
                prompt=message,
                keep_alive='0'
            )
            return response.response
        
        except ResponseError as e:
            raise RuntimeError(f"Error sending message: {e.error}")
        except Exception as e:
            raise RuntimeError(f"Failed to send message: {e}")