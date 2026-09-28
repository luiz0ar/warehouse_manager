"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { useWarehouseStore } from "@/store/useWarehouseStore";
import { SlotSnapshot } from "@/types/warehouse";

interface WarehouseSceneProps {
  onSlotClick?: (slot: SlotSnapshot) => void;
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
  const instancedMeshRef = useRef<THREE.InstancedMesh | null>(null);
  const targetLookAtRef = useRef<THREE.Vector3>(new THREE.Vector3(0, 0, 0));
  const currentLookAtRef = useRef<THREE.Vector3>(new THREE.Vector3(0, 0, 0));
  const pointerDownPos = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Mapeamento index -> SlotSnapshot
  const slotIndexMapRef = useRef<SlotSnapshot[]>([]);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    // 1. Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f1117);
    sceneRef.current = scene;

    // 2. Camera (Posição isométrica ideal para armazém 3D)
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 1000);
    camera.position.set(16, 14, 18);
    cameraRef.current = camera;

    // 3. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.innerHTML = "";
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2 - 0.05; // Evita olhar por debaixo do chão
    controls.minDistance = 5;
    controls.maxDistance = 60;
    controls.target.set(3, 1.5, 2);
    targetLookAtRef.current.set(3, 1.5, 2);
    currentLookAtRef.current.set(3, 1.5, 2);
    controlsRef.current = controls;

    // 5. Iluminação Clean & Moderna
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight1.position.set(20, 30, 20);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x60a5fa, 0.4);
    dirLight2.position.set(-20, -10, -20);
    scene.add(dirLight2);

    // 6. Grid do Chão & Piso Minimalista
    const gridHelper = new THREE.GridHelper(40, 40, 0x1e293b, 0x161e2e);
    gridHelper.position.y = -0.51;
    scene.add(gridHelper);

    // 7. Raycaster para Toque / Click
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
      // Se moveu mais de 6px foi drag/pan, não clique
      if (dist > 6) return;

      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      if (instancedMeshRef.current) {
        const intersects = raycaster.intersectObject(instancedMeshRef.current);
        if (intersects.length > 0) {
          const instanceId = intersects[0].instanceId;
          if (instanceId !== undefined && slotIndexMapRef.current[instanceId]) {
            const slot = slotIndexMapRef.current[instanceId];
            selectSlot(slot);
            if (onSlotClick) onSlotClick(slot);
          }
        }
      }
    };

    const domElement = renderer.domElement;
    domElement.addEventListener("pointerdown", handlePointerDown);
    domElement.addEventListener("pointerup", handlePointerUp);

    // 8. Loop de Animação com Pulso de Destaque
    let animationFrameId: number;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = performance.now() * 0.001;

      // Interpolação suave de foco da câmera
      if (targetLookAtRef.current && controls) {
        currentLookAtRef.current.lerp(targetLookAtRef.current, 0.05);
        controls.target.copy(currentLookAtRef.current);
      }

      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    // 9. Resize Handler
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

  // Atualização da Geometria e Cores das Instâncias (InstancedMesh)
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !warehouse) return;

    // Remove mesh anterior se existir
    if (instancedMeshRef.current) {
      scene.remove(instancedMeshRef.current);
      instancedMeshRef.current.geometry.dispose();
      (instancedMeshRef.current.material as THREE.Material).dispose();
      instancedMeshRef.current = null;
    }

    // Remove doca anterior
    const prevDock = scene.getObjectByName("dock_group");
    if (prevDock) scene.remove(prevDock);

    const totalSlots = warehouse.slots.length;
    if (totalSlots === 0) return;

    // Tamanho dos blocos cúbicos (0.85 para dar um espaçamento sutil como no Figma)
    const cubeSize = 0.88;
    const geometry = new THREE.BoxGeometry(cubeSize, cubeSize, cubeSize);

    // Material com acabamento fosco suave moderno
    const material = new THREE.MeshStandardMaterial({
      roughness: 0.35,
      metalness: 0.1,
    });

    const instancedMesh = new THREE.InstancedMesh(geometry, material, totalSlots);
    instancedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);

    const dummy = new THREE.Object3D();
    const colorFree = new THREE.Color(0x22c55e);      // Verde livre
    const colorOccupied = new THREE.Color(0xef4444);  // Vermelho ocupado
    const colorHighlight = new THREE.Color(0xfacc15); // Amarelo destaque/busca

    const slotIndexMap: SlotSnapshot[] = [];

    // Fator de separação de corredor (para criar os 2 blocos de ruas do mockup)
    // Se rua >= 3, adiciona um espaço extra no eixo X (corredor para empilhadeira)
    const aisleGap = 1.2;
    const streetSpacing = 1.1;
    const colSpacing = 1.1;
    const levelSpacing = 1.05;

    warehouse.slots.forEach((slot, index) => {
      slotIndexMap.push(slot);

      const x = slot.coordinates.street_x;
      const y = slot.coordinates.column_y;
      const z = slot.coordinates.level_z;

      // Posição no espaço 3D (X = ruas, Y = altura/nível, Z = colunas/profundidade)
      const posX = x * streetSpacing + (x >= 3 ? aisleGap : 0);
      const posY = z * levelSpacing;
      const posZ = y * colSpacing;

      dummy.position.set(posX, posY, posZ);
      dummy.updateMatrix();
      instancedMesh.setMatrixAt(index, dummy.matrix);

      // Determina cor
      const isHighlighted =
        highlightedSlotCoords &&
        highlightedSlotCoords.street_x === x &&
        highlightedSlotCoords.column_y === y &&
        highlightedSlotCoords.level_z === z;

      if (isHighlighted) {
        instancedMesh.setColorAt(index, colorHighlight);
      } else if (slot.status === "OCCUPIED") {
        instancedMesh.setColorAt(index, colorOccupied);
      } else {
        instancedMesh.setColorAt(index, colorFree);
      }
    });

    instancedMesh.instanceColor!.needsUpdate = true;
    instancedMesh.instanceMatrix.needsUpdate = true;
    scene.add(instancedMesh);
    instancedMeshRef.current = instancedMesh;
    slotIndexMapRef.current = slotIndexMap;

    // Criar Indicador 3D da DOCA DE CARGA (Ground Zero)
    const dockGroup = new THREE.Group();
    dockGroup.name = "dock_group";

    // Plataforma da doca (em frente à rua 0 e 1)
    const dockGeo = new THREE.BoxGeometry(2.6, 0.1, 3.8);
    const dockMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      roughness: 0.6,
    });
    const dockMesh = new THREE.Mesh(dockGeo, dockMat);
    dockMesh.position.set(0.8, -0.45, -2.6);
    dockGroup.add(dockMesh);

    // Borda luminosa / neon ciano da doca
    const borderGeo = new THREE.EdgesGeometry(dockGeo);
    const borderMat = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      linewidth: 2,
    });
    const dockBorder = new THREE.LineSegments(borderGeo, borderMat);
    dockBorder.position.copy(dockMesh.position);
    dockGroup.add(dockBorder);

    // Marcador de texto / ícone da Doca em Sprite
    const canvas = document.createElement("canvas");
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "rgba(15, 23, 42, 0.9)";
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

  // Atualização suave do alvo de foco da câmera quando muda no store
  useEffect(() => {
    if (!cameraFocus) return;
    const [x, z, y] = cameraFocus;

    const aisleGap = 1.2;
    const streetSpacing = 1.1;
    const colSpacing = 1.1;
    const levelSpacing = 1.05;

    const posX = x * streetSpacing + (x >= 3 ? aisleGap : 0);
    const posY = z * levelSpacing;
    const posZ = y * colSpacing;

    targetLookAtRef.current.set(posX, posY, posZ);
  }, [cameraFocus]);

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full select-none touch-none overflow-hidden"
    />
  );
};
