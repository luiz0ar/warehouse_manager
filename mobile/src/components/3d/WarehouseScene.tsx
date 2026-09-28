"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import * as BufferGeometryUtils from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { useWarehouseStore } from "@/store/useWarehouseStore";
import { SlotSnapshot } from "@/types/warehouse";

interface WarehouseSceneProps {
  onSlotClick?: (slot: SlotSnapshot) => void;
}

function createRoundedBoxEdgesGeometry(
  w: number,
  h: number,
  d: number,
  r: number,
  segments: number = 3
): THREE.BufferGeometry {
  const points: number[] = [];
  const hw = w / 2 - r;
  const hh = h / 2 - r;
  const hd = d / 2 - r;

  for (const sy of [-1, 1]) {
    for (const sz of [-1, 1]) {
      points.push(-hw, sy * (hh + r), sz * (hd + r));
      points.push( hw, sy * (hh + r), sz * (hd + r));
    }
  }

  for (const sx of [-1, 1]) {
    for (const sz of [-1, 1]) {
      points.push(sx * (hw + r), -hh, sz * (hd + r));
      points.push(sx * (hw + r),  hh, sz * (hd + r));
    }
  }

  for (const sx of [-1, 1]) {
    for (const sy of [-1, 1]) {
      points.push(sx * (hw + r), sy * (hh + r), -hd);
      points.push(sx * (hw + r), sy * (hh + r),  hd);
    }
  }

  for (const sx of [-1, 1]) {
    for (const sy of [-1, 1]) {
      for (const sz of [-1, 1]) {
        const cx = sx * hw;
        const cy = sy * hh;
        const cz = sz * hd;

        for (let i = 0; i < segments; i++) {
          const a1 = (i / segments) * (Math.PI / 2);
          const a2 = ((i + 1) / segments) * (Math.PI / 2);
          points.push(
            cx + sx * r * Math.sin(a1), cy + sy * r * Math.cos(a1), sz * (hd + r),
            cx + sx * r * Math.sin(a2), cy + sy * r * Math.cos(a2), sz * (hd + r)
          );
        }

        for (let i = 0; i < segments; i++) {
          const a1 = (i / segments) * (Math.PI / 2);
          const a2 = ((i + 1) / segments) * (Math.PI / 2);
          points.push(
            cx + sx * r * Math.sin(a1), sy * (hh + r), cz + sz * r * Math.cos(a1),
            cx + sx * r * Math.sin(a2), sy * (hh + r), cz + sz * r * Math.cos(a2)
          );
        }

        for (let i = 0; i < segments; i++) {
          const a1 = (i / segments) * (Math.PI / 2);
          const a2 = ((i + 1) / segments) * (Math.PI / 2);
          points.push(
            sx * (hw + r), cy + sy * r * Math.sin(a1), cz + sz * r * Math.cos(a1),
            sx * (hw + r), cy + sy * r * Math.sin(a2), cz + sz * r * Math.cos(a2)
          );
        }
      }
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
  return geometry;
}

export const WarehouseScene: React.FC<WarehouseSceneProps> = ({ onSlotClick }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const warehouse = useWarehouseStore((state) => state.warehouse);
  const highlightedSlotCoords = useWarehouseStore(
    (state) => state.highlightedSlotCoords
  );
  const cameraFocus = useWarehouseStore((state) => state.cameraFocus);
  const selectSlot = useWarehouseStore((state) => state.selectSlot);

  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);

  // Instanced Meshes independentes para Livres e Ocupados (permite materiais e opacidades distintas)
  const freeMeshRef = useRef<THREE.InstancedMesh | null>(null);
  const occupiedMeshRef = useRef<THREE.InstancedMesh | null>(null);
  const freeMaterialRef = useRef<THREE.MeshStandardMaterial | null>(null);
  const occupiedMaterialRef = useRef<THREE.MeshStandardMaterial | null>(null);

  // Mapeamentos de instâncias para SlotSnapshot
  const freeSlotsMapRef = useRef<SlotSnapshot[]>([]);
  const occupiedSlotsMapRef = useRef<SlotSnapshot[]>([]);

  // Outlines / Edges com Glow por categoria (linha nítida + halo aditivo)
  const edgesGroupRef = useRef<THREE.Group | null>(null);
  const freeEdgesMatRef = useRef<THREE.LineBasicMaterial | null>(null);
  const freeEdgesGlowMatRef = useRef<THREE.LineBasicMaterial | null>(null);
  const occupiedEdgesMatRef = useRef<THREE.LineBasicMaterial | null>(null);
  const occupiedEdgesGlowMatRef = useRef<THREE.LineBasicMaterial | null>(null);

  // Controles de Câmera
  const targetLookAtRef = useRef<THREE.Vector3>(new THREE.Vector3(0, 0, 0));
  const currentLookAtRef = useRef<THREE.Vector3>(new THREE.Vector3(0, 0, 0));
  const targetCameraPosRef = useRef<THREE.Vector3 | null>(null);
  const pointerDownPos = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Grupo de Destaque Dedicado para o Lote Focado (Amarelo Glow com Raio-X)
  const highlightGroupRef = useRef<THREE.Group | null>(null);
  const highlightMeshRef = useRef<THREE.Mesh | null>(null);
  const highlightWireframeRef = useRef<THREE.LineSegments | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // 1. Scene com fundo escuro profundo ultra-clean (#07080c)
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07080c);
    sceneRef.current = scene;

    // 2. Camera Isométrica
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 1000);
    camera.position.set(16, 14, 18);
    cameraRef.current = camera;

    // 3. Renderer com suporte a ACES Filmic Tone Mapping
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;
    container.innerHTML = "";
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2 - 0.05;
    controls.minDistance = 3;
    controls.maxDistance = 60;
    controls.target.set(3, 1.5, 2);
    targetLookAtRef.current.set(3, 1.5, 2);
    currentLookAtRef.current.set(3, 1.5, 2);
    controlsRef.current = controls;

    // 5. Iluminação Elegante
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.4);
    dirLight1.position.set(20, 30, 20);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x38bdf8, 0.5);
    dirLight2.position.set(-20, -10, -20);
    scene.add(dirLight2);

    // 6. Grid do Chão Elegante
    const gridHelper = new THREE.GridHelper(50, 50, 0x161822, 0x0f1118);
    gridHelper.position.y = -0.51;
    scene.add(gridHelper);

    // 7. Grupo de Destaque Dedicado para o Lote Focado (Amarelo Glow com Raio-X)
    const highlightGroup = new THREE.Group();
    highlightGroup.visible = false;

    // Corpo do cubo focado: amarelo sólido luminoso (cor sólida conforme solicitado)
    const roundedHighlightGeo = new RoundedBoxGeometry(0.92, 0.92, 0.92, 4, 0.08);
    const highlightMat = new THREE.MeshStandardMaterial({
      color: 0xfacc15,
      emissive: 0xf59e0b,
      emissiveIntensity: 0.65,
      roughness: 0.25,
      metalness: 0.08,
      transparent: false,
      depthWrite: true,
    });
    const highlightMesh = new THREE.Mesh(roundedHighlightGeo, highlightMat);
    highlightGroup.add(highlightMesh);
    highlightMeshRef.current = highlightMesh;

    // Outline Glow vivo amarelo arredondado com depthTest: false
    const highlightOutlineGeo = createRoundedBoxEdgesGeometry(0.95, 0.95, 0.95, 0.08, 4);
    const highlightBoxMat = new THREE.LineBasicMaterial({
      color: 0xffea00,
      linewidth: 3,
      depthTest: false,
      transparent: true,
      opacity: 0.98,
    });
    const highlightWireframe = new THREE.LineSegments(highlightOutlineGeo, highlightBoxMat);
    highlightWireframe.renderOrder = 999;
    highlightGroup.add(highlightWireframe);
    highlightWireframeRef.current = highlightWireframe;

    // Farol vertical luminoso (Beacon)
    const beaconPoints = [new THREE.Vector3(0, 0.5, 0), new THREE.Vector3(0, 4.2, 0)];
    const beaconGeo = new THREE.BufferGeometry().setFromPoints(beaconPoints);
    const beaconMat = new THREE.LineBasicMaterial({
      color: 0xfacc15,
      linewidth: 2,
      depthTest: false,
      transparent: true,
      opacity: 0.85,
    });
    const beacon = new THREE.Line(beaconGeo, beaconMat);
    beacon.renderOrder = 999;
    highlightGroup.add(beacon);

    scene.add(highlightGroup);
    highlightGroupRef.current = highlightGroup;

    // 8. Raycaster para Toque / Click
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handlePointerDown = (e: PointerEvent) => {
      pointerDownPos.current = { x: e.clientX, y: e.clientY };
    };

    const handlePointerUp = (e: PointerEvent) => {
      const dist = Math.hypot(
        e.clientX - pointerDownPos.current.x,
        e.clientY - pointerDownPos.current.y
      );
      if (dist > 6) return;

      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);

      const targetMeshes: THREE.InstancedMesh[] = [];
      if (freeMeshRef.current) targetMeshes.push(freeMeshRef.current);
      if (occupiedMeshRef.current) targetMeshes.push(occupiedMeshRef.current);

      if (targetMeshes.length > 0) {
        const intersects = raycaster.intersectObjects(targetMeshes);
        if (intersects.length > 0) {
          const hit = intersects[0];
          const instanceId = hit.instanceId;
          if (instanceId !== undefined) {
            let slot: SlotSnapshot | undefined;
            if (hit.object === freeMeshRef.current) {
              slot = freeSlotsMapRef.current[instanceId];
            } else if (hit.object === occupiedMeshRef.current) {
              slot = occupiedSlotsMapRef.current[instanceId];
            }
            if (slot) {
              selectSlot(slot);
              if (onSlotClick) onSlotClick(slot);
            }
          }
        }
      }
    };

    const domElement = renderer.domElement;
    domElement.addEventListener("pointerdown", handlePointerDown);
    domElement.addEventListener("pointerup", handlePointerUp);

    // 9. Loop de Animação com Pulso Amarelo e Transparência
    let animationFrameId: number;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = performance.now() * 0.001;

      // Interpolação suave do alvo da câmera
      if (targetLookAtRef.current && controls) {
        currentLookAtRef.current.lerp(targetLookAtRef.current, 0.06);
        controls.target.copy(currentLookAtRef.current);
      }

      // Voo suave da câmera até o lote
      if (targetCameraPosRef.current && camera) {
        camera.position.lerp(targetCameraPosRef.current, 0.05);
        if (camera.position.distanceTo(targetCameraPosRef.current) < 0.2) {
          targetCameraPosRef.current = null;
        }
      }

      // Transparência suave dos demais blocos e outlines durante o foco
      const isHighlightActive = highlightGroupRef.current?.visible;

      // Corpo dos blocos livres: cinza com fundo bem transparente (0.16 normal, 0.04 quando em foco)
      if (freeMaterialRef.current) {
        const targetFreeOpacity = isHighlightActive ? 0.04 : 0.16;
        freeMaterialRef.current.opacity = THREE.MathUtils.lerp(
          freeMaterialRef.current.opacity,
          targetFreeOpacity,
          0.08
        );
      }

      // Corpo dos blocos ocupados: cor sólida (1.0) quando normal; baixa opacidade (0.12) quando em foco para revelar o alvo
      if (occupiedMaterialRef.current) {
        const targetOccOpacity = isHighlightActive ? 0.12 : 1.0;
        occupiedMaterialRef.current.opacity = THREE.MathUtils.lerp(
          occupiedMaterialRef.current.opacity,
          targetOccOpacity,
          0.08
        );
        occupiedMaterialRef.current.depthWrite = occupiedMaterialRef.current.opacity > 0.85;
      }

      // Outlines dos blocos livres: contorno visível com glow
      if (freeEdgesMatRef.current) {
        const targetEdgeOpacity = isHighlightActive ? 0.10 : 0.48;
        freeEdgesMatRef.current.opacity = THREE.MathUtils.lerp(
          freeEdgesMatRef.current.opacity,
          targetEdgeOpacity,
          0.08
        );
      }
      if (freeEdgesGlowMatRef.current) {
        const targetEdgeGlowOpacity = isHighlightActive ? 0.05 : 0.22;
        freeEdgesGlowMatRef.current.opacity = THREE.MathUtils.lerp(
          freeEdgesGlowMatRef.current.opacity,
          targetEdgeGlowOpacity,
          0.08
        );
      }

      // Outlines dos blocos ocupados: neon vermelho vibrante
      if (occupiedEdgesMatRef.current) {
        const targetOccEdgeOpacity = isHighlightActive ? 0.18 : 0.95;
        occupiedEdgesMatRef.current.opacity = THREE.MathUtils.lerp(
          occupiedEdgesMatRef.current.opacity,
          targetOccEdgeOpacity,
          0.08
        );
      }
      if (occupiedEdgesGlowMatRef.current) {
        const targetOccGlowOpacity = isHighlightActive ? 0.10 : 0.55;
        occupiedEdgesGlowMatRef.current.opacity = THREE.MathUtils.lerp(
          occupiedEdgesGlowMatRef.current.opacity,
          targetOccGlowOpacity,
          0.08
        );
      }

      // Efeito de pulso no lote selecionado
      if (highlightGroupRef.current && highlightGroupRef.current.visible) {
        const pulse = 0.5 + 0.5 * Math.sin(elapsedTime * 6);
        if (highlightMeshRef.current) {
          const mat = highlightMeshRef.current.material as THREE.MeshStandardMaterial;
          mat.emissiveIntensity = 0.6 + 0.5 * pulse;
        }
        if (highlightWireframeRef.current) {
          const wireScale = 1.0 + 0.04 * Math.sin(elapsedTime * 6);
          highlightWireframeRef.current.scale.set(wireScale, wireScale, wireScale);
        }
      }

      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      domElement.removeEventListener("pointerdown", handlePointerDown);
      domElement.removeEventListener("pointerup", handlePointerUp);
      cancelAnimationFrame(animationFrameId);
      renderer.dispose();
      scene.clear();
    };
  }, [selectSlot, onSlotClick]);

  // Atualização da Geometria: Cubos Arredondados com Transparência e Outline Glow
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !warehouse) return;

    // Limpa meshes anteriores
    if (freeMeshRef.current) {
      scene.remove(freeMeshRef.current);
      freeMeshRef.current.geometry.dispose();
      (freeMeshRef.current.material as THREE.Material).dispose();
      freeMeshRef.current = null;
    }
    if (occupiedMeshRef.current) {
      scene.remove(occupiedMeshRef.current);
      occupiedMeshRef.current.geometry.dispose();
      (occupiedMeshRef.current.material as THREE.Material).dispose();
      occupiedMeshRef.current = null;
    }

    if (edgesGroupRef.current) {
      scene.remove(edgesGroupRef.current);
      edgesGroupRef.current.traverse((obj) => {
        if (obj instanceof THREE.LineSegments) {
          obj.geometry.dispose();
          (obj.material as THREE.Material).dispose();
        }
      });
      edgesGroupRef.current = null;
    }

    const prevDock = scene.getObjectByName("dock_group");
    if (prevDock) scene.remove(prevDock);

    const totalSlots = warehouse.slots.length;
    if (totalSlots === 0) return;

    // 1. Geometria Arredondada Suave
    const cubeSize = 0.88;
    const cornerRadius = 0.08;
    const bodyGeometry = new RoundedBoxGeometry(cubeSize, cubeSize, cubeSize, 4, cornerRadius);

    // Geometria de contorno arredondado de alta fidelidade
    const outlineGeo = createRoundedBoxEdgesGeometry(cubeSize, cubeSize, cubeSize, cornerRadius, 3);
    const outlineGlowGeo = createRoundedBoxEdgesGeometry(
      cubeSize * 1.018,
      cubeSize * 1.018,
      cubeSize * 1.018,
      cornerRadius * 1.018,
      3
    );

    // 2. Separação de Slots Livres e Ocupados
    const freeSlots: { slot: SlotSnapshot; matrix: THREE.Matrix4 }[] = [];
    const occupiedSlots: { slot: SlotSnapshot; matrix: THREE.Matrix4 }[] = [];

    const dummy = new THREE.Object3D();
    const midStreet = Math.max(1, Math.floor(warehouse.total_streets / 2));
    const aisleGap = 1.2;
    const streetSpacing = 1.1;
    const colSpacing = 1.1;
    const levelSpacing = 1.05;

    let highlightedPos: THREE.Vector3 | null = null;

    warehouse.slots.forEach((slot) => {
      const x = slot.coordinates.street_x;
      const y = slot.coordinates.column_y;
      const z = slot.coordinates.level_z;

      const posX = x * streetSpacing + (x >= midStreet ? aisleGap : 0);
      const posY = z * levelSpacing;
      const posZ = y * colSpacing;

      dummy.position.set(posX, posY, posZ);
      dummy.updateMatrix();

      const isHighlighted =
        highlightedSlotCoords &&
        highlightedSlotCoords.street_x === x &&
        highlightedSlotCoords.column_y === y &&
        highlightedSlotCoords.level_z === z;

      if (isHighlighted) {
        highlightedPos = new THREE.Vector3(posX, posY, posZ);
      }

      if (slot.status === "OCCUPIED") {
        occupiedSlots.push({ slot, matrix: dummy.matrix.clone() });
      } else {
        freeSlots.push({ slot, matrix: dummy.matrix.clone() });
      }
    });

    // 3. Criação do InstancedMesh para Slots Livres (Cinza com fundo mais transparente estilo vidro fumê)
    const freeMaterial = new THREE.MeshStandardMaterial({
      color: 0x1e293b,     // Slate escuro translúcido
      roughness: 0.10,
      metalness: 0.05,
      transparent: true,
      opacity: 0.16,       // Fundo bem transparente conforme solicitado
      depthWrite: false,
    });
    freeMaterialRef.current = freeMaterial;

    const freeMesh = new THREE.InstancedMesh(bodyGeometry, freeMaterial, freeSlots.length);
    freeMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    freeSlotsMapRef.current = freeSlots.map((s) => s.slot);

    // 4. Criação do InstancedMesh para Slots Ocupados (Vermelho sólido com contorno glow)
    const occupiedMaterial = new THREE.MeshStandardMaterial({
      color: 0xef233c,     // Vermelho sólido vívido
      emissive: 0x4a000d,  // Brilho sutil nas bordas
      emissiveIntensity: 0.25,
      roughness: 0.35,
      metalness: 0.08,
      transparent: true,
      opacity: 1.0,        // 100% Sólido
      depthWrite: true,
    });
    occupiedMaterialRef.current = occupiedMaterial;

    const occupiedMesh = new THREE.InstancedMesh(bodyGeometry, occupiedMaterial, occupiedSlots.length);
    occupiedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    occupiedSlotsMapRef.current = occupiedSlots.map((s) => s.slot);

    // Listas para mesclagem de contornos com glow
    const freeEdgeGeometries: THREE.BufferGeometry[] = [];
    const freeEdgeGlowGeometries: THREE.BufferGeometry[] = [];
    const occEdgeGeometries: THREE.BufferGeometry[] = [];
    const occEdgeGlowGeometries: THREE.BufferGeometry[] = [];

    freeSlots.forEach((item, index) => {
      freeMesh.setMatrixAt(index, item.matrix);

      const edgeInst = outlineGeo.clone();
      edgeInst.applyMatrix4(item.matrix);
      freeEdgeGeometries.push(edgeInst);

      const glowInst = outlineGlowGeo.clone();
      glowInst.applyMatrix4(item.matrix);
      freeEdgeGlowGeometries.push(glowInst);
    });

    occupiedSlots.forEach((item, index) => {
      occupiedMesh.setMatrixAt(index, item.matrix);

      const edgeInst = outlineGeo.clone();
      edgeInst.applyMatrix4(item.matrix);
      occEdgeGeometries.push(edgeInst);

      const glowInst = outlineGlowGeo.clone();
      glowInst.applyMatrix4(item.matrix);
      occEdgeGlowGeometries.push(glowInst);
    });

    freeMesh.instanceMatrix.needsUpdate = true;
    occupiedMesh.instanceMatrix.needsUpdate = true;

    scene.add(freeMesh);
    scene.add(occupiedMesh);
    freeMeshRef.current = freeMesh;
    occupiedMeshRef.current = occupiedMesh;

    // 5. Montagem dos Outlines com Outline Glow por Categoria (Mesclados para 60 FPS)
    const edgesGroup = new THREE.Group();
    edgesGroup.name = "edges_group";

    // Contorno dos Livres: linha sutil grafite/ardósia escuro com acabamento vidro fumê
    if (freeEdgeGeometries.length > 0) {
      const mergedFreeEdges = BufferGeometryUtils.mergeGeometries(freeEdgeGeometries, false);
      const freeEdgesMat = new THREE.LineBasicMaterial({
        color: 0x334155, // Slate escuro elegante estilo cubo fumê da referência
        linewidth: 1.5,
        transparent: true,
        opacity: 0.48,
        depthWrite: false,
      });
      freeEdgesMatRef.current = freeEdgesMat;
      const freeLines = new THREE.LineSegments(mergedFreeEdges, freeEdgesMat);
      edgesGroup.add(freeLines);
      freeEdgeGeometries.forEach((g) => g.dispose());

      const mergedFreeGlow = BufferGeometryUtils.mergeGeometries(freeEdgeGlowGeometries, false);
      const freeGlowMat = new THREE.LineBasicMaterial({
        color: 0x475569,
        linewidth: 2,
        transparent: true,
        opacity: 0.22,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      });
      freeEdgesGlowMatRef.current = freeGlowMat;
      const freeGlowLines = new THREE.LineSegments(mergedFreeGlow, freeGlowMat);
      edgesGroup.add(freeGlowLines);
      freeEdgeGlowGeometries.forEach((g) => g.dispose());
    }

    // Contorno dos Ocupados: linha nítida neon vermelha + glow halo aditivo
    if (occEdgeGeometries.length > 0) {
      const mergedOccEdges = BufferGeometryUtils.mergeGeometries(occEdgeGeometries, false);
      const occEdgesMat = new THREE.LineBasicMaterial({
        color: 0xff1e42, // Vermelho neon intenso
        linewidth: 2,
        transparent: true,
        opacity: 0.95,
        depthWrite: false,
      });
      occupiedEdgesMatRef.current = occEdgesMat;
      const occLines = new THREE.LineSegments(mergedOccEdges, occEdgesMat);
      edgesGroup.add(occLines);
      occEdgeGeometries.forEach((g) => g.dispose());

      const mergedOccGlow = BufferGeometryUtils.mergeGeometries(occEdgeGlowGeometries, false);
      const occGlowMat = new THREE.LineBasicMaterial({
        color: 0xff3366,
        linewidth: 3,
        transparent: true,
        opacity: 0.55,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      });
      occupiedEdgesGlowMatRef.current = occGlowMat;
      const occGlowLines = new THREE.LineSegments(mergedOccGlow, occGlowMat);
      edgesGroup.add(occGlowLines);
      occEdgeGlowGeometries.forEach((g) => g.dispose());
    }

    outlineGeo.dispose();
    outlineGlowGeo.dispose();
    scene.add(edgesGroup);
    edgesGroupRef.current = edgesGroup;

    // 6. Atualiza Grupo de Destaque Dedicado
    if (highlightGroupRef.current) {
      if (highlightedPos) {
        highlightGroupRef.current.position.copy(highlightedPos);
        highlightGroupRef.current.visible = true;
      } else {
        highlightGroupRef.current.visible = false;
      }
    }

    // 7. Indicador 3D da DOCA DE CARGA
    const dockGroup = new THREE.Group();
    dockGroup.name = "dock_group";

    const dockGeo = new RoundedBoxGeometry(2.6, 0.12, 3.8, 3, 0.06);
    const dockMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.5,
    });
    const dockMesh = new THREE.Mesh(dockGeo, dockMat);
    dockMesh.position.set(0.8, -0.45, -2.6);
    dockGroup.add(dockMesh);

    const borderGeo = new THREE.EdgesGeometry(dockGeo);
    const borderMat = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      linewidth: 2,
    });
    const dockBorder = new THREE.LineSegments(borderGeo, borderMat);
    dockBorder.position.copy(dockMesh.position);
    dockGroup.add(dockBorder);

    // Marcador textual da Doca
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "rgba(10, 14, 23, 0.92)";
      ctx.roundRect(0, 0, 256, 64, 12);
      ctx.fill();
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 4;
      ctx.stroke();

      ctx.fillStyle = "#38bdf8";
      ctx.font = "bold 26px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("⚓ DOCA 01", 128, 32);
    }
    const texture = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.scale.set(3, 0.8, 1);
    sprite.position.set(0.8, 0.4, -2.6);
    dockGroup.add(sprite);

    scene.add(dockGroup);
  }, [warehouse, highlightedSlotCoords]);

  // Voo e foco da câmera quando o lote selecionado/buscado muda
  useEffect(() => {
    if (!cameraFocus) return;
    const [x, z, y] = cameraFocus;

    const midStreet = Math.max(1, Math.floor((warehouse?.total_streets || 4) / 2));
    const aisleGap = 1.2;
    const streetSpacing = 1.1;
    const colSpacing = 1.1;
    const levelSpacing = 1.05;

    const posX = x * streetSpacing + (x >= midStreet ? aisleGap : 0);
    const posY = z * levelSpacing;
    const posZ = y * colSpacing;

    targetLookAtRef.current.set(posX, posY, posZ);
    targetCameraPosRef.current = new THREE.Vector3(posX + 4.5, posY + 4.0, posZ + 5.5);
  }, [cameraFocus, warehouse]);

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full select-none touch-none overflow-hidden"
    />
  );
};
