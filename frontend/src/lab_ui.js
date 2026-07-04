export function setupLabUi({ onSubmit }) {
  const chatPanel = document.querySelector(".chat-panel");
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
  const simulationPanel = document.querySelector(".simulation-panel");
  const simulationPanelResizer = document.querySelector("#simulationPanelResizer");
  const playPauseButton = document.querySelector("#playPauseButton");
  const resetSimulationButton = document.querySelector("#resetSimulationButton");
  const stepSimulationButton = document.querySelector("#stepSimulationButton");
  const loadResultButton = document.querySelector("#loadResultButton");
  const simulationStatus = document.querySelector("#simulationStatus");
  const codexTaskEmpty = document.querySelector("#codexTaskEmpty");
  const codexTaskPanel = document.querySelector("#codexTaskPanel");
  const codexTaskPanelResizer = document.querySelector("#codexTaskPanelResizer");
  const codexTaskDetail = document.querySelector("#codexTaskDetail");
  const codexTaskSimulation = document.querySelector("#codexTaskSimulation");
  const codexTaskGoal = document.querySelector("#codexTaskGoal");
  const codexTaskSaveInfo = document.querySelector("#codexTaskSaveInfo");
  const codexTaskActionInfo = document.querySelector("#codexTaskActionInfo");
  const codexTaskText = document.querySelector("#codexTaskText");
  const saveCodexTaskButton = document.querySelector("#saveCodexTaskButton");
  const copyCodexTaskButton = document.querySelector("#copyCodexTaskButton");
  const codexTaskHistory = document.querySelector("#codexTaskHistory");

  initResizablePanels();

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
    showCodexTaskDraft({ experimentSpec, codexTask }) {
      const simulationName = experimentSpec?.simulation_name ?? "new_simulation";
      const goal = experimentSpec?.goal ?? "未設定";
      codexTaskEmpty.hidden = true;
      codexTaskDetail.hidden = false;
      codexTaskSimulation.textContent = simulationName;
      codexTaskGoal.textContent = goal;
      codexTaskSaveInfo.textContent = "未保存";
      codexTaskActionInfo.textContent = "";
      codexTaskText.value = codexTask;
      saveCodexTaskButton.disabled = false;
      saveCodexTaskButton.textContent = "保存";
      copyCodexTaskButton.disabled = false;
    },
    setCodexTaskSaved({ taskId, createdAt }) {
      codexTaskSaveInfo.textContent = `保存済み: ${taskId} / ${formatDateTime(createdAt)}`;
      saveCodexTaskButton.disabled = true;
      saveCodexTaskButton.textContent = "保存";
      copyCodexTaskButton.disabled = false;
    },
    setCodexTaskBusy(isBusy) {
      saveCodexTaskButton.disabled = isBusy;
      copyCodexTaskButton.disabled = isBusy;
      saveCodexTaskButton.textContent = isBusy ? "保存中" : "保存";
    },
    setCodexTaskStatus(message) {
      codexTaskActionInfo.textContent = message;
    },
    selectCodexTaskText() {
      codexTaskText.focus();
      codexTaskText.select();
    },
    setCodexTaskHistory(tasks = []) {
      codexTaskHistory.replaceChildren();
      if (!tasks.length) {
        return;
      }
      const title = document.createElement("div");
      title.textContent = "保存済み依頼案";
      codexTaskHistory.append(title);
      tasks.slice(0, 5).forEach((task) => {
        const item = document.createElement("div");
        item.className = "codex-task-history-item";
        item.title = task.title;
        item.textContent = `${formatDateTime(task.created_at)} / ${task.simulation_name} / ${task.title}`;
        codexTaskHistory.append(item);
      });
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
    onSaveCodexTask(handler) {
      saveCodexTaskButton.addEventListener("click", handler);
    },
    onCopyCodexTask(handler) {
      copyCodexTaskButton.addEventListener("click", handler);
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

  function initResizablePanels() {
    if (!chatPanel || !simulationPanel || !codexTaskPanel || !simulationPanelResizer || !codexTaskPanelResizer) {
      return;
    }

    const minChatHeight = 96;
    const minSimulationHeight = 120;
    const minCodexHeight = 72;
    const storageKeys = {
      simulation: "3d-ai-lab-simulation-panel-height",
      codex: "3d-ai-lab-codex-task-panel-height",
    };

    const readStoredHeight = (key, fallback) => {
      const value = Number(window.localStorage.getItem(key));
      return Number.isFinite(value) ? value : fallback;
    };

    const setPanelHeights = (simulationHeight, codexHeight) => {
      const availableHeight =
        chatPanel.clientHeight -
        document.querySelector(".chat-header").offsetHeight -
        form.offsetHeight -
        simulationPanelResizer.offsetHeight -
        codexTaskPanelResizer.offsetHeight -
        minChatHeight;
      const available = Math.max(minSimulationHeight + minCodexHeight, availableHeight);
      const simulation = clampNumber(simulationHeight, minSimulationHeight, available - minCodexHeight);
      const codex = clampNumber(codexHeight, minCodexHeight, available - simulation);

      chatPanel.style.setProperty("--simulation-panel-height", `${simulation}px`);
      chatPanel.style.setProperty("--codex-task-panel-height", `${codex}px`);
      return { simulation, codex };
    };

    const initial = setPanelHeights(
      readStoredHeight(storageKeys.simulation, simulationPanel.getBoundingClientRect().height || 250),
      readStoredHeight(storageKeys.codex, codexTaskPanel.getBoundingClientRect().height || 180)
    );
    window.localStorage.setItem(storageKeys.simulation, String(Math.round(initial.simulation)));
    window.localStorage.setItem(storageKeys.codex, String(Math.round(initial.codex)));

    const startDrag = (event, target) => {
      event.preventDefault();
      const handle = target === "simulation" ? simulationPanelResizer : codexTaskPanelResizer;
      const startY = event.clientY;
      const startSimulationHeight = simulationPanel.getBoundingClientRect().height;
      const startCodexHeight = codexTaskPanel.getBoundingClientRect().height;
      handle.classList.add("is-dragging");
      handle.setPointerCapture?.(event.pointerId);

      const onPointerMove = (moveEvent) => {
        const delta = moveEvent.clientY - startY;
        const nextSimulationHeight = target === "simulation" ? startSimulationHeight + delta : startSimulationHeight;
        const nextCodexHeight = target === "codex" ? startCodexHeight + delta : startCodexHeight;
        const next = setPanelHeights(nextSimulationHeight, nextCodexHeight);
        window.localStorage.setItem(storageKeys.simulation, String(Math.round(next.simulation)));
        window.localStorage.setItem(storageKeys.codex, String(Math.round(next.codex)));
      };

      const onPointerUp = () => {
        handle.classList.remove("is-dragging");
        window.removeEventListener("pointermove", onPointerMove);
        window.removeEventListener("pointerup", onPointerUp);
      };

      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", onPointerUp);
    };

    simulationPanelResizer.addEventListener("pointerdown", (event) => startDrag(event, "simulation"));
    codexTaskPanelResizer.addEventListener("pointerdown", (event) => startDrag(event, "codex"));
    window.addEventListener("resize", () => {
      setPanelHeights(simulationPanel.getBoundingClientRect().height, codexTaskPanel.getBoundingClientRect().height);
    });
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

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value ?? "-";
  }
  return date.toLocaleString("ja-JP", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
