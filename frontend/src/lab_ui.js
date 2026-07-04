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
  const mazeRandomInput = document.querySelector("#mazeRandomInput");
  const mazeSizeInput = document.querySelector("#mazeSizeInput");
  const mazeDensityInput = document.querySelector("#mazeDensityInput");
  const mazeSeedInput = document.querySelector("#mazeSeedInput");
  const flockingParams = document.querySelector("#flockingParams");
  const flockingCountInput = document.querySelector("#flockingCountInput");
  const flockingSeedInput = document.querySelector("#flockingSeedInput");
  const cohesionInput = document.querySelector("#cohesionInput");
  const alignmentInput = document.querySelector("#alignmentInput");
  const separationInput = document.querySelector("#separationInput");
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
      const seed = readOptionalInteger(mazeSeedInput);
      const params = {
        grid_size: clampNumber(readNumber(mazeSizeInput, 7), 5, 11),
        steps_per_cell: 12,
        dt: 0.08,
        show_search: false,
        randomize: mazeRandomInput.checked,
        wall_density: clampNumber(readNumber(mazeDensityInput, 0.32), 0, 1),
      };
      if (seed !== null) {
        params.seed = seed;
      }
      return params;
    },
    applyMazeAgentParams(params = {}) {
      if (typeof params.grid_size === "number") {
        mazeSizeInput.value = params.grid_size.toString();
      }
      if (typeof params.randomize === "boolean") {
        mazeRandomInput.checked = params.randomize;
      }
      if (typeof params.wall_density === "number") {
        mazeDensityInput.value = params.wall_density.toString();
      }
      if (typeof params.seed === "number") {
        mazeSeedInput.value = params.seed.toString();
      }
    },
    getFlockingParams() {
      const seed = readOptionalInteger(flockingSeedInput);
      const params = {
        agent_count: clampNumber(readNumber(flockingCountInput, 30), 10, 80),
        steps: 360,
        dt: 0.08,
        cohesion_weight: clampNumber(readNumber(cohesionInput, 0.55), 0, 2),
        alignment_weight: clampNumber(readNumber(alignmentInput, 0.65), 0, 2),
        separation_weight: clampNumber(readNumber(separationInput, 1.25), 0, 3),
        perception_radius: 2.2,
        separation_radius: 0.7,
        bounds: 6.0,
      };
      if (seed !== null) {
        params.seed = seed;
      }
      return params;
    },
    applyFlockingParams(params = {}) {
      if (typeof params.agent_count === "number") {
        flockingCountInput.value = params.agent_count.toString();
      }
      if (typeof params.seed === "number") {
        flockingSeedInput.value = params.seed.toString();
      }
      if (typeof params.cohesion_weight === "number") {
        cohesionInput.value = params.cohesion_weight.toString();
      }
      if (typeof params.alignment_weight === "number") {
        alignmentInput.value = params.alignment_weight.toString();
      }
      if (typeof params.separation_weight === "number") {
        separationInput.value = params.separation_weight.toString();
      }
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
    const isFlocking = simulationName === "flocking";
    simulationTitle.textContent = simulationName;
    gravityParams.hidden = isMaze || isFlocking;
    mazeParams.hidden = !isMaze;
    flockingParams.hidden = !isFlocking;
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

function readOptionalInteger(input) {
  if (!input.value.trim()) {
    return null;
  }
  const value = Number.parseInt(input.value, 10);
  return Number.isFinite(value) ? value : null;
}

function clampNumber(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}
