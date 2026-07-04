export function setupLabUi({ onSubmit }) {
  const chatPanel = document.querySelector(".chat-panel");
  const form = document.querySelector("#chatForm");
  const input = document.querySelector("#messageInput");
  const sendButton = document.querySelector("#sendButton");
  const speechBubble = document.querySelector("#speechBubble");
  const labResetButton = document.querySelector("#labResetButton");
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
  const codexTaskDetail = document.querySelector("#codexTaskDetail");
  const codexTaskSimulation = document.querySelector("#codexTaskSimulation");
  const codexTaskGoal = document.querySelector("#codexTaskGoal");
  const codexTaskSaveInfo = document.querySelector("#codexTaskSaveInfo");
  const codexTaskActionInfo = document.querySelector("#codexTaskActionInfo");
  const codexTaskText = document.querySelector("#codexTaskText");
  const saveCodexTaskButton = document.querySelector("#saveCodexTaskButton");
  const copyCodexTaskButton = document.querySelector("#copyCodexTaskButton");
  const previewCodexTaskButton = document.querySelector("#previewCodexTaskButton");
  const applyCodexTaskButton = document.querySelector("#applyCodexTaskButton");
  const requestCodexImplementationButton = document.querySelector("#requestCodexImplementationButton");
  const codexTaskPlan = document.querySelector("#codexTaskPlan");
  const codexImplementationProgress = document.querySelector("#codexImplementationProgress");
  const codexTaskHistory = document.querySelector("#codexTaskHistory");

  initResizablePanels();

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) {
      return;
    }

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
      this.setSpeech(message);
    },
    addError(message) {
      this.setSpeech(message);
      setStatusText(codexTaskActionInfo, message);
    },
    resetChat(message) {
      this.setSpeech(message);
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
    resetSimulationInputs() {
      gravityInput.value = "9.8";
      heightInput.value = "5.0";
      bounceInput.value = "0.72";
      mazeRandomInput.checked = false;
      mazeSizeInput.value = "7";
      mazeDensityInput.value = "0.32";
      mazeSeedInput.value = "";
      flockingCountInput.value = "30";
      flockingSeedInput.value = "";
      cohesionInput.value = "0.55";
      alignmentInput.value = "0.65";
      separationInput.value = "1.25";
      speedSelect.value = "1";
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
      previewCodexTaskButton.disabled = true;
      applyCodexTaskButton.disabled = true;
      setButtonDisabled(requestCodexImplementationButton, true);
      codexTaskPlan.hidden = true;
      codexTaskPlan.replaceChildren();
      clearCodexImplementationProgress();
    },
    showSavedCodexTask(task) {
      codexTaskEmpty.hidden = true;
      codexTaskDetail.hidden = false;
      codexTaskSimulation.textContent = task.simulation_name ?? task.experiment_spec?.simulation_name ?? "new_simulation";
      codexTaskGoal.textContent = task.experiment_spec?.goal ?? "未設定";
      codexTaskSaveInfo.textContent = `保存済み: ${task.task_id} / ${formatDateTime(task.created_at)}`;
      codexTaskActionInfo.textContent = "";
      codexTaskText.value = task.codex_task ?? "";
      saveCodexTaskButton.disabled = true;
      saveCodexTaskButton.textContent = "保存";
      copyCodexTaskButton.disabled = false;
      previewCodexTaskButton.disabled = false;
      applyCodexTaskButton.disabled = true;
      setButtonDisabled(requestCodexImplementationButton, false);
      codexTaskPlan.hidden = true;
      codexTaskPlan.replaceChildren();
      clearCodexImplementationProgress();
    },
    setCodexTaskSaved({ taskId, createdAt }) {
      codexTaskSaveInfo.textContent = `保存済み: ${taskId} / ${formatDateTime(createdAt)}`;
      saveCodexTaskButton.disabled = true;
      saveCodexTaskButton.textContent = "保存";
      copyCodexTaskButton.disabled = false;
      previewCodexTaskButton.disabled = false;
      applyCodexTaskButton.disabled = true;
      setButtonDisabled(requestCodexImplementationButton, false);
    },
    setCodexTaskBusy(isBusy) {
      [saveCodexTaskButton, copyCodexTaskButton, previewCodexTaskButton, applyCodexTaskButton, requestCodexImplementationButton].forEach((button) => {
        if (!button) {
          return;
        }
        if (isBusy) {
          button.dataset.wasDisabled = button.disabled ? "true" : "false";
          button.disabled = true;
          return;
        }
        button.disabled = button.dataset.wasDisabled === "true";
        delete button.dataset.wasDisabled;
      });
      saveCodexTaskButton.textContent = isBusy ? "保存中" : "保存";
    },
    setCodexTaskStatus(message) {
      codexTaskActionInfo.textContent = message;
    },
    selectCodexTaskText() {
      codexTaskText.focus();
      codexTaskText.select();
    },
    setCodexTaskPlan(plan) {
      codexTaskPlan.replaceChildren();
      codexTaskPlan.hidden = false;
      const status = document.createElement("div");
      status.innerHTML = `<strong>プレビュー:</strong> ${plan.status} / ${plan.simulation_name}`;
      codexTaskPlan.append(status);

      const operations = document.createElement("div");
      operations.innerHTML = `<strong>変更:</strong> ${formatOperations(plan.operations)}`;
      codexTaskPlan.append(operations);

      if (plan.affected_files?.length) {
        const files = document.createElement("div");
        files.innerHTML = `<strong>影響ファイル:</strong> ${plan.affected_files.join(", ")}`;
        codexTaskPlan.append(files);
      }

      if (plan.warnings?.length) {
        const warnings = document.createElement("div");
        warnings.innerHTML = `<strong>注意:</strong> ${plan.warnings.join(" / ")}`;
        codexTaskPlan.append(warnings);
      }

      applyCodexTaskButton.disabled = !plan.apply_available;
    },
    setCodexTaskApplyResult(result) {
      codexTaskPlan.hidden = false;
      const applied = document.createElement("div");
      applied.innerHTML = `<strong>適用結果:</strong> ${result.status} / ${formatDateTime(result.applied_at)}`;
      codexTaskPlan.append(applied);
      applyCodexTaskButton.disabled = true;
    },
    resetCodexTaskPanel() {
      codexTaskEmpty.hidden = false;
      codexTaskDetail.hidden = true;
      codexTaskSimulation.textContent = "-";
      codexTaskGoal.textContent = "-";
      codexTaskSaveInfo.textContent = "";
      codexTaskActionInfo.textContent = "";
      codexTaskText.value = "";
      saveCodexTaskButton.disabled = true;
      saveCodexTaskButton.textContent = "保存";
      copyCodexTaskButton.disabled = true;
      previewCodexTaskButton.disabled = true;
      applyCodexTaskButton.disabled = true;
      setButtonDisabled(requestCodexImplementationButton, true);
      codexTaskPlan.hidden = true;
      codexTaskPlan.replaceChildren();
      codexTaskHistory.replaceChildren();
      clearCodexImplementationProgress();
    },
    setCodexImplementationProgress(status) {
      if (!codexImplementationProgress) {
        return;
      }
      codexImplementationProgress.hidden = false;
      codexImplementationProgress.replaceChildren();

      const summary = document.createElement("div");
      const updatedAt = status.updated_at ? ` / ${formatDateTime(status.updated_at)}` : "";
      const exitCode = Number.isInteger(status.exit_code) ? ` / exit ${status.exit_code}` : "";
      summary.textContent = `実装状況: ${status.status}${updatedAt}${exitCode}`;
      codexImplementationProgress.append(summary);

      if (status.error) {
        const error = document.createElement("div");
        error.textContent = `エラー: ${status.error}`;
        codexImplementationProgress.append(error);
      }

      if (status.output_tail) {
        const output = document.createElement("pre");
        output.textContent = trimCodexOutput(status.output_tail);
        codexImplementationProgress.append(output);
        output.scrollTop = output.scrollHeight;
      }
    },
    clearCodexImplementationProgress() {
      clearCodexImplementationProgress();
    },
    setCodexTaskHistory(tasks = [], onSelect) {
      codexTaskHistory.replaceChildren();
      if (!tasks.length) {
        return;
      }
      const title = document.createElement("div");
      title.textContent = "保存済み依頼案";
      codexTaskHistory.append(title);
      tasks.slice(0, 5).forEach((task) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "codex-task-history-item";
        item.title = task.title;
        item.textContent = `${formatDateTime(task.created_at)} / ${task.simulation_name} / ${task.title}`;
        item.addEventListener("click", () => onSelect?.(task));
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
    onPreviewCodexTask(handler) {
      previewCodexTaskButton.addEventListener("click", handler);
    },
    onApplyCodexTask(handler) {
      applyCodexTaskButton.addEventListener("click", handler);
    },
    onRequestCodexImplementation(handler) {
      requestCodexImplementationButton?.addEventListener("click", handler);
    },
    onLabReset(handler) {
      labResetButton?.addEventListener("click", handler);
    },
    setLabResetBusy(isBusy) {
      if (!labResetButton) {
        return;
      }
      labResetButton.disabled = isBusy;
      labResetButton.textContent = isBusy ? "初期化中" : "初期状態";
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

  function clearCodexImplementationProgress() {
    if (!codexImplementationProgress) {
      return;
    }
    codexImplementationProgress.hidden = true;
    codexImplementationProgress.replaceChildren();
  }

  function initResizablePanels() {
    if (!chatPanel || !simulationPanel || !simulationPanelResizer) {
      return;
    }

    const minSimulationHeight = 120;
    const storageKey = "3d-ai-lab-simulation-panel-height";

    const readStoredHeight = (key, fallback) => {
      const value = Number(window.localStorage.getItem(key));
      return Number.isFinite(value) ? value : fallback;
    };

    const setPanelHeight = (simulationHeight) => {
      const availableHeight =
        chatPanel.clientHeight -
        document.querySelector(".chat-header").offsetHeight -
        form.offsetHeight -
        simulationPanelResizer.offsetHeight -
        120;
      const simulation = clampNumber(simulationHeight, minSimulationHeight, Math.max(minSimulationHeight, availableHeight));

      chatPanel.style.setProperty("--simulation-panel-height", `${simulation}px`);
      return simulation;
    };

    const initial = setPanelHeight(readStoredHeight(storageKey, simulationPanel.getBoundingClientRect().height || 250));
    window.localStorage.setItem(storageKey, String(Math.round(initial)));

    const startDrag = (event) => {
      event.preventDefault();
      const handle = simulationPanelResizer;
      const startY = event.clientY;
      const startSimulationHeight = simulationPanel.getBoundingClientRect().height;
      handle.classList.add("is-dragging");
      handle.setPointerCapture?.(event.pointerId);

      const onPointerMove = (moveEvent) => {
        const delta = moveEvent.clientY - startY;
        const next = setPanelHeight(startSimulationHeight + delta);
        window.localStorage.setItem(storageKey, String(Math.round(next)));
      };

      const onPointerUp = () => {
        handle.classList.remove("is-dragging");
        window.removeEventListener("pointermove", onPointerMove);
        window.removeEventListener("pointerup", onPointerUp);
      };

      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", onPointerUp);
    };

    simulationPanelResizer.addEventListener("pointerdown", startDrag);
    window.addEventListener("resize", () => {
      setPanelHeight(simulationPanel.getBoundingClientRect().height);
    });
  }
}

function setBusy(button, input, isBusy) {
  button.disabled = isBusy;
  input.disabled = isBusy;
  button.textContent = isBusy ? "送信中" : "送信";
}

function setButtonDisabled(button, isDisabled) {
  if (!button) {
    return;
  }
  button.disabled = isDisabled;
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

function formatOperations(operations = []) {
  if (!operations.length) {
    return "適用可能な変更はありません";
  }
  return operations.map((operation) => `${operation.label}=${formatOperationValue(operation.value)}`).join(" / ");
}

function formatOperationValue(value) {
  return Array.isArray(value) ? value.join(", ") : value;
}

function trimCodexOutput(output) {
  const lines = String(output)
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "");
  return lines.slice(-80).join("\n");
}
