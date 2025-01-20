/////////////////////
// HTML REFERENCES //
/////////////////////

// Sections
const connectionSection = document.getElementById('connection-section'); // Section
const theFrameSection = document.getElementById('the-frame-section'); // Section
const mqttSection = document.getElementById('mqtt-section'); // Section
const settingsSection = document.getElementById('settings-section'); // Section
const previewSection = document.getElementById('preview-section'); // Section

// Widgets for "connection-section"
const ollamaIPInput = document.getElementById('ollama-ip'); // Text
const ollamaPortInput = document.getElementById('ollama-port'); // Text
const ollamaStatusIndicator = document.getElementById('ollama-status'); // Status indicator
const sdIPInput = document.getElementById('sd-ip'); // Text
const sdPortInput = document.getElementById('sd-port'); // Text
const sdStatusIndicator = document.getElementById('sd-status'); // Status indicator
const theFrameIPInput = document.getElementById('the-frame-ip'); // Text
const theFramePortInput = document.getElementById('the-frame-port'); // Text
const theFrameStatusIndicator = document.getElementById('the-frame-status'); // Status indicator
const autoConnectCheckbox = document.getElementById('auto-connect'); // Checkbox
const connectBtn = document.getElementById('connect-btn'); // Button

// Widgets for "the-frame-section"
const theFrameAutoUploadCheckbox = document.getElementById('the-frame-auto-upload'); // Checkbox
const theFramecloarOldArtCheckbox = document.getElementById('the-frame-clear-old-art'); // Checkbox
const theFrameForceArtModeCheckbox = document.getElementById('the-frame-force-art-mode'); // Checkbox
const theFrameMatteSelect = document.getElementById('the-frame-matte'); // Select
const theFramePhotoFilterSelect = document.getElementById('the-frame-photo-filter'); // Select
const theFrameColorOptionsContainer = document.getElementById('the-frame-color-options'); // Container

// Widgets for "mqtt-section"
const mqttEnableCheckbox = document.getElementById('mqtt-enable'); // Checkbox
const mqttBrokerInput = document.getElementById('mqtt-broker-ip'); // Text
const mqttStatusIndicator = document.getElementById('mqtt-status'); // Status indicator
const mqttPortInput = document.getElementById('mqtt-port'); // Text
const mqttUserInput = document.getElementById('mqtt-user'); // Text
const mqttPasswordInput = document.getElementById('mqtt-password'); // Text
const mqttHAPrefixInput = document.getElementById('mqtt-ha-prefix'); // Text
const mqttClientIDInput = document.getElementById('mqtt-client-id'); // Text
const mqttDiscoveryPrefixInput = document.getElementById('mqtt-discovery-prefix'); // Text
const mqttPositivePromptInstructionInput = document.getElementById('mqtt-positive-prompt-instruction'); // Text
const mqttConnectBtn = document.getElementById('mqtt-connect-btn'); // Button

// Widgets for "settings-section"
const ollamaModelSelect = document.getElementById('ollama-model'); // Select
const sdModelSelect = document.getElementById('sd-model'); // Select
const sdLoraSelect = document.getElementById('sd-lora'); // Select
const sdLoraWeight = document.getElementById('sd-lora-weight'); // Float
const imageWidthInput = document.getElementById('width'); // Number
const imageHeightInput = document.getElementById('height'); // Number
const generationStepsInput = document.getElementById('steps'); // Number
const generationSeedInput = document.getElementById('seed'); // Number
const upscaleSelect = document.getElementById('upscale'); // Select
const positivePromptInstructionInput = document.getElementById('positive-prompt-instruction'); // Text
const negativePromptInput = document.getElementById('negative-prompt'); // Text
const automaticGenerateCheckbox = document.getElementById('automatic-generation'); // Checkbox
const automaticGenerateMinutesInput = document.getElementById('automatic-generation-minutes'); // Number
const generateBtn = document.getElementById('generate-btn'); // Button

// Widgets for "preview-section"
const generatedImage = document.getElementById('generated-image'); // Image

/////////////////////////////////////
// WEBSOCKET (BACKEND -> FRONTEND) //
/////////////////////////////////////

const socket = new WebSocket('ws://localhost:8765');

socket.onmessage = (event) => {
    const image = event.data;
    previewSection.style.display = 'none';

    if (image) {
        // Display the generated image in the previewSection
        previewSection.style.display = 'block';
        generatedImage.src = `data:image/png;base64,${image}`;
    }
};

socket.onerror = (error) => {
    console.error('WebSocket error:', error);
};

socket.onclose = () => {
    console.log('WebSocket connection closed');
};

///////////////
// FUNCTIONS //
///////////////

async function refreshVisibility() {

    const backendStatus = await isBackendConnected();
    const mqttStatus = await isMQTTConnected();

    if (backendStatus) {
        settingsSection.style.display = 'block';
        theFrameSection.style.display = 'block';
        mqttSection.style.display = 'block';
        previewSection.style.display = generatedImage.src ? 'block' : 'none';

        connectBtn.textContent = "Disconnect";
    }
    else {
        settingsSection.style.display = 'none';
        theFrameSection.style.display = 'none';
        mqttSection.style.display = 'none';
        previewSection.style.display = 'none';

        connectBtn.textContent = "Connect";
    }

    if(mqttStatus) {
        mqttConnectBtn.textContent = "Disconnect";
    }
    else {
        mqttConnectBtn.textContent = "Connect";
    }

    // Enable or disable the manual generate button depending if auto-generate is selected
    generateBtn.disabled = automaticGenerateCheckbox.checked

    // Enable or disable MQTT widgets depending on the checkbox
    mqttBrokerInput.disabled = !mqttEnableCheckbox.checked;
    mqttPortInput.disabled = !mqttEnableCheckbox.checked;
    mqttUserInput.disabled = !mqttEnableCheckbox.checked;
    mqttPasswordInput.disabled = !mqttEnableCheckbox.checked;
    mqttHAPrefixInput.disabled = !mqttEnableCheckbox.checked;
    mqttClientIDInput.disabled = !mqttEnableCheckbox.checked;
    mqttDiscoveryPrefixInput.disabled = !mqttEnableCheckbox.checked;
    mqttPositivePromptInstructionInput.disabled = !mqttEnableCheckbox.checked;

    const ollamaStatus = await isOllamaConnected();
    const sdStatus = await isSDConnected();
    const theFrameStatus = await isTheFrameConnected();
    
    ollamaStatusIndicator.textContent = ollamaStatus ? 'Connected' : 'Disconnected';
    ollamaStatusIndicator.className = ollamaStatus ? 'status-indicator connected' : 'status-indicator disconnected'; 
    sdStatusIndicator.textContent = sdStatus ? 'Connected' : 'Disconnected';
    sdStatusIndicator.className = sdStatus ? 'status-indicator connected' : 'status-indicator disconnected';
    theFrameStatusIndicator.textContent = theFrameStatus ? 'Connected' : 'Disconnected';
    theFrameStatusIndicator.className = theFrameStatus ? 'status-indicator connected' : 'status-indicator disconnected';
    mqttStatusIndicator.textContent = mqttStatus ? 'Connected' : 'Disconnected';
    mqttStatusIndicator.className = mqttStatus ? 'status-indicator connected' : 'status-indicator disconnected';

    // Enable/disable connection settings depending if a connection was made
    ollamaIPInput.disabled = backendStatus;
    ollamaPortInput.disabled = backendStatus;
    sdIPInput.disabled = backendStatus;
    sdPortInput.disabled = backendStatus;
    theFrameIPInput.disabled = backendStatus;
    theFramePortInput.disabled = backendStatus;

    // Enable/disable mqtt settings depending if a connection was made
    mqttBrokerInput.disabled = mqttStatus;
    mqttPortInput.disabled = mqttStatus;
    mqttUserInput.disabled = mqttStatus;
    mqttPasswordInput.disabled = mqttStatus;
    mqttHAPrefixInput.disabled = mqttStatus;
    mqttClientIDInput.disabled = mqttStatus;
    mqttDiscoveryPrefixInput.disabled = mqttStatus;
    mqttPositivePromptInstructionInput.disabled = mqttStatus;

    automaticGenerateMinutesInput.disabled = automaticGenerateCheckbox.checked;
}

async function initializeFromBackendConfig() {
    try {
        const response = await fetch('/config', { method: 'GET' });

        if (!response.ok) {
            throw new Error('Failed to fetch initial configuration');
        }

        const config = await response.json();

        // Populate inputs with the received config
        ollamaIPInput.value = config.ollama_ip;
        ollamaPortInput.value = config.ollama_port;
        sdIPInput.value = config.sd_ip;
        sdPortInput.value = config.sd_port;
        theFrameIPInput.value = config.the_frame_ip;
        theFramePortInput.value = config.the_frame_port;
        autoConnectCheckbox.checked = config.auto_connect;

        theFrameAutoUploadCheckbox.checked = config.the_frame_auto_upload;
        theFramecloarOldArtCheckbox.checked = config.the_frame_clear_old_art;
        theFrameForceArtModeCheckbox.checked = config.the_frame_force_art_mode;
        theFrameMatteSelect.value = config.the_frame_matte;

        mqttEnableCheckbox.checked = config.mqtt_enable;
        mqttBrokerInput.value = config.mqtt_broker_ip;
        mqttPortInput.value = config.mqtt_port;
        mqttUserInput.value = config.mqtt_user;
        mqttPasswordInput.value = config.mqtt_password;
        mqttHAPrefixInput.value = config.mqtt_ha_prefix;
        mqttClientIDInput.value = config.mqtt_client_id;
        mqttDiscoveryPrefixInput.value = config.mqtt_discovery_prefix;
        mqttPositivePromptInstructionInput.value = config.mqtt_positive_instruction;

        ollamaModelSelect.value = config.ollama_model;
        sdModelSelect.value = config.sd_model;
        sdLoraSelect.value = config.sd_lora;
        sdLoraWeight.value = config.sd_lora_weight;
        imageWidthInput.value = config.image_width;
        imageHeightInput.value = config.image_height;
        generationStepsInput.value = config.generation_steps;
        generationSeedInput.value = config.generation_seed;
        upscaleSelect.value = config.image_upscale;
        positivePromptInstructionInput.value = config.generation_positive_instruction;
        negativePromptInput.value = config.generation_negative_prompt;
        automaticGenerateCheckbox.checked = config.generation_auto_generate;
        automaticGenerateMinutesInput.value = config.generation_auto_generate_minutes;

        // If ips are set and auto-start is selected, validate connections and fetch models
        if (await isBackendConnected()) {
            await fetchModels();
            await fetchMatte();
            await fetchPhotoFilter();

            // Set these values again in case fetchModels() just added their entries into the selector widgets
            ollamaModelSelect.value = config.ollama_model;
            sdModelSelect.value = config.sd_model;
            sdLoraSelect.value = config.sd_lora;

            // Set these values again in case fetchMatte() just added their entries into the selector widgets
            theFrameMatteSelect.value = config.the_frame_matte;
            // theFramePhotoFilterSelect = config.the_frame_photo_filter;
            // theFrameColorOptionsContainer TODO: Need to convert list into checkbox selection
        }

        await refreshVisibility();

    } catch (error) {
        console.error('Error initializing configuration:', error);
        alert('Failed to load initial configuration. Check console for details.');
    }
}

async function updateBackendConfig() {

    const configData = {
        ollama_ip: ollamaIPInput.value,
        ollama_port: parseInt(ollamaPortInput.value),
        sd_ip: sdIPInput.value,
        sd_port: parseInt(sdPortInput.value),
        the_frame_ip: theFrameIPInput.value,
        the_frame_port: parseInt(theFramePortInput.value),
        auto_connect: autoConnectCheckbox.checked,

        the_frame_auto_upload: theFrameAutoUploadCheckbox.checked,
        the_frame_clear_old_art: theFramecloarOldArtCheckbox.checked,
        the_frame_force_art_mode: theFrameForceArtModeCheckbox.checked,
        the_frame_matte: theFrameMatteSelect.value,
        // the_frame_photo_filter: theFramePhotoFilterSelect.value,
        // the_frame_color_list: await getSelectedColorOptions(),

        mqtt_enable: mqttEnableCheckbox.checked,
        mqtt_broker_ip: mqttBrokerInput.value,
        mqtt_port: parseInt(mqttPortInput.value),
        mqtt_user: mqttUserInput.value,
        mqtt_password: mqttPasswordInput.value,
        mqtt_ha_prefix: mqttHAPrefixInput.value,
        mqtt_client_id: mqttClientIDInput.value,
        mqtt_discovery_prefix: mqttDiscoveryPrefixInput.value,
        mqtt_positive_instruction: mqttPositivePromptInstructionInput.value,

        ollama_model: ollamaModelSelect.value,
        sd_model: sdModelSelect.value,
        sd_lora: sdLoraSelect.value,
        sd_lora_weight: parseFloat(sdLoraWeight.value),
        image_width: parseInt(imageWidthInput.value),
        image_height: parseInt(imageHeightInput.value),
        generation_steps: parseInt(generationStepsInput.value),
        generation_seed: parseInt(generationSeedInput.value),
        image_upscale: parseInt(upscaleSelect.value),
        generation_positive_instruction: positivePromptInstructionInput.value,
        generation_negative_prompt: negativePromptInput.value,
        generation_auto_generate: automaticGenerateCheckbox.checked,
        generation_auto_generate_minutes: parseInt(automaticGenerateMinutesInput.value)
    };

    try {
        const response = await fetch('/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(configData),
        });

        if (!response.ok) {
            throw new Error('Failed to update configuration');
        }

        await refreshVisibility();
        
    } catch (error) {
        console.error('Error updating configuration:', error);
        alert('Failed to update configuration. Check console for details.');
    }
}

const fetchModels = async () => {
    try {
        const ollamaModelsResponse = await fetch('/ollama/models');
        const ollamaModels = await ollamaModelsResponse.json();
        ollamaModelSelect.innerHTML = ollamaModels.models?.length
            ? ollamaModels.models.map(model => `<option value="${model}">${model}</option>`).join('')
            : `<option value="">No models available</option>`;

        const sdModelsResponse = await fetch('/sd/models');
        const sdModels = await sdModelsResponse.json();
        sdModelSelect.innerHTML = sdModels.models?.length
            ? sdModels.models.map(model => `<option value="${model}">${model}</option>`).join('')
            : `<option value="">No models available</option>`;

        const sdLorasResponse = await fetch('/sd/loras');
        const sdLoras = await sdLorasResponse.json();
        sdLoraSelect.innerHTML = `<option value="">none</option>` + 
            (sdLoras.loras?.length 
                ? sdLoras.loras.map(lora => `<option value="${lora}">${lora}</option>`).join('')
                : '');

    } catch (error) {
        alert('Error fetching models/loras: ' + error.message);
    }
};

const fetchMatte = async () => {

    if (!await isTheFrameConnected()) {
        return;
    }

    try {
        const response = await fetch('/the_frame/matte');
        const matte = await response.json();
        
        // Filter out 'none' from fetched mattes
        const filteredMattes = matte.mattes?.filter(m => m !== 'none') || [];
        
        // Regular matte select
        theFrameMatteSelect.innerHTML = `<option value="none">none</option>` +
            filteredMattes.map(matte => `<option value="${matte}">${matte}</option>`).join('');

    } catch (error) {
        alert('Error fetching mattes: ' + error.message);
    }
};

async function getSelectedColorOptions() {
    const checkboxes = document.querySelectorAll('#the-frame-color-options input[type="checkbox"]:checked');
    const selectedColors = Array.from(checkboxes).map(cb => cb.value);
    
    return selectedColors;

    // Usage example:
    // const selectedColors = getSelectedColorOptions();
}

const fetchPhotoFilter = async () => {

    if (!await isTheFrameConnected()) {
        return;
    }

    try {
        const response = await fetch('/the_frame/photo_filter');
        const filter = await response.json();

        // Filter out 'none' from photo filters
        const filteredFilters = filter.filters?.filter(m => m !== 'none') || [];
        
        theFramePhotoFilterSelect.innerHTML = `<option value="none">none</option>` +
            `<option value="random">random</option>` +
            filteredFilters.map(filter => `<option value="${filter}">${filter}</option>`).join('');

    } catch (error) {
        alert('Error fetching filters: ' + error.message);
    }
};

const isOllamaConnected = async () => {
    try {
        const response = await fetch('/status/ollama');
        return response.ok;
    } catch (error) {
        return false;
    }
};

const isSDConnected = async () => {
    try {
        const response = await fetch('/status/sd');
        return response.ok;
    } catch (error) {
        return false;
    }
};

const isTheFrameConnected = async () => {
    try {
        const response = await fetch('/status/the_frame');
        return response.ok;
    } catch (error) {
        return false;
    }
};

const isMQTTConnected = async () => {
    try {
        const response = await fetch('/status/mqtt');
        return response.ok;
    } catch (error) {
        return false;
    }
};

const isBackendConnected = async () => {
    try {
        return await isOllamaConnected() && await isSDConnected();
    } catch (error) {
        alert('Error checking connections: ' + error.message);
        return false;
    }
};

////////////////////////
// CALLBACKS / EVENTS //
////////////////////////

document.addEventListener('DOMContentLoaded', async () => {initializeFromBackendConfig()});

// If any of the connection settings changes, disconnect backend and update its configuration
[ollamaIPInput, ollamaPortInput, sdIPInput, sdPortInput, theFrameIPInput, theFramePortInput
].forEach((element) => {
    element.addEventListener('input', async () => {
        await fetch('/disconnect_backend', { method: 'POST' });
        await updateBackendConfig()
    });
});

// If the MQTT settings change, disconnect MQTT and update its configuration
[mqttBrokerInput, mqttPortInput, mqttUserInput, mqttPasswordInput,
    mqttHAPrefixInput, mqttClientIDInput, mqttDiscoveryPrefixInput, mqttPositivePromptInstructionInput
].forEach((element) => {
    element.addEventListener('input', async () => {
        await fetch('/disconnect_mqtt', { method: 'POST' });
        await updateBackendConfig()
    });
});

// If the auto connect checkbox or mqtt enabled changes, be sure to inform the backend
[autoConnectCheckbox, theFrameAutoUploadCheckbox, theFramecloarOldArtCheckbox, theFrameForceArtModeCheckbox, mqttEnableCheckbox
].forEach((element) => {
    element.addEventListener('input', async () => {
        await updateBackendConfig()
    });
});

// If any generation settings change, stop automatic generation and update the backend configuration
[ollamaModelSelect, sdModelSelect, sdLoraSelect, sdLoraWeight, imageWidthInput, imageHeightInput,
    generationStepsInput, generationSeedInput, upscaleSelect, positivePromptInstructionInput, 
    negativePromptInput, automaticGenerateMinutesInput
].forEach((element) => {
    element.addEventListener('input', async () => {
        automaticGenerateCheckbox.checked = false;
        await updateBackendConfig()
    });
});

// If the auto connect checkbox or mqtt enabled changes, be sure to inform the backend
[automaticGenerateCheckbox].forEach((element) => {
    element.addEventListener('input', async () => {
        await updateBackendConfig()
    });
});


// If any of the portrait options were changed, update the backend configuration
[theFrameMatteSelect].forEach((element) => {
    element.addEventListener('input', async () => {
        await updateBackendConfig()
        await fetch('/the_frame/matte', { method: 'POST' });
    });
});

// If the color selection was changed, reflect the backend
[theFrameColorOptionsContainer].forEach((element) => {
    element.addEventListener('input', async () => {
        await updateBackendConfig()
    });
});

connectBtn.addEventListener('click', async () => {
    try {
        if (await isBackendConnected()) {
            await fetch('/disconnect_backend', { method: 'POST' });
            await initializeFromBackendConfig();
        }
        else {
            await updateBackendConfig();

            await fetch('/connect_backend', { method: 'POST' });

            if(await isBackendConnected()) {
                await fetchModels();
                await fetchMatte();
                await fetchPhotoFilter();
            }

            await refreshVisibility();
        }

    } catch (err) {
        alert('Failed to connect: ' + err.message);
    }
});

mqttConnectBtn.addEventListener('click', async () => {
    try {
        if (await isMQTTConnected()) {
            await fetch('/disconnect_mqtt', { method: 'POST' });
            await initializeFromBackendConfig();
        }
        else {
            await updateBackendConfig();

            await fetch('/connect_mqtt', { method: 'POST' });

            await refreshVisibility();
        }

    } catch (err) {
        alert('Failed to connect: ' + err.message);
    }
});

generateBtn.addEventListener('click', async () => {
    try {
        // Make the API call to the server
        await fetch('/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

    } catch (error) {
        alert('Error: ' + error.message);
    }
});