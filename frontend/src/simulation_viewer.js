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

