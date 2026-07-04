import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  applyCodexTask,
  getCodexImplementationRequests,
  getCodexImplementationStatus,
  getFlockingResult,
  getCodexTask,
  getCodexTasks,
  getGravityBallResult,
  getMazeAgentResult,
  planCodexTask,
  requestCodexImplementation,
  resetLabState,
  runFlocking,
  runGravityBall,
  runMazeAgent,
  saveCodexTask,
  sendChatMessage,
} from "./api_client.js?v=20260704-progress-sync2";
import { animateLabAssistant, createLabAssistant } from "./avatar.js?v=20260704-progress-sync2";
import { setupLabUi } from "./lab_ui.js?v=20260704-progress-sync2";
import { FlockingViewer, GravityBallViewer, MazeAgentViewer } from "./simulation_viewer.js?v=20260704-progress-sync2";

const canvas = document.querySelector("#scene");
const sessionKey = "3d-ai-lab-session-id";
let sessionId = window.localStorage.getItem(sessionKey);
let codexImplementationPollId = null;

const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: true,
  alpha: false,
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x0d1116, 1);
renderer.shadowMap.enabled = true;

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0x0d1116, 12, 34);

const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 100);
camera.position.set(3.6, 3.0, 6.2);
camera.lookAt(0, 1.35, 0);

const controls = new OrbitControls(camera, canvas);
controls.target.set(0, 1.2, 0);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 2.2;
controls.maxDistance = 18;
controls.maxPolarAngle = Math.PI * 0.48;
controls.update();

const assistant = createLabAssistant();
assistant.position.set(-2.35, 0, 0);
scene.add(assistant);

addLights(scene);
addLabFloor(scene);

const clock = new THREE.Clock();
const gravityBallViewer = new GravityBallViewer(scene);
const mazeAgentViewer = new MazeAgentViewer(scene);
const flockingViewer = new FlockingViewer(scene);
const viewers = {
  gravity_ball: gravityBallViewer,
  maze_agent: mazeAgentViewer,
  flocking: flockingViewer,
};
let activeSimulation = "gravity_ball";
let currentCodexTaskDraft = null;
let codexImplementationPollFailures = 0;
mazeAgentViewer.setVisible(false);
flockingViewer.setVisible(false);

const ui = setupLabUi({
  async onSubmit(message) {
    try {
      const response = await sendChatMessage({ message, sessionId });
      sessionId = response.session_id;
      window.localStorage.setItem(sessionKey, sessionId);
      const isPendingImplementationConfirmation = response.assistant_notes?.includes("シミュレーション実装確認待ち") ?? false;
      if (response.codex_task) {
        currentCodexTaskDraft = {
          session_id: sessionId,
          source_message: message,
          experiment_spec: response.experiment_spec ?? {},
          codex_task: response.codex_task,
        };
        ui.showCodexTaskDraft({
          experimentSpec: currentCodexTaskDraft.experiment_spec,
          codexTask: currentCodexTaskDraft.codex_task,
        });
      }
      ui.setSpeech(response.reply);

      if (response.suggested_action === "run_gravity_ball") {
        switchSimulation("gravity_ball");
        ui.applyGravityBallParams(response.simulation_params ?? {});
        ui.setSpeech("gravity_ball を指定条件で実行します。");
        await runActiveSimulationFromUi();
      }

      if (response.suggested_action === "run_maze_agent") {
        switchSimulation("maze_agent");
        ui.applyMazeAgentParams(response.simulation_params ?? {});
        ui.setSpeech("maze_agent を軽量探索で実行します。");
        await runActiveSimulationFromUi();
      }

      if (response.suggested_action === "run_flocking") {
        switchSimulation("flocking");
        ui.applyFlockingParams(response.simulation_params ?? {});
        ui.setSpeech("flocking を指定条件で実行します。");
        await runActiveSimulationFromUi();
      }
    } catch (error) {
      const messageText = error instanceof Error ? error.message : "チャット送信に失敗しました。";
      ui.addError(messageText);
      ui.setSpeech("通信に失敗しました。サーバーが起動しているか確認してください。");
    }
  },
});

ui.setSpeech("こんにちは。ここでは小さな3D実験の相談ができます。");
ui.onRunSimulation(runActiveSimulationFromUi);
ui.onLoadResult(loadLatestActiveSimulation);
ui.onSimulationChange(async (simulationName) => {
  switchSimulation(simulationName);
  await loadLatestActiveSimulation();
});
ui.onTogglePlayback(() => {
  const isPlaying = getActiveViewer().togglePlaying();
  ui.setPlayButton(isPlaying);
});
ui.onResetSimulation(() => {
  getActiveViewer().reset();
  getActiveViewer().setPlaying(false);
  ui.setPlayButton(false);
  updateSimulationStatus();
});
ui.onStepSimulation(() => {
  getActiveViewer().step();
  ui.setPlayButton(false);
  updateSimulationStatus();
});
ui.onSpeedChange((speed) => {
  Object.values(viewers).forEach((viewer) => viewer.setSpeed(speed));
  updateSimulationStatus();
});
ui.onSaveCodexTask(saveCurrentCodexTaskDraft);
ui.onCopyCodexTask(copyCurrentCodexTaskDraft);
ui.onPreviewCodexTask(previewCurrentCodexTask);
ui.onApplyCodexTask(applyCurrentCodexTask);
ui.onRequestCodexImplementation(requestCurrentCodexImplementation);
ui.onLabReset(resetLabToInitialState);

resize();
window.addEventListener("resize", resize);
requestAnimationFrame(tick);
loadLatestActiveSimulation();
loadCodexTaskHistory();
resumeAnyCodexImplementationProgress();
window.setInterval(resumeAnyCodexImplementationProgress, 5000);

function tick() {
  const delta = clock.getDelta();
  const elapsed = clock.elapsedTime;
  animateLabAssistant(assistant, elapsed);
  gravityBallViewer.update(delta);
  mazeAgentViewer.update(delta);
  flockingViewer.update(delta);
  controls.update();
  updateSimulationStatus();
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}

function resize() {
  const { clientWidth, clientHeight } = canvas.parentElement;
  camera.aspect = clientWidth / clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(clientWidth, clientHeight, false);
}

function addLights(targetScene) {
  const ambient = new THREE.HemisphereLight(0xddeeff, 0x20242b, 1.55);
  targetScene.add(ambient);

  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(4, 8, 5);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  targetScene.add(key);

  const rim = new THREE.PointLight(0x45c4a0, 25, 12);
  rim.position.set(-3.5, 2.8, -3);
  targetScene.add(rim);
}

function addLabFloor(targetScene) {
  const floorMaterial = new THREE.MeshStandardMaterial({
    color: 0x1a222b,
    roughness: 0.86,
    metalness: 0.04,
  });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(18, 18), floorMaterial);
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  targetScene.add(floor);

  const grid = new THREE.GridHelper(18, 18, 0x45c4a0, 0x2a3640);
  grid.position.y = 0.01;
  targetScene.add(grid);
}

function switchSimulation(simulationName) {
  activeSimulation = Object.hasOwn(viewers, simulationName) ? simulationName : "gravity_ball";
  Object.entries(viewers).forEach(([name, viewer]) => {
    viewer.setVisible(name === activeSimulation);
    if (name !== activeSimulation) {
      viewer.setPlaying(false);
    }
  });
  ui.setSelectedSimulation(activeSimulation);
  ui.setPlayButton(getActiveViewer().getStatus().playing);
  updateSimulationStatus();
}

function getActiveViewer() {
  return viewers[activeSimulation];
}

async function runActiveSimulationFromUi() {
  ui.setSimulationBusy(true);
  try {
    const params = getActiveSimulationParams();
    const result = await runActiveSimulation(params);
    getActiveViewer().loadResult(result);
    getActiveViewer().setPlaying(true);
    ui.setPlayButton(true);
    ui.setSpeech(`${activeSimulation} を実行しました。シミュレーションを再生します。`);
    updateSimulationStatus();
  } catch (error) {
    const message = error instanceof Error ? error.message : "シミュレーションの実行に失敗しました。";
    ui.addError(`${activeSimulation} の実行に失敗しました: ${message}`);
    ui.setSpeech("シミュレーションの実行に失敗しました。");
  } finally {
    ui.setSimulationBusy(false);
  }
}

async function loadLatestActiveSimulation() {
  ui.setSimulationBusy(true);
  try {
    const result = await getActiveSimulationResult();
    getActiveViewer().loadResult(result);
    if (activeSimulation === "gravity_ball") {
      ui.applyGravityBallParams(result.meta?.parameters ?? {});
    }
    if (activeSimulation === "maze_agent") {
      ui.applyMazeAgentParams(result.meta?.parameters ?? {});
    }
    if (activeSimulation === "flocking") {
      ui.applyFlockingParams(result.meta?.parameters ?? {});
    }
    ui.setPlayButton(false);
    updateSimulationStatus();
  } catch (error) {
    const message = error instanceof Error ? error.message : "シミュレーション結果の読み込みに失敗しました。";
    ui.addError(message);
  } finally {
    ui.setSimulationBusy(false);
  }
}

function updateSimulationStatus() {
  const status = getActiveViewer().getStatus();
  if (!status.loaded) {
    ui.setSimulationStatus("まだシミュレーション結果は読み込まれていません。");
    return;
  }

  const frame = status.frameCount > 0 ? status.frameIndex + 1 : 0;
  const summary = status.summary ?? {};
  const params = status.parameters ?? {};
  if (activeSimulation === "flocking") {
    ui.setSimulationStatus(
      [
        `frame ${frame}/${status.frameCount}`,
        `個体 ${summary.agent_count ?? params.agent_count ?? "-"} / seed ${summary.seed ?? "-"}`,
        `平均速度 ${formatNumber(summary.avg_speed)} / 広がり ${formatNumber(summary.avg_spread)} / 再生 ${status.playing ? "中" : "停止"}`,
      ].join("  ")
    );
    return;
  }

  if (activeSimulation === "maze_agent") {
    const mazeKind = summary.maze_type === "random" ? `ランダム seed ${summary.seed ?? "-"}` : "固定";
    ui.setSimulationStatus(
      [
        `frame ${frame}/${status.frameCount}`,
        `${mazeKind} / 迷路 ${summary.grid_size ?? params.grid_size ?? 7}x${summary.grid_size ?? params.grid_size ?? 7}`,
        `壁 ${summary.wall_count ?? "-"} / 経路 ${summary.path_length ?? "-"} マス / ゴール ${summary.reached_goal ? "到達" : "未到達"} / 再生 ${status.playing ? "中" : "停止"}`,
      ].join("  ")
    );
    return;
  }

  ui.setSimulationStatus(
    [
      `frame ${frame}/${status.frameCount}`,
      `重力 ${formatNumber(params.gravity)} / 高さ ${formatNumber(params.initial_height)} / 反発 ${formatNumber(params.bounce)}`,
      `跳ね返り ${summary.bounces ?? 0} 回 / 最大高さ ${formatNumber(summary.max_height)} / 再生 ${status.playing ? "中" : "停止"}`,
    ].join("  ")
  );
}

function getActiveSimulationParams() {
  if (activeSimulation === "maze_agent") {
    return ui.getMazeAgentParams();
  }
  if (activeSimulation === "flocking") {
    return ui.getFlockingParams();
  }
  return ui.getGravityBallParams();
}

function runActiveSimulation(params) {
  if (activeSimulation === "maze_agent") {
    return runMazeAgent(params);
  }
  if (activeSimulation === "flocking") {
    return runFlocking(params);
  }
  return runGravityBall(params);
}

function getActiveSimulationResult() {
  if (activeSimulation === "maze_agent") {
    return getMazeAgentResult();
  }
  if (activeSimulation === "flocking") {
    return getFlockingResult();
  }
  return getGravityBallResult();
}

async function saveCurrentCodexTaskDraft() {
  if (!currentCodexTaskDraft) {
    ui.setCodexTaskStatus("保存できるCodex依頼案がまだありません。");
    return;
  }

  let saved = false;
  ui.setCodexTaskBusy(true);
  try {
    const result = await saveCodexTask(currentCodexTaskDraft);
    currentCodexTaskDraft.task_id = result.task_id;
    currentCodexTaskDraft.created_at = result.created_at;
    currentCodexTaskDraft.simulation_name = result.simulation_name;
    currentCodexTaskDraft.title = result.title;
    saved = true;
    ui.setCodexTaskSaved({
      taskId: result.task_id,
      createdAt: result.created_at,
    });
    await loadCodexTaskHistory();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Codex依頼案の保存に失敗しました。";
    ui.setCodexTaskStatus(message);
    ui.addError(message);
  } finally {
    if (!saved) {
      ui.setCodexTaskBusy(false);
    }
  }
}

async function copyCurrentCodexTaskDraft() {
  if (!currentCodexTaskDraft) {
    ui.setCodexTaskStatus("コピーできるCodex依頼案がまだありません。");
    return;
  }

  try {
    await navigator.clipboard.writeText(currentCodexTaskDraft.codex_task);
    ui.setCodexTaskStatus("コピーしました。");
  } catch {
    ui.selectCodexTaskText();
    ui.setCodexTaskStatus("自動コピーに失敗しました。テキストを選択したので手動でコピーしてください。");
  }
}

async function loadCodexTaskHistory() {
  if (!sessionId) {
    ui.setCodexTaskHistory([]);
    return;
  }

  try {
    const result = await getCodexTasks({ sessionId, limit: 5 });
    const tasks = result.tasks ?? [];
    ui.setCodexTaskHistory(tasks, selectSavedCodexTask);
  } catch (error) {
    console.warn("Failed to load Codex task history", error);
  }
}

async function selectSavedCodexTask(task, { showImplementationStatus = true } = {}) {
  try {
    const detail = await getCodexTask(task.task_id);
    const savedTask = detail.task ?? task;
    currentCodexTaskDraft = {
      task_id: savedTask.task_id,
      created_at: savedTask.created_at,
      session_id: savedTask.session_id,
      source_message: savedTask.source_message,
      simulation_name: savedTask.simulation_name,
      title: savedTask.title,
      experiment_spec: savedTask.experiment_spec ?? {},
      codex_task: savedTask.codex_task,
    };
    ui.showSavedCodexTask(savedTask);
    if (detail.latest_plan) {
      ui.setCodexTaskPlan(detail.latest_plan);
    }
    if (showImplementationStatus) {
      await showCodexImplementationStatus(savedTask.task_id);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Codex依頼案の取得に失敗しました。";
    ui.setCodexTaskStatus(message);
    ui.addError(message);
  }
}

async function resumeAnyCodexImplementationProgress() {
  if (codexImplementationPollId !== null) {
    return;
  }

  try {
    const result = await getCodexImplementationRequests({ status: "in_progress", limit: 1 });
    let request = result.requests?.[0];
    if (!request) {
      const completed = await getCodexImplementationRequests({ status: "completed", limit: 1 });
      request = completed.requests?.[0];
    }
    if (!request?.task_id) {
      return;
    }
    await selectSavedCodexTask(
      {
        task_id: request.task_id,
        created_at: request.requested_at,
        simulation_name: request.simulation_name,
        title: request.title,
      },
      { showImplementationStatus: false }
    );
    const status = await getCodexImplementationStatus({ taskId: request.task_id, tailChars: 12000 });
    ui.setCodexImplementationProgress(status);
    if (["pending", "in_progress"].includes(status.status)) {
      startCodexImplementationPolling(request.task_id);
    }
  } catch (error) {
    console.warn("Failed to resume global Codex implementation progress", error);
  }
}

async function showCodexImplementationStatus(taskId) {
  const status = await getCodexImplementationStatus({ taskId, tailChars: 12000 });
  if (status.status === "not_requested") {
    ui.clearCodexImplementationProgress();
    return;
  }
  ui.setCodexImplementationProgress(status);
  if (["pending", "in_progress"].includes(status.status)) {
    startCodexImplementationPolling(taskId);
  }
}

async function previewCurrentCodexTask() {
  if (!currentCodexTaskDraft?.task_id) {
    ui.setCodexTaskStatus("先にCodex依頼案を保存してください。");
    return;
  }

  ui.setCodexTaskBusy(true);
  let plan = null;
  try {
    plan = await planCodexTask({
      taskId: currentCodexTaskDraft.task_id,
      sessionId,
    });
    ui.setCodexTaskStatus(plan.apply_available ? "適用可能な変更を確認しました。" : "この依頼案は限定適用の対象外です。");
  } catch (error) {
    const message = error instanceof Error ? error.message : "Codex依頼案のプレビューに失敗しました。";
    ui.setCodexTaskStatus(message);
    ui.addError(message);
  } finally {
    ui.setCodexTaskBusy(false);
    if (plan) {
      ui.setCodexTaskPlan(plan);
    }
  }
}

async function applyCurrentCodexTask() {
  if (!currentCodexTaskDraft?.task_id) {
    ui.setCodexTaskStatus("先にCodex依頼案を保存してください。");
    return;
  }

  ui.setCodexTaskBusy(true);
  let result = null;
  try {
    result = await applyCodexTask({ taskId: currentCodexTaskDraft.task_id });
    ui.setCodexTaskStatus("限定適用が完了しました。");
    if (Object.hasOwn(viewers, result.simulation_name)) {
      switchSimulation(result.simulation_name);
      await loadLatestActiveSimulation();
    }
    await loadCodexTaskHistory();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Codex依頼案の適用に失敗しました。";
    ui.setCodexTaskStatus(message);
    ui.addError(message);
  } finally {
    ui.setCodexTaskBusy(false);
    if (result) {
      ui.setCodexTaskApplyResult(result);
    }
  }
}

async function requestCurrentCodexImplementation() {
  if (!currentCodexTaskDraft?.task_id) {
    ui.setCodexTaskStatus("先にCodex依頼案を保存してください。");
    return;
  }

  ui.setCodexTaskBusy(true);
  try {
    const result = await requestCodexImplementation({ taskId: currentCodexTaskDraft.task_id });
    ui.setCodexTaskStatus(`Codex実装待ちに追加しました: ${result.handoff_file}`);
    ui.setCodexImplementationProgress({
      status: result.status,
      updated_at: result.requested_at,
      output_tail: "watcherが起動中なら、まもなくCodex CLIの出力がここに表示されます。",
    });
    startCodexImplementationPolling(currentCodexTaskDraft.task_id);
    await loadCodexTaskHistory();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Codex実装依頼の登録に失敗しました。";
    ui.setCodexTaskStatus(message);
    ui.addError(message);
  } finally {
    ui.setCodexTaskBusy(false);
  }
}

function startCodexImplementationPolling(taskId) {
  stopCodexImplementationPolling();
  codexImplementationPollFailures = 0;

  const poll = async () => {
    try {
      const status = await getCodexImplementationStatus({ taskId, tailChars: 12000 });
      codexImplementationPollFailures = 0;
      ui.setCodexImplementationProgress(status);
      if (["completed", "failed", "not_found"].includes(status.status)) {
        stopCodexImplementationPolling();
        await loadCodexTaskHistory();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Codex実装状況の取得に失敗しました。";
      ui.setCodexTaskStatus(message);
      codexImplementationPollFailures += 1;
      ui.setCodexImplementationProgress({
        status: codexImplementationPollFailures >= 3 ? "status_check_retrying" : "status_check_waiting",
        output_tail: `${message}\nサーバーのリロード中かもしれないため、確認を続けています。`,
      });
    }
  };

  poll();
  codexImplementationPollId = window.setInterval(poll, 3000);
}

function stopCodexImplementationPolling() {
  if (codexImplementationPollId !== null) {
    window.clearInterval(codexImplementationPollId);
    codexImplementationPollId = null;
  }
  codexImplementationPollFailures = 0;
}

async function resetLabToInitialState() {
  const shouldReset = window.confirm(
    "3D-AI Labを初期状態に戻します。見た目の変更と最新シミュレーション結果を既定値に戻し、画面上の会話と依頼案表示をクリアします。よろしいですか？"
  );
  if (!shouldReset) {
    return;
  }

  ui.setLabResetBusy(true);
  ui.setSimulationBusy(true);
  try {
    await resetLabState();
    stopCodexImplementationPolling();
    currentCodexTaskDraft = null;
    sessionId = null;
    window.localStorage.removeItem(sessionKey);
    Object.values(viewers).forEach((viewer) => {
      viewer.setPlaying(false);
      viewer.reset();
      viewer.setSpeed(1);
    });
    resetCamera();
    ui.resetSimulationInputs();
    ui.resetCodexTaskPanel();
    ui.resetChat("3D-AI Labを初期状態に戻しました。ここでは小さな3D実験の相談ができます。");
    ui.setSpeech("初期状態に戻しました。");
    switchSimulation("gravity_ball");
    await loadLatestActiveSimulation();
  } catch (error) {
    const message = error instanceof Error ? error.message : "初期状態へのリセットに失敗しました。";
    ui.addError(message);
    ui.setSpeech("初期状態へのリセットに失敗しました。");
  } finally {
    ui.setSimulationBusy(false);
    ui.setLabResetBusy(false);
  }
}

function resetCamera() {
  camera.position.set(3.6, 3.0, 6.2);
  controls.target.set(0, 1.2, 0);
  controls.update();
}

function formatNumber(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return Number.parseFloat(value.toFixed(3)).toString();
}
