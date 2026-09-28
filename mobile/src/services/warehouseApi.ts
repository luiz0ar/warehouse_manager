import { api } from "@/api/api";
import {
  PickingRequest,
  PickingResponse,
  WarehouseGridSnapshot,
  SlotSnapshot,
} from "@/types/warehouse";

/**
 * Gera um armazém mock estruturado fiel ao layout do Figma:
 * Dois módulos de ruas (Bloco A e Bloco B), 3x3x3 cada, com lotes reais de café.
 */
export function generateMockWarehouse(): WarehouseGridSnapshot {
  const totalStreets = 6;
  const totalColumns = 3;
  const totalLevels = 3;

  const slots: SlotSnapshot[] = [];
  let occupiedCount = 0;
  let freeCount = 0;

  // Lotes predefinidos para bater com o layout visual do Figma
  const occupiedPresets: Record<string, { batchId: string; type: string; coop: string; weight: number }> = {
    "1-1-1": { batchId: "LOTE-2026-001", type: "ARABICA", coop: "COOP-SUL", weight: 1250 },
    "2-2-0": { batchId: "LOTE-2026-002", type: "ARABICA", coop: "COOP-MINAS", weight: 1100 },
    "2-2-1": { batchId: "LOTE-2026-003", type: "CONILON", coop: "COOP-ESPIRITO", weight: 1320 },
    "5-0-0": { batchId: "LOTE-2026-010", type: "ARABICA", coop: "COOP-SUL", weight: 1200 },
    "5-0-1": { batchId: "LOTE-2026-011", type: "ARABICA", coop: "COOP-SUL", weight: 1200 },
    "5-0-2": { batchId: "LOTE-2026-012", type: "ARABICA", coop: "COOP-SUL", weight: 1180 },
    "5-2-0": { batchId: "LOTE-2026-020", type: "CONILON", coop: "COOP-MOGIANA", weight: 1400 },
    "5-2-1": { batchId: "LOTE-2026-021", type: "CONILON", coop: "COOP-MOGIANA", weight: 1350 },
    "0-2-1": { batchId: "LOTE-2026-077", type: "ARABICA", coop: "COOP-CERRADO", weight: 1210 },
  };

  for (let x = 0; x < totalStreets; x++) {
    for (let y = 0; y < totalColumns; y++) {
      for (let z = 0; z < totalLevels; z++) {
        const key = `${x}-${y}-${z}`;
        const preset = occupiedPresets[key];

        if (preset) {
          occupiedCount++;
          slots.push({
            coordinates: { street_x: x, column_y: y, level_z: z },
            status: "OCCUPIED",
            batch: {
              batch_id: preset.batchId,
              cooperative_id: preset.coop,
              coffee_type: preset.type,
              harvest_year: 2026,
              entry_date: "2026-09-20T10:00:00Z",
              weight_kg: preset.weight,
            },
          });
        } else {
          freeCount++;
          slots.push({
            coordinates: { street_x: x, column_y: y, level_z: z },
            status: "FREE",
            batch: null,
          });
        }
      }
    }
  }

  return {
    warehouse_id: "WH-CENTRAL-01",
    name: "Armazém Cooperativa Central (Digital Twin)",
    total_streets: totalStreets,
    total_columns: totalColumns,
    total_levels: totalLevels,
    dock_coordinates: { street_x: 0, column_y: 0, level_z: 0 },
    total_slots: totalStreets * totalColumns * totalLevels,
    occupied_slots_count: occupiedCount,
    free_slots_count: freeCount,
    slots,
  };
}

/**
 * Consulta a topologia 3D do armazém utilizando a biblioteca ky.
 */
export async function fetchWarehouseGrid(
  warehouseId: string = "WH-MINASUL-01"
): Promise<{ data: WarehouseGridSnapshot; isMock: boolean }> {
  try {
    const data = await api
      .get(`warehouses/${warehouseId}/grid`)
      .json<WarehouseGridSnapshot>();
    return { data, isMock: false };
  } catch (error) {
    console.warn("API indisponível via ky, utilizando fallback simulado:", error);
    return { data: generateMockWarehouse(), isMock: true };
  }
}

/**
 * Solicita rota ótima de picking via API com ky.
 */
export async function requestPickingRecommendation(
  payload: PickingRequest
): Promise<PickingResponse> {
  try {
    const response = await api
      .post("picking/recommend", {
        json: payload,
      })
      .json<PickingResponse>();
    return response;
  } catch (error) {
    console.warn("API Picking indisponível via ky, simulando rota heurística local:", error);

    // Simulação local de recomendação heurística como fallback
    const mockWarehouse = generateMockWarehouse();
    const candidates = mockWarehouse.slots
      .filter(
        (s) =>
          s.status === "OCCUPIED" &&
          s.batch &&
          (!payload.coffee_type || s.batch.coffee_type === payload.coffee_type) &&
          (!payload.cooperative_id || s.batch.cooperative_id === payload.cooperative_id)
      )
      .slice(0, payload.max_recommendations || 3)
      .map((slot, index) => {
        const dist = Math.sqrt(
          slot.coordinates.street_x ** 2 +
            slot.coordinates.column_y ** 2 +
            slot.coordinates.level_z ** 2
        );
        return {
          rank: index + 1,
          batch_id: slot.batch!.batch_id,
          coordinates: slot.coordinates,
          distance_to_dock: Number(dist.toFixed(1)),
          blocking_bags_count: 0,
          estimated_cost: Number((dist * 1.2).toFixed(1)),
          coffee_type: slot.batch!.coffee_type,
          cooperative_id: slot.batch!.cooperative_id,
        };
      });

    return {
      warehouse_id: payload.warehouse_id,
      generated_at: new Date().toISOString(),
      total_candidates_evaluated: candidates.length,
      recommendations: candidates,
    };
  }
}
