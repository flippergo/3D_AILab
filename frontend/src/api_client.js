export async function sendChatMessage({ message, sessionId }) {
  const response = await fetch("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || "チャット送信に失敗しました。");
  }

  return response.json();
}

export async function runGravityBall(params) {
  const response = await fetch("/simulations/gravity_ball/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || "シミュレーションの実行に失敗しました。");
  }

  return response.json();
}

export async function getGravityBallResult() {
  const response = await fetch("/simulations/gravity_ball/result");

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || "シミュレーション結果の読み込みに失敗しました。");
  }

  return response.json();
}

export async function runMazeAgent(params = {}) {
  const response = await fetch("/simulations/maze_agent/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || "迷路シミュレーションの実行に失敗しました。");
  }

  return response.json();
}

export async function getMazeAgentResult() {
  const response = await fetch("/simulations/maze_agent/result");

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || "迷路シミュレーション結果の読み込みに失敗しました。");
  }

  return response.json();
}

export async function runFlocking(params = {}) {
  const response = await fetch("/simulations/flocking/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || "群れシミュレーションの実行に失敗しました。");
  }

  return response.json();
}

export async function getFlockingResult() {
  const response = await fetch("/simulations/flocking/result");

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail || "群れシミュレーション結果の読み込みに失敗しました。");
  }

  return response.json();
}

async function readErrorDetail(response) {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (payload.detail) {
      return JSON.stringify(payload.detail);
    }
    return JSON.stringify(payload);
  } catch {
    return "";
  }
}
