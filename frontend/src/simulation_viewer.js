import * as THREE from "three";

export class GravityBallViewer {
  constructor(scene) {
    this.scene = scene;
    this.group = new THREE.Group();
    this.group.name = "gravity-ball-viewer";
    this.scene.add(this.group);

    this.result = null;
    this.ball = null;
    this.frameIndex = 0;
    this.frameCursor = 0;
    this.playing = false;
    this.speed = 1;
  }

  loadResult(result) {
    this.clear();
    this.result = result;
    this.frameIndex = 0;
    this.frameCursor = 0;
    this.playing = false;

    const ballObject = result.objects.find((object) => object.id === "ball_1");
    const radius = ballObject?.radius ?? 0.3;
    const color = new THREE.Color(ballObject?.color ?? "#ffd166");
    const ballMaterial = new THREE.MeshStandardMaterial({
      color,
      roughness: 0.45,
      metalness: 0.03,
      emissive: color.clone().multiplyScalar(0.12),
    });

    this.ball = new THREE.Mesh(new THREE.SphereGeometry(radius, 32, 20), ballMaterial);
    this.ball.name = "gravity-ball";
    this.ball.castShadow = true;
    this.group.add(this.ball);

    this.addTrajectory(result.frames);
    this.applyFrame(0);
  }

  clear() {
    while (this.group.children.length > 0) {
      const child = this.group.children.pop();
      child.traverse?.((object) => {
        object.geometry?.dispose?.();
        object.material?.dispose?.();
      });
    }
    this.ball = null;
  }

  setVisible(visible) {
    this.group.visible = visible;
  }

  setPlaying(playing) {
    this.playing = playing;
  }

  togglePlaying() {
    this.playing = !this.playing;
    return this.playing;
  }

  setSpeed(speed) {
    this.speed = Number(speed) || 1;
  }

  reset() {
    this.frameIndex = 0;
    this.frameCursor = 0;
    this.applyFrame(0);
  }

  step() {
    if (!this.result?.frames?.length) {
      return;
    }
    this.playing = false;
    this.frameIndex = Math.min(this.frameIndex + 1, this.result.frames.length - 1);
    this.frameCursor = this.frameIndex;
    this.applyFrame(this.frameIndex);
  }

  update(deltaSeconds) {
    if (!this.playing || !this.result?.frames?.length) {
      return;
    }

    const dt = this.result.meta?.dt ?? 0.016;
    this.frameCursor += (deltaSeconds / dt) * this.speed;
    if (this.frameCursor >= this.result.frames.length - 1) {
      this.frameCursor = this.result.frames.length - 1;
      this.playing = false;
    }

    this.frameIndex = Math.floor(this.frameCursor);
    this.applyFrame(this.frameIndex);
  }

  getStatus() {
    const frameCount = this.result?.frames?.length ?? 0;
    const summary = this.result?.summary;
    return {
      loaded: frameCount > 0,
      playing: this.playing,
      frameIndex: this.frameIndex,
      frameCount,
      summary,
      parameters: this.result?.meta?.parameters,
    };
  }

  applyFrame(index) {
    if (!this.ball || !this.result?.frames?.length) {
      return;
    }

    const frame = this.result.frames[index];
    const position = frame?.objects?.ball_1?.position;
    if (!position) {
      return;
    }

    this.ball.position.set(position[0], position[1], position[2]);
  }

  addTrajectory(frames) {
    if (!frames?.length) {
      return;
    }

    const points = frames
      .filter((_, index) => index % 4 === 0)
      .map((frame) => {
        const [x, y, z] = frame.objects.ball_1.position;
        return new THREE.Vector3(x, y, z);
      });

    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const material = new THREE.LineBasicMaterial({
      color: 0xffd166,
      transparent: true,
      opacity: 0.72,
    });
    const line = new THREE.Line(geometry, material);
    line.name = "gravity-ball-trajectory";
    this.group.add(line);
  }
}

export class MazeAgentViewer {
  constructor(scene) {
    this.scene = scene;
    this.group = new THREE.Group();
    this.group.name = "maze-agent-viewer";
    this.group.position.set(0.9, 0, -0.15);
    this.group.scale.setScalar(0.82);
    this.scene.add(this.group);

    this.result = null;
    this.agent = null;
    this.frameIndex = 0;
    this.frameCursor = 0;
    this.playing = false;
    this.speed = 1;
  }

  loadResult(result) {
    this.clear();
    this.result = result;
    this.frameIndex = 0;
    this.frameCursor = 0;
    this.playing = false;

    const gridSize = result.summary?.grid_size ?? result.meta?.parameters?.grid_size ?? 7;
    this.addFloor(gridSize);
    this.addObjects(result.objects ?? [], gridSize);
    this.addAgent(result.objects?.find((object) => object.id === "agent_1"));
    this.addRoute(result.objects?.find((object) => object.id === "maze_path"), gridSize);
    this.applyFrame(0);
  }

  clear() {
    while (this.group.children.length > 0) {
      const child = this.group.children.pop();
      child.traverse?.((object) => {
        object.geometry?.dispose?.();
        object.material?.dispose?.();
      });
    }
    this.agent = null;
  }

  setVisible(visible) {
    this.group.visible = visible;
  }

  setPlaying(playing) {
    this.playing = playing;
  }

  togglePlaying() {
    this.playing = !this.playing;
    return this.playing;
  }

  setSpeed(speed) {
    this.speed = Number(speed) || 1;
  }

  reset() {
    this.frameIndex = 0;
    this.frameCursor = 0;
    this.applyFrame(0);
  }

  step() {
    if (!this.result?.frames?.length) {
      return;
    }
    this.playing = false;
    this.frameIndex = Math.min(this.frameIndex + 1, this.result.frames.length - 1);
    this.frameCursor = this.frameIndex;
    this.applyFrame(this.frameIndex);
  }

  update(deltaSeconds) {
    if (!this.playing || !this.result?.frames?.length) {
      return;
    }

    const dt = this.result.meta?.dt ?? 0.08;
    this.frameCursor += (deltaSeconds / dt) * this.speed;
    if (this.frameCursor >= this.result.frames.length - 1) {
      this.frameCursor = this.result.frames.length - 1;
      this.playing = false;
    }

    this.frameIndex = Math.floor(this.frameCursor);
    this.applyFrame(this.frameIndex);
  }

  getStatus() {
    const frameCount = this.result?.frames?.length ?? 0;
    return {
      loaded: frameCount > 0,
      playing: this.playing,
      frameIndex: this.frameIndex,
      frameCount,
      summary: this.result?.summary,
      parameters: this.result?.meta?.parameters,
    };
  }

  applyFrame(index) {
    if (!this.agent || !this.result?.frames?.length) {
      return;
    }

    const frame = this.result.frames[index];
    const position = frame?.objects?.agent_1?.position;
    if (!position) {
      return;
    }

    this.agent.position.set(position[0], position[1], position[2]);
  }

  addFloor(gridSize) {
    const floorGroup = new THREE.Group();
    floorGroup.name = "maze-floor";

    const tileGeometry = new THREE.BoxGeometry(0.92, 0.04, 0.92);
    const tileMaterial = new THREE.MeshStandardMaterial({
      color: 0x1b242d,
      roughness: 0.82,
      metalness: 0.03,
    });

    for (let x = 0; x < gridSize; x += 1) {
      for (let z = 0; z < gridSize; z += 1) {
        const tile = new THREE.Mesh(tileGeometry, tileMaterial);
        const [worldX, , worldZ] = cellToWorld([x, z], gridSize);
        tile.position.set(worldX, 0.03, worldZ);
        tile.receiveShadow = true;
        floorGroup.add(tile);
      }
    }

    this.group.add(floorGroup);
  }

  addObjects(objects, gridSize) {
    objects.forEach((object) => {
      if (object.type === "wall") {
        const wall = new THREE.Mesh(
          new THREE.BoxGeometry(0.86, object.height ?? 0.76, 0.86),
          new THREE.MeshStandardMaterial({
            color: new THREE.Color(object.color ?? "#566273"),
            roughness: 0.68,
            metalness: 0.02,
          })
        );
        const [worldX, , worldZ] = cellToWorld(object.cell, gridSize);
        wall.position.set(worldX, (object.height ?? 0.76) / 2 + 0.05, worldZ);
        wall.castShadow = true;
        wall.receiveShadow = true;
        this.group.add(wall);
      }

      if (object.type === "marker") {
        const marker = new THREE.Mesh(
          new THREE.CylinderGeometry(0.34, 0.34, 0.06, 28),
          new THREE.MeshStandardMaterial({
            color: new THREE.Color(object.color ?? "#ffffff"),
            emissive: new THREE.Color(object.color ?? "#ffffff").multiplyScalar(0.18),
            roughness: 0.45,
          })
        );
        const [worldX, , worldZ] = cellToWorld(object.cell, gridSize);
        marker.position.set(worldX, 0.09, worldZ);
        marker.castShadow = true;
        this.group.add(marker);
      }
    });
  }

  addAgent(agentObject) {
    const color = new THREE.Color(agentObject?.color ?? "#72a7ff");
    const agentGroup = new THREE.Group();
    agentGroup.name = "maze-agent";

    const body = new THREE.Mesh(
      new THREE.SphereGeometry(agentObject?.radius ?? 0.22, 28, 18),
      new THREE.MeshStandardMaterial({
        color,
        roughness: 0.35,
        metalness: 0.04,
        emissive: color.clone().multiplyScalar(0.16),
      })
    );
    body.castShadow = true;
    agentGroup.add(body);

    const direction = new THREE.Mesh(
      new THREE.ConeGeometry(0.11, 0.22, 18),
      new THREE.MeshStandardMaterial({ color: 0xf2f5f7, roughness: 0.42 })
    );
    direction.rotation.x = Math.PI / 2;
    direction.position.set(0, 0.02, 0.22);
    direction.castShadow = true;
    agentGroup.add(direction);

    this.agent = agentGroup;
    this.group.add(agentGroup);
  }

  addRoute(pathObject, gridSize) {
    const cells = pathObject?.cells ?? [];
    if (!cells.length) {
      return;
    }

    const routeMaterial = new THREE.MeshStandardMaterial({
      color: new THREE.Color(pathObject.color ?? "#45c4a0"),
      emissive: new THREE.Color(pathObject.color ?? "#45c4a0").multiplyScalar(0.18),
      transparent: true,
      opacity: 0.58,
      roughness: 0.6,
    });
    const routeGeometry = new THREE.CylinderGeometry(0.28, 0.28, 0.035, 24);
    cells.forEach((cell) => {
      const [x, , z] = cellToWorld(cell, gridSize);
      const marker = new THREE.Mesh(routeGeometry, routeMaterial);
      marker.position.set(x, 0.115, z);
      this.group.add(marker);
    });

    const points = cells.map((cell) => {
      const [x, , z] = cellToWorld(cell, gridSize);
      return new THREE.Vector3(x, 0.16, z);
    });
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const material = new THREE.LineBasicMaterial({
      color: new THREE.Color(pathObject.color ?? "#45c4a0"),
      transparent: true,
      opacity: 0.86,
    });
    const line = new THREE.Line(geometry, material);
    line.name = "maze-route";
    this.group.add(line);
  }
}

function cellToWorld(cell, gridSize) {
  const offset = (gridSize - 1) / 2;
  return [cell[0] - offset, 0, cell[1] - offset];
}
