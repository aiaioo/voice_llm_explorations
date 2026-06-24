/**
 * Main application script for Gemini Live API Demo
 * Handles UI interactions, media streaming, and communication with Gemini API
 */

// Global state
const state = {
  client: null,
  audio: { streamer: null, player: null, isStreaming: false },
  video: { streamer: null, isStreaming: false },
  screen: { capture: null, isSharing: false },
  user: { speaking: false, animationId: null },
  ai: { speaking: false, animationId: null },
};

// DOM element cache
const elements = {};

// Initialize DOM references
function initDOM() {
  const ids = [
    //"model",
    //"systemInstructions",
    //"enableInputTranscription",
    //"enableOutputTranscription",
    //"enableGrounding",
    //"enableAlertTool",
    //"enableCssStyleTool",
    //"voiceSelect",
    //"temperature",
    //"temperatureValue",
    //"disableActivityDetection",
    //"silenceDuration",
    //"prefixPadding",
    //"endSpeechSensitivity",
    //"startSpeechSensitivity",
    //"activityHandling",
    "connectionStatus",
    "startAudioBtn",
    "startVideoBtn",
    "startScreenBtn",
    "videoPreview",
    "micSelect",
    "cameraSelect",
    "volume",
    "volumeValue",
    "chatContainer",
    //"chatInput",
    //"sendBtn",
    "debugInfo",
    "setupJsonSection",
    "setupJsonDisplay",
    "userSpeakingContainer",
    "userAudioViz",
    "aiSpeakingContainer",
    "aiAudioViz",
  ];

  ids.forEach((id) => {
    elements[id] = document.getElementById(id);
  });
}

// Populate media device selectors
async function populateMediaDevices() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();

    // Clear existing options
    elements.micSelect.innerHTML =
      '<option value="">Default Microphone</option>';
    elements.cameraSelect.innerHTML =
      '<option value="">Default Camera</option>';

    // Add audio input devices
    devices
      .filter((device) => device.kind === "audioinput")
      .forEach((device) => {
        const option = document.createElement("option");
        option.value = device.deviceId;
        option.textContent =
          device.label || `Microphone ${device.deviceId.substr(0, 8)}`;
        elements.micSelect.appendChild(option);
      });

    // Add video input devices
    devices
      .filter((device) => device.kind === "videoinput")
      .forEach((device) => {
        const option = document.createElement("option");
        option.value = device.deviceId;
        option.textContent =
          device.label || `Camera ${device.deviceId.substr(0, 8)}`;
        elements.cameraSelect.appendChild(option);
      });
  } catch (error) {
    console.error("Error enumerating devices:", error);
  }
}

// Create reusable message element
function createMessage(text, className = "") {
  const div = document.createElement("div");
  div.textContent = text;
  if (className) div.className = className;
  return div;
}

// Update status display
function updateStatus(elementId, text) {
  if (elements[elementId]) {
    elements[elementId].textContent = text;
  }
}

// Connect to Gemini
async function connect() {
  try {
    updateStatus("connectionStatus", "Fetching ephemeral token...");

  //elements["model"] = 'gemini-3.1-flash-live-preview';
  //elements["systemInstructions"] = 'You are a helpful assistant. Be concise and friendly.';
  //elements["enableInputTranscription"] = true;
  //elements["enableOutputTranscription"] = false;
  //elements["enableGrounding"] = false;
  //elements["enableAlertTool"] = false;
  //elements["enableCssStyleTool"] = false;
  //elements["voiceSelect"] = "Puck";
  //elements["temperature"] = "1.0";
  //elements["temperatureValue"] = "1.0";
  //elements["disableActivityDetection"] = false;
  //elements["silenceDuration"] = "500";
  //elements["prefixPadding"] = "500";
  //elements["endSpeechSensitivity"] = "END_SENSITIVITY_UNSPECIFIED";
  //elements["startSpeechSensitivity"] = "START_SENSITIVITY_UNSPECIFIED";
  //elements["activityHandling"] = "ACTIVITY_HANDLING_UNSPECIFIED";

    // Fetch token from backend
    const response = await fetch("/api/token", { method: "POST" });
    if (!response.ok) {
      throw new Error(`Failed to fetch token: ${response.statusText}`);
    }
    const { token } = await response.json();
    const model = 'gemini-3.1-flash-live-preview'; //elements.model.value;

    updateStatus("connectionStatus", "Connecting...");

    // Create GeminiLiveAPI instance
    state.client = new GeminiLiveAPI(token, model);

    // Configure settings
    state.client.systemInstructions = 'You are a helpful assistant. Be concise and friendly.'; //elements.systemInstructions.value;
    state.client.inputAudioTranscription = true;
      //elements.enableInputTranscription.checked;
    state.client.outputAudioTranscription = true;
      //elements.enableOutputTranscription.checked;
    state.client.googleGrounding = false; //elements.enableGrounding.checked;
    state.client.responseModalities = ["AUDIO"];
    state.client.voiceName = 'Puck'; //elements.voiceSelect.value;
    state.client.temperature = 1.0; //parseFloat(elements.temperature.value);

    // Set automatic activity detection configuration
    state.client.automaticActivityDetection = {
      disabled: false, //elements.disableActivityDetection.checked,
      silence_duration_ms: 500, // parseInt(elements.silenceDuration.value),
      prefix_padding_ms: 500, // parseInt(elements.prefixPadding.value),
      end_of_speech_sensitivity: "END_SENSITIVITY_UNSPECIFIED", //elements.endSpeechSensitivity.value,
      start_of_speech_sensitivity: "START_SENSITIVITY_UNSPECIFIED", //elements.startSpeechSensitivity.value,
    };

    // Set activity handling
    state.client.activityHandling = "ACTIVITY_HANDLING_UNSPECIFIED"; //elements.activityHandling.value;

    // Add custom tools only if Google grounding is disabled
    const isGroundingEnabled = false; //elements.enableGrounding.checked;

    if (!isGroundingEnabled) {
      // Add alert tool if enabled
      //if (elements.enableAlertTool.checked) {
      //  const alertTool = new ShowAlertTool();
      //  state.client.addFunction(alertTool);
      //  console.log("✅ Alert tool enabled");
      //}

      // Add CSS style tool if enabled
      //if (elements.enableCssStyleTool.checked) {
      //  const cssStyleTool = new AddCSSStyleTool();
      //  state.client.addFunction(cssStyleTool);
      //  console.log("✅ CSS style tool enabled");
      //}
    } else {
      console.log(
        "⚠️ Custom tools disabled due to Google grounding being enabled"
      );
    }

    // Set callbacks
    state.client.onReceiveResponse = handleMessage;
    state.client.onError = handleError;
    state.client.onOpen = handleOpen;
    state.client.onClose = handleClose;

    await state.client.connect();

    // Initialize media handlers
    state.audio.streamer = new AudioStreamer(state.client);
    state.video.streamer = new VideoStreamer(state.client);
    state.screen.capture = new ScreenCapture(state.client);
    state.audio.player = new AudioPlayer();
    await state.audio.player.init();

    updateStatus("debugInfo", "Connected successfully");
  } catch (error) {
    console.error("Connection failed:", error);
    updateStatus("connectionStatus", "Connection failed: " + error.message);
    updateStatus("debugInfo", "Error: " + error.message);
  }
}

// Disconnect
function disconnect() {
  if (state.client && state.client.webSocket) {
    state.client.webSocket.close();
    state.client = null;
  }

  // Stop all streams
  if (state.audio.streamer) state.audio.streamer.stop();
  if (state.video.streamer) state.video.streamer.stop();
  if (state.screen.capture) state.screen.capture.stop();

  // Reset states
  state.audio.isStreaming = false;
  state.video.isStreaming = false;
  state.screen.isSharing = false;

  // Update UI
  updateStatus("connectionStatus", "Disconnected");

  elements.startAudioBtn.classList.remove("active");
  elements.startAudioBtn.title = "Start microphone";
  elements.startVideoBtn.classList.remove("active");
  elements.startVideoBtn.title = "Start camera";
  elements.startScreenBtn.classList.remove("active");
  elements.startScreenBtn.title = "Share screen";

  elements.videoPreview.hidden = true;
  elements.videoPreview.srcObject = null;
}

// Input audio visualization (microphone → Gemini)
function startInputVisualization() {
  if (state.user.speaking) return;
  state.user.speaking = true;
  elements.userSpeakingContainer.style.display = "flex";

  const canvas = elements.userAudioViz;
  const ctx = canvas.getContext("2d");
  const analyser = state.audio.streamer && state.audio.streamer.analyserNode;
  if (!analyser) return;

  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  const barCount = 32;
  const barSpacing = 2;
  const barWidth = (canvas.width - barSpacing * (barCount - 1)) / barCount;

  function draw() {
    state.user.animationId = requestAnimationFrame(draw);
    analyser.getByteFrequencyData(dataArray);

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let i = 0; i < barCount; i++) {
      const binIndex = Math.floor((i / barCount) * (bufferLength * 0.75));
      const amplitude = dataArray[binIndex] / 255;
      const barHeight = Math.max(3, amplitude * canvas.height);

      const x = i * (barWidth + barSpacing);
      const y = (canvas.height - barHeight) / 2;

      // Green gradient based on amplitude
      const green = Math.round(157 + amplitude * 55);
      const alpha = 0.5 + amplitude * 0.5;
      ctx.fillStyle = `rgba(15, ${green}, 88, ${alpha})`;
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, barHeight, 2);
      ctx.fill();
    }
  }

  draw();
}

function stopInputVisualization() {
  if (state.user.animationId) {
    cancelAnimationFrame(state.user.animationId);
    state.user.animationId = null;
  }
  state.user.speaking = false;
  elements.userSpeakingContainer.style.display = "none";

  const canvas = elements.userAudioViz;
  if (canvas) {
    canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
  }
}

// Output audio visualization (Gemini → speaker)
function startAudioVisualization() {
  if (state.ai.speaking) return;
  state.ai.speaking = true;
  elements.aiSpeakingContainer.style.display = "flex";

  const canvas = elements.aiAudioViz;
  const ctx = canvas.getContext("2d");
  const analyser = state.audio.player && state.audio.player.analyserNode;
  if (!analyser) return;

  const bufferLength = analyser.frequencyBinCount; // fftSize / 2 = 128
  const dataArray = new Uint8Array(bufferLength);
  const barCount = 32;
  const barSpacing = 2;
  const barWidth = (canvas.width - barSpacing * (barCount - 1)) / barCount;

  function draw() {
    state.ai.animationId = requestAnimationFrame(draw);
    analyser.getByteFrequencyData(dataArray);

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let i = 0; i < barCount; i++) {
      // Sample frequency bins spread across the useful range (skip the top bins)
      const binIndex = Math.floor((i / barCount) * (bufferLength * 0.75));
      const amplitude = dataArray[binIndex] / 255;
      const barHeight = Math.max(3, amplitude * canvas.height);

      const x = i * (barWidth + barSpacing);
      const y = (canvas.height - barHeight) / 2;

      // Blue gradient based on amplitude
      const blue = Math.round(200 + amplitude * 55);
      const alpha = 0.5 + amplitude * 0.5;
      ctx.fillStyle = `rgba(66, 133, ${blue}, ${alpha})`;
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, barHeight, 2);
      ctx.fill();
    }
  }

  draw();
}

function stopAudioVisualization() {
  if (state.ai.animationId) {
    cancelAnimationFrame(state.ai.animationId);
    state.ai.animationId = null;
  }
  state.ai.speaking = false;
  elements.aiSpeakingContainer.style.display = "none";

  // Clear canvas
  const canvas = elements.aiAudioViz;
  if (canvas) {
    canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
  }
}

// Handle messages
function handleMessage(message) {
  updateStatus("debugInfo", `Message: ${message.type}`);

  switch (message.type) {
    case MultimodalLiveResponseType.TEXT:
      addMessage(message.data, "assistant");
      break;

    case MultimodalLiveResponseType.AUDIO:
      if (state.audio.player) {
        state.audio.player.play(message.data);
        startAudioVisualization();
      }
      break;

    case MultimodalLiveResponseType.INPUT_TRANSCRIPTION:
      console.log("Input transcription:", message.data);
      if (!message.data.finished) {
        addMessage(message.data.text, "user-transcript", (append = true));
      }
      break;

    case MultimodalLiveResponseType.OUTPUT_TRANSCRIPTION:
      console.log("Output transcription:", message.data);
      if (!message.data.finished) {
        addMessage(message.data.text, "assistant", (append = true));
      }
      break;

    case MultimodalLiveResponseType.SETUP_COMPLETE:
      console.log("Setup complete:", message.data);
      addMessage("Ready!", "system");

      // Display the setup JSON
      //if (state.client && state.client.lastSetupMessage) {
      //  elements.setupJsonDisplay.textContent = JSON.stringify(
      //    state.client.lastSetupMessage,
      //    null,
      //    2
      //  );
      //  elements.setupJsonSection.style.display = "block";
      //}
      break;

    case MultimodalLiveResponseType.TOOL_CALL:
      console.log("🛠️ Tool call received: ", message.data);
      const functionCalls = message.data.functionCalls;
      const functionResponses = [];
      for (let index = 0; index < functionCalls.length; index++) {
        const functionCall = functionCalls[index];
        const functionName = functionCall.name;
        const functionCallId = functionCall.id;
        const parameters = functionCall.args;
        console.log(
          `Calling function ${functionName} with parameters: ${JSON.stringify(
            parameters
          )}`
        );
        let result;
        try {
          result = state.client.callFunction(functionName, parameters);
          functionResponses.push({
            id: functionCallId,
            name: functionName,
            response: { result: result ?? "ok" },
          });
        } catch (err) {
          console.error(`Error calling function ${functionName}:`, err);
          functionResponses.push({
            id: functionCallId,
            name: functionName,
            response: { error: err.message },
          });
        }
      }
      // Send all function responses back to the API
      state.client.sendToolResponse(functionResponses);
      break;

    case MultimodalLiveResponseType.TURN_COMPLETE:
      console.log("Turn complete:", message.data);
      updateStatus("debugInfo", "Turn complete");
      stopAudioVisualization();
      break;

    case MultimodalLiveResponseType.INTERRUPTED:
      console.log("Interrupted");
      addMessage("[Interrupted]", "system");
      if (state.audio.player) state.audio.player.interrupt();
      stopAudioVisualization();
      break;
  }
}

// Connection handlers
function handleOpen() {
  updateStatus("connectionStatus", "Connected");
}

function handleClose() {
  updateStatus("connectionStatus", "Disconnected");
  disconnect();
}

function handleError(error) {
  console.error("Error:", error);
  updateStatus("connectionStatus", "Error: " + error);
  updateStatus("debugInfo", "Error: " + error);
}

// Toggle audio
async function toggleAudio() {
  if (!state.audio.isStreaming) {
    try {
      await connect();
      const selectedMicId = elements.micSelect.value;
      await state.audio.streamer.start(selectedMicId);
      state.audio.isStreaming = true;
      elements.startAudioBtn.classList.add("active");
      elements.startAudioBtn.title = "Stop microphone";
      addMessage("[Microphone on]", "system");
      startInputVisualization();
    } catch (error) {
      addMessage("[Audio error: " + error.message + "]", "system");
    }
  } else {
    stopInputVisualization();
    if (state.audio.streamer) state.audio.streamer.stop();
    state.audio.isStreaming = false;
    elements.startAudioBtn.classList.remove("active");
    elements.startAudioBtn.title = "Start microphone";
    addMessage("[Microphone off]", "system");
    disconnect();
  }
}

// Toggle video
async function toggleVideo() {
  if (!state.video.isStreaming) {
    try {
      // Initialize streamer if needed
      if (!state.video.streamer && state.client) {
        state.video.streamer = new VideoStreamer(state.client);
      }

      if (state.video.streamer) {
        // Get selected camera device ID
        const selectedCameraId = elements.cameraSelect.value;
        const video = await state.video.streamer.start({
          fps: 1,
          width: 640,
          height: 480,
          deviceId: selectedCameraId || null,
        });
        state.video.isStreaming = true;

        elements.videoPreview.srcObject = video.srcObject;
        elements.videoPreview.hidden = false;
        elements.startVideoBtn.classList.add("active");
        elements.startVideoBtn.title = "Stop camera";
        addMessage("[Camera on]", "system");
      } else {
        addMessage("[Connect to Gemini first]", "system");
      }
    } catch (error) {
      addMessage("[Video error: " + error.message + "]", "system");
    }
  } else {
    if (state.video.streamer) state.video.streamer.stop();
    state.video.isStreaming = false;

    elements.videoPreview.srcObject = null;
    elements.videoPreview.hidden = true;
    elements.startVideoBtn.classList.remove("active");
    elements.startVideoBtn.title = "Start camera";
    addMessage("[Camera off]", "system");
  }
}

// Toggle screen
async function toggleScreen() {
  if (!state.screen.isSharing) {
    try {
      // Initialize capture if needed
      if (!state.screen.capture && state.client) {
        state.screen.capture = new ScreenCapture(state.client);
      }

      if (state.screen.capture) {
        const video = await state.screen.capture.start({ fps: 0.5 });
        state.screen.isSharing = true;

        // Show screen preview in the same video element
        elements.videoPreview.srcObject = video.srcObject;
        elements.videoPreview.hidden = false;
        elements.startScreenBtn.classList.add("active");
        elements.startScreenBtn.title = "Stop sharing screen";
        addMessage("[Screen sharing on]", "system");
      } else {
        addMessage("[Connect to Gemini first]", "system");
      }
    } catch (error) {
      addMessage("[Screen share error: " + error.message + "]", "system");
    }
  } else {
    if (state.screen.capture) state.screen.capture.stop();
    state.screen.isSharing = false;

    // Hide preview if not using camera
    if (!state.video.isStreaming) {
      elements.videoPreview.srcObject = null;
      elements.videoPreview.hidden = true;
    }

    elements.startScreenBtn.classList.remove("active");
    elements.startScreenBtn.title = "Share screen";
    addMessage("[Screen sharing off]", "system");
  }
}

// Send message
function sendMessage() {
  const message = elements.chatInput.value.trim();
  if (!message) return;

  if (state.client) {
    addMessage(message, "user");
    state.client.sendTextMessage(message);
    elements.chatInput.value = "";
  } else {
    addMessage("[Connect to Gemini first]", "system");
  }
}

// Add message to chat
function addMessage(text, type, append = false) {
  // Get all div children (messages)
  const messages = elements.chatContainer.querySelectorAll("div");
  const lastMessage = messages[messages.length - 1];

  // Check if we should append to the last message
  if (append && lastMessage && lastMessage.className === type) {
    // Append to existing message of the same type
    lastMessage.textContent += text;
  } else {
    // Create new message
    const message = createMessage(text, type);
    elements.chatContainer.appendChild(message);
  }

  elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

// Update volume
function updateVolume() {
  const value = elements.volume.value;
  const volume = value / 100;
  if (state.audio.player) {
    state.audio.player.setVolume(volume);
  }
  updateStatus("volumeValue", value + "%");
}

// Update temperature display
function updateTemperature() {
  const value = elements.temperature.value;
  updateStatus("temperatureValue", value);
}

// Event listeners
function initEventListeners() {
  elements.startAudioBtn.addEventListener("click", toggleAudio);
  elements.startVideoBtn.addEventListener("click", toggleVideo);
  elements.startScreenBtn.addEventListener("click", toggleScreen);
  //elements.sendBtn.addEventListener("click", sendMessage);
  elements.volume.addEventListener("input", updateVolume);
  //elements.temperature.addEventListener("input", updateTemperature);

  //elements.chatInput.addEventListener("keypress", (e) => {
  //  if (e.key === "Enter") sendMessage();
  //});
}

// Initialize
window.addEventListener("DOMContentLoaded", () => {
  initDOM();
  initEventListeners();
  populateMediaDevices();
  updateStatus("debugInfo", "Application initialized");
});
