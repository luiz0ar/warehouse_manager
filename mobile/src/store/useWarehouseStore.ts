import { create } from "zustand";
import {
  Coordinates,
  PickingRecommendationItem,
  SlotSnapshot,
  WarehouseGridSnapshot,
} from "@/types/warehouse";

interface WarehouseState {
  warehouse: WarehouseGridSnapshot | null;
  isMockMode: boolean;
  selectedSlot: SlotSnapshot | null;
  searchQuery: string;
  searchFilterType: string;
  highlightedSlotCoords: Coordinates | null;
  highlightedBatchId: string | null;
  pickingRecommendations: PickingRecommendationItem[];
  activePickingRank: number | null;
  cameraFocus: [number, number, number] | null;

  // Actions
  setWarehouse: (warehouse: WarehouseGridSnapshot, isMock?: boolean) => void;
  selectSlot: (slot: SlotSnapshot | null) => void;
  setSearchQuery: (query: string) => void;
  setSearchFilterType: (filter: string) => void;
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
  searchFilterType: "ALL",
  highlightedSlotCoords: null,
  highlightedBatchId: null,
  pickingRecommendations: [],
  activePickingRank: null,
  cameraFocus: null,

  setWarehouse: (warehouse, isMock = false) => {
    set({ warehouse, isMockMode: isMock });
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

  setSearchQuery: (query) => {
    set({ searchQuery: query });
    get().searchBatch(query);
  },

  setSearchFilterType: (filter) => {
    set({ searchFilterType: filter });
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

    // Busca por batch_id com prioridade para exato, depois parcial
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
