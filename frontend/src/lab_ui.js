export function setupLabUi({ onSubmit }) {
  const form = document.querySelector("#chatForm");
  const input = document.querySelector("#messageInput");
  const sendButton = document.querySelector("#sendButton");
  const chatLog = document.querySelector("#chatLog");
  const speechBubble = document.querySelector("#speechBubble");
  const gravityInput = document.querySelector("#gravityInput");
  const heightInput = document.querySelector("#heightInput");
  const bounceInput = document.querySelector("#bounceInput");
  const simulationTitle = document.querySelector("#simulationTitle");
  const simulationSelect = document.querySelector("#simulationSelect");
  const gravityParams = document.querySelector("#gravityParams");
  const mazeParams = document.querySelector("#mazeParams");
  const speedSelect = document.querySelector("#speedSelect");
  const runSimulationButton = document.querySelector("#runSimulationButton");
  const playPauseButton = document.querySelector("#playPauseButton");
  const resetSimulationButton = document.querySelector("#resetSimulationButton");
  const stepSimulationButton = document.querySelector("#stepSimulationButton");
  const loadResultButton = document.querySelector("#loadResultButton");
  const simulationStatus = document.querySelector("#simulationStatus");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) {
      return;
    }

    addMessage(chatLog, "student", message);
    input.value = "";
    setBusy(sendButton, input, true);

    try {
      await onSubmit(message);
    } finally {
      setBusy(sendButton, input, false);
      input.focus();
    }
  });

  return {
    addAssistantMessage(message) {
      addMessage(chatLog, "assistant", message);
    },
    addError(message) {
      addMessage(chatLog, "error", message);
    },
    setSpeech(text) {
      speechBubble.textContent = text;
    },
    getSelectedSimulation() {
      return simulationSelect.value;
    },
    setSelectedSimulation(simulationName) {
      simulationSelect.value = simulationName;
      setSimulationMode(simulationName);
    },
    getGravityBallParams() {
      return {
        gravity: readNumber(gravityInput, 9.8),
        initial_height: readNumber(heightInput, 5.0),
        bounce: readNumber(bounceInput, 0.72),
        steps: 360,
        dt: 0.016,
      };
    },
    applyGravityBallParams(params = {}) {
      if (typeof params.gravity === "number") {
        gravityInput.value = params.gravity.toString();
      }
      if (typeof params.initial_height === "number") {
        heightInput.value = params.initial_height.toString();
      }
      if (typeof params.bounce === "number") {
        bounceInput.value = params.bounce.toString();
      }
    },
    getMazeAgentParams() {
      return {
        grid_size: 7,
        steps_per_cell: 12,
        dt: 0.08,
        show_search: false,
      };
    },
    setSimulationMode(simulationName) {
      setSimulationMode(simulationName);
    },
    setSimulationBusy(isBusy) {
      runSimulationButton.disabled = isBusy;
      loadResultButton.disabled = isBusy;
      runSimulationButton.textContent = isBusy ? "実行中" : "実行";
    },
    setPlayButton(isPlaying) {
      playPauseButton.textContent = isPlaying ? "一時停止" : "再生";
    },
    setSimulationStatus(status) {
      simulationStatus.textContent = status;
    },
    onRunSimulation(handler) {
      runSimulationButton.addEventListener("click", handler);
    },
    onSimulationChange(handler) {
      simulationSelect.addEventListener("change", () => {
        setSimulationMode(simulationSelect.value);
        handler(simulationSelect.value);
      });
    },
    onLoadResult(handler) {
      loadResultButton.addEventListener("click", handler);
    },
    onTogglePlayback(handler) {
      playPauseButton.addEventListener("click", handler);
    },
    onResetSimulation(handler) {
      resetSimulationButton.addEventListener("click", handler);
    },
    onStepSimulation(handler) {
      stepSimulationButton.addEventListener("click", handler);
    },
    onSpeedChange(handler) {
      speedSelect.addEventListener("change", () => handler(Number(speedSelect.value)));
    },
  };

  function setSimulationMode(simulationName) {
    const isMaze = simulationName === "maze_agent";
    simulationTitle.textContent = simulationName;
    gravityParams.hidden = isMaze;
    mazeParams.hidden = !isMaze;
  }
}

function addMessage(container, role, text) {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  message.textContent = text;
  container.append(message);
  container.scrollTop = container.scrollHeight;
}

function setBusy(button, input, isBusy) {
  button.disabled = isBusy;
  input.disabled = isBusy;
  button.textContent = isBusy ? "送信中" : "送信";
}

function readNumber(input, fallback) {
  const value = Number(input.value);
  return Number.isFinite(value) ? value : fallback;
}
