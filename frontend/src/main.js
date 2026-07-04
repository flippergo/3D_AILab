import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { getGravityBallResult, getMazeAgentResult, runGravityBall, runMazeAgent, sendChatMessage } from "./api_client.js";
import { animateLabAssistant, createLabAssistant } from "./avatar.js";
import { setupLabUi } from "./lab_ui.js";
import { GravityBallViewer, MazeAgentViewer } from "./simulation_viewer.js";

const canvas = document.querySelector("#scene");
const sessionKey = "3d-ai-lab-session-id";
let sessionId = window.localStorage.getItem(sessionKey);

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
const viewers = {
  gravity_ball: gravityBallViewer,
  maze_agent: mazeAgentViewer,
};
let activeSimulation = "gravity_ball";
mazeAgentViewer.setVisible(false);

const ui = setupLabUi({
  async onSubmit(message) {
    try {
      const response = await sendChatMessage({ message, sessionId });
      sessionId = response.session_id;
      window.localStorage.setItem(sessionKey, sessionId);
      ui.addAssistantMessage(response.reply);
      if (response.experiment_spec) {
        ui.addAssistantMessage(formatExperimentSpec(response.experiment_spec));
      }
      if (response.codex_task) {
        ui.addAssistantMessage(`Codex向けタスク案:\n${response.codex_task}`);
      }
      ui.setSpeech(response.reply);

      if (response.suggested_action === "run_gravity_ball") {
        switchSimulation("gravity_ball");
        ui.applyGravityBallParams(response.simulation_params ?? {});
        ui.addAssistantMessage("gravity_ball を指定条件で実行します。");
        await runActiveSimulationFromUi();
      }

      if (response.suggested_action === "run_maze_agent") {
        switchSimulation("maze_agent");
        ui.addAssistantMessage("maze_agent を軽量探索で実行します。");
        await runActiveSimulationFromUi();
      }
    } catch (error) {
      const messageText = error instanceof Error ? error.message : "チャット送信に失敗しました。";
      ui.addError(messageText);
      ui.setSpeech("通信に失敗しました。サーバーが起動しているか確認してください。");
    }
  },
});

ui.addAssistantMessage("こんにちは。ここでは小さな3D実験の相談ができます。");
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

resize();
window.addEventListener("resize", resize);
requestAnimationFrame(tick);
loadLatestActiveSimulation();

function tick() {
  const delta = clock.getDelta();
  const elapsed = clock.elapsedTime;
  animateLabAssistant(assistant, elapsed);
  gravityBallViewer.update(delta);
  mazeAgentViewer.update(delta);
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
  activeSimulation = simulationName === "maze_agent" ? "maze_agent" : "gravity_ball";
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
    const result =
      activeSimulation === "maze_agent"
        ? await runMazeAgent(ui.getMazeAgentParams())
        : await runGravityBall(ui.getGravityBallParams());
    getActiveViewer().loadResult(result);
    getActiveViewer().setPlaying(true);
    ui.setPlayButton(true);
    ui.setSpeech(
      activeSimulation === "maze_agent"
        ? "maze_agent を実行しました。エージェントが迷路を進む様子を再生します。"
        : "gravity_ball を実行しました。ボールの落下と反発を再生します。"
    );
    updateSimulationStatus();
  } catch (error) {
    const message = error instanceof Error ? error.message : "シミュレーションの実行に失敗しました。";
    ui.addError(message);
    ui.setSpeech("シミュレーションの実行に失敗しました。");
  } finally {
    ui.setSimulationBusy(false);
  }
}

async function loadLatestActiveSimulation() {
  ui.setSimulationBusy(true);
  try {
    const result = activeSimulation === "maze_agent" ? await getMazeAgentResult() : await getGravityBallResult();
    getActiveViewer().loadResult(result);
    if (activeSimulation === "gravity_ball") {
      ui.applyGravityBallParams(result.meta?.parameters ?? {});
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
  if (activeSimulation === "maze_agent") {
    ui.setSimulationStatus(
      [
        `frame ${frame}/${status.frameCount}`,
        `迷路 ${summary.grid_size ?? params.grid_size ?? 7}x${summary.grid_size ?? params.grid_size ?? 7} / 経路 ${summary.path_length ?? "-"} マス`,
        `探索 ${summary.visited_count ?? "-"} マス / ゴール ${summary.reached_goal ? "到達" : "未到達"} / 再生 ${status.playing ? "中" : "停止"}`,
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

function formatNumber(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "-";
  }
  return Number.parseFloat(value.toFixed(3)).toString();
}

function formatExperimentSpec(spec) {
  const parameters = spec.parameters
    ? Object.entries(spec.parameters)
        .map(([key, value]) => `${key}: ${value}`)
        .join(" / ")
    : "未設定";
  const observations = Array.isArray(spec.observations) ? spec.observations.join("、") : "未設定";

  return [
    `実験案: ${spec.title ?? "未設定"}`,
    `目的: ${spec.goal ?? "未設定"}`,
    `対象: ${spec.simulation_name ?? "未設定"}`,
    `変更できる値: ${parameters}`,
    `観察ポイント: ${observations}`,
  ].join("\n");
}
