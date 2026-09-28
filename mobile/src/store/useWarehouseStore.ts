import { create } from "zustand";
import {
  Coordinates,
  PickingRecommendationItem,
  SlotSnapshot,
  WarehouseGridSnapshot,
} from "@/types/warehouse";
import { requestPickingRecommendation } from "@/services/warehouseApi";

interface WarehouseState {
  warehouse: WarehouseGridSnapshot | null;
  isMockMode: boolean;
  selectedSlot: SlotSnapshot | null;
  searchQuery: string;
  isSearchModalOpen: boolean;
  filterCoffeeType: string;
  filterCooperative: string;
  highlightedSlotCoords: Coordinates | null;
  highlightedBatchId: string | null;
  pickingRecommendations: PickingRecommendationItem[];
  activePickingRank: number | null;
  cameraFocus: [number, number, number] | null;

  // Actions
  setWarehouse: (warehouse: WarehouseGridSnapshot, isMock?: boolean) => void;
  selectSlot: (slot: SlotSnapshot | null) => void;
  setIsSearchModalOpen: (open: boolean) => void;
  setFilterCoffeeType: (coffeeType: string) => void;
  setFilterCooperative: (coop: string) => void;
  executeFilterSearch: (params: {
    coffeeType?: string;
    cooperative?: string;
    batchId?: string;
  }) => Promise<void>;
  searchBatch: (query: string) => void;
  clearSearch: () => void;
  setPickingRecommendations: (recommendations: PickingRecommendationItem[]) => void;
  focusPickingRank: (rank: number) => void;
  clearPicking: () => void;
}

export const useWarehouseStore = create<WarehouseState>((set, get) => ({
  warehouse: null,
  isMockMode: false,
  selectedSlot: null,
  searchQuery: "",
  isSearchModalOpen: false,
  filterCoffeeType: "ALL",
  filterCooperative: "ALL",
  highlightedSlotCoords: null,
  highlightedBatchId: null,
  pickingRecommendations: [],
  activePickingRank: null,
  cameraFocus: null,

  setWarehouse: (warehouse, isMock = false) => {
    set({ warehouse, isMockMode: isMock });
  },

  setIsSearchModalOpen: (open) => {
    set({ isSearchModalOpen: open });
  },

  setFilterCoffeeType: (coffeeType) => {
    set({ filterCoffeeType: coffeeType });
  },

  setFilterCooperative: (coop) => {
    set({ filterCooperative: coop });
  },

  selectSlot: (slot) => {
    if (!slot) {
      set({ selectedSlot: null });
      return;
    }

    set({
      selectedSlot: slot,
      highlightedSlotCoords: slot.coordinates,
      highlightedBatchId: slot.batch ? slot.batch.batch_id : null,
      cameraFocus: [
        slot.coordinates.street_x,
        slot.coordinates.level_z,
        slot.coordinates.column_y,
      ],
    });
  },

  executeFilterSearch: async ({ coffeeType, cooperative, batchId }) => {
    const { warehouse } = get();
    if (!warehouse) return;

    const typeFilter = coffeeType && coffeeType !== "ALL" ? coffeeType : undefined;
    const coopFilter = cooperative && cooperative !== "ALL" ? cooperative : undefined;
    const batchFilter = batchId?.trim().toUpperCase();

    // 1. Se informou batch_id específico, busca exato ou parcial
    if (batchFilter) {
      const exact = warehouse.slots.find(
        (s) => s.batch && s.batch.batch_id.toUpperCase() === batchFilter
      );
      const partial = warehouse.slots.find(
        (s) => s.batch && s.batch.batch_id.toUpperCase().includes(batchFilter)
      );
      const match = exact || partial;

      if (match) {
        set({
          selectedSlot: match,
          highlightedBatchId: match.batch!.batch_id,
          highlightedSlotCoords: match.coordinates,
          cameraFocus: [
            match.coordinates.street_x,
            match.coordinates.level_z,
            match.coordinates.column_y,
          ],
          isSearchModalOpen: false,
        });
        return;
      }
    }

    // 2. Consulta rota de picking via API para recomendar o melhor lote (Top 1)
    try {
      const res = await requestPickingRecommendation({
        warehouse_id: warehouse.warehouse_id,
        coffee_type: typeFilter || "BOURBON_AMARELO",
        cooperative_id: coopFilter,
        max_recommendations: 5,
      });

      if (res.recommendations && res.recommendations.length > 0) {
        const top1 = res.recommendations[0];
        const slot = warehouse.slots.find(
          (s) =>
            s.coordinates.street_x === top1.coordinates.street_x &&
            s.coordinates.column_y === top1.coordinates.column_y &&
            s.coordinates.level_z === top1.coordinates.level_z
        );

        set({
          pickingRecommendations: res.recommendations,
          activePickingRank: 1,
          selectedSlot: slot || null,
          highlightedBatchId: top1.batch_id,
          highlightedSlotCoords: top1.coordinates,
          cameraFocus: [
            top1.coordinates.street_x,
            top1.coordinates.level_z,
            top1.coordinates.column_y,
          ],
          isSearchModalOpen: false,
        });
        return;
      }
    } catch (err) {
      console.warn("Falha ao obter picking durante a busca:", err);
    }

    // 3. Fallback: seleciona o lote mais próximo da doca que bate com os filtros
    const candidates = warehouse.slots.filter(
      (s) =>
        s.status === "OCCUPIED" &&
        s.batch &&
        (!typeFilter || s.batch.coffee_type === typeFilter) &&
        (!coopFilter || s.batch.cooperative_id === coopFilter)
    );

    if (candidates.length > 0) {
      candidates.sort((a, b) => {
        const distA =
          a.coordinates.street_x + a.coordinates.column_y + a.coordinates.level_z;
        const distB =
          b.coordinates.street_x + b.coordinates.column_y + b.coordinates.level_z;
        return distA - distB;
      });

      const top1 = candidates[0];
      set({
        selectedSlot: top1,
        highlightedBatchId: top1.batch!.batch_id,
        highlightedSlotCoords: top1.coordinates,
        cameraFocus: [
          top1.coordinates.street_x,
          top1.coordinates.level_z,
          top1.coordinates.column_y,
        ],
        isSearchModalOpen: false,
      });
    } else {
      // Nenhum lote compatível encontrado
      set({
        isSearchModalOpen: false,
      });
    }
  },

  searchBatch: (query) => {
    const trimmed = query.trim().toUpperCase();
    if (!trimmed) {
      set({
        highlightedBatchId: null,
        highlightedSlotCoords: null,
        selectedSlot: null,
      });
      return;
    }

    const { warehouse } = get();
    if (!warehouse) return;

    const exactMatch = warehouse.slots.find(
      (slot) => slot.batch && slot.batch.batch_id.toUpperCase() === trimmed
    );
    const match =
      exactMatch ||
      warehouse.slots.find(
        (slot) =>
          slot.batch &&
          (slot.batch.batch_id.toUpperCase().includes(trimmed) ||
            slot.batch.cooperative_id.toUpperCase().includes(trimmed))
      );

    if (match) {
      set({
        highlightedBatchId: match.batch!.batch_id,
        highlightedSlotCoords: match.coordinates,
        selectedSlot: match,
        cameraFocus: [
          match.coordinates.street_x,
          match.coordinates.level_z,
          match.coordinates.column_y,
        ],
      });
    } else {
      set({
        highlightedBatchId: null,
        highlightedSlotCoords: null,
      });
    }
  },

  clearSearch: () => {
    set({
      searchQuery: "",
      highlightedBatchId: null,
      highlightedSlotCoords: null,
      selectedSlot: null,
      cameraFocus: null,
      pickingRecommendations: [],
      activePickingRank: null,
    });
  },

  setPickingRecommendations: (recommendations) => {
    if (recommendations.length > 0) {
      const first = recommendations[0];
      set({
        pickingRecommendations: recommendations,
        activePickingRank: 1,
        highlightedBatchId: first.batch_id,
        highlightedSlotCoords: first.coordinates,
        cameraFocus: [
          first.coordinates.street_x,
          first.coordinates.level_z,
          first.coordinates.column_y,
        ],
      });
    } else {
      set({
        pickingRecommendations: [],
        activePickingRank: null,
      });
    }
  },

  focusPickingRank: (rank) => {
    const { pickingRecommendations, warehouse } = get();
    const item = pickingRecommendations.find((r) => r.rank === rank);
    if (!item) return;

    const slot = warehouse?.slots.find(
      (s) =>
        s.coordinates.street_x === item.coordinates.street_x &&
        s.coordinates.column_y === item.coordinates.column_y &&
        s.coordinates.level_z === item.coordinates.level_z
    );

    set({
      activePickingRank: rank,
      highlightedBatchId: item.batch_id,
      highlightedSlotCoords: item.coordinates,
      selectedSlot: slot || null,
      cameraFocus: [
        item.coordinates.street_x,
        item.coordinates.level_z,
        item.coordinates.column_y,
      ],
    });
  },

  clearPicking: () => {
    set({
      pickingRecommendations: [],
      activePickingRank: null,
      highlightedBatchId: null,
      highlightedSlotCoords: null,
    });
  },
}));
