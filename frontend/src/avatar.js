import * as THREE from "three";

export function createLabAssistant() {
  const group = new THREE.Group();
  group.name = "Lab Assistant";

  const bodyMaterial = new THREE.MeshStandardMaterial({
    color: 0x45c4a0,
    roughness: 0.65,
    metalness: 0.08,
  });
  const headMaterial = new THREE.MeshStandardMaterial({
    color: 0xf2d2b6,
    roughness: 0.7,
  });
  const darkMaterial = new THREE.MeshStandardMaterial({
    color: 0x1c2530,
    roughness: 0.5,
  });
  const accentMaterial = new THREE.MeshStandardMaterial({
    color: 0xffd166,
    roughness: 0.45,
  });

  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.55, 1.05, 8, 18), bodyMaterial);
  body.position.y = 1.35;
  group.add(body);

  const head = new THREE.Mesh(new THREE.SphereGeometry(0.45, 32, 20), headMaterial);
  head.name = "assistant-head";
  head.position.y = 2.35;
  group.add(head);

  const visor = new THREE.Mesh(new THREE.BoxGeometry(0.64, 0.12, 0.08), darkMaterial);
  visor.position.set(0, 2.42, 0.38);
  group.add(visor);

  const antennaStem = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.35, 12), darkMaterial);
  antennaStem.position.y = 2.86;
  group.add(antennaStem);

  const antennaTip = new THREE.Mesh(new THREE.SphereGeometry(0.07, 16, 10), accentMaterial);
  antennaTip.name = "assistant-antenna-tip";
  antennaTip.position.y = 3.06;
  group.add(antennaTip);

  const leftArm = createArm(bodyMaterial);
  leftArm.position.set(-0.68, 1.48, 0);
  leftArm.rotation.z = -0.26;
  group.add(leftArm);

  const rightArm = createArm(bodyMaterial);
  rightArm.position.set(0.68, 1.48, 0);
  rightArm.rotation.z = 0.26;
  group.add(rightArm);

  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.72, 0.8, 0.2, 32), darkMaterial);
  base.position.y = 0.36;
  group.add(base);

  group.position.set(0, 0, 0);

  return group;
}

export function animateLabAssistant(assistant, elapsedSeconds) {
  assistant.position.y = Math.sin(elapsedSeconds * 1.8) * 0.06;
  assistant.rotation.y = Math.sin(elapsedSeconds * 0.7) * 0.18;

  const antenna = assistant.children.find((child) => child.name === "assistant-antenna-tip");
  if (antenna) {
    antenna.scale.setScalar(1 + Math.sin(elapsedSeconds * 4) * 0.04);
  }
}

function createArm(material) {
  const arm = new THREE.Group();
  const upper = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.08, 0.68, 14), material);
  upper.rotation.z = Math.PI / 12;
  upper.position.y = -0.28;
  arm.add(upper);

  const hand = new THREE.Mesh(new THREE.SphereGeometry(0.1, 16, 10), material);
  hand.position.y = -0.66;
  arm.add(hand);

  return arm;
}
