export type SlotStatus = "FREE" | "OCCUPIED" | "RESERVED";

export interface Coordinates {
  street_x: number;
  column_y: number;
  level_z: number;
}

export interface Batch {
  batch_id: string;
  cooperative_id: string;
  coffee_type: string;
  harvest_year: number;
  entry_date: string;
  weight_kg: number;
}

export interface SlotSnapshot {
  coordinates: Coordinates;
  status: SlotStatus;
  batch: Batch | null;
}

export interface WarehouseGridSnapshot {
  warehouse_id: string;
  name: string;
  total_streets: number;
  total_columns: number;
  total_levels: number;
  dock_coordinates: Coordinates;
  total_slots: number;
  occupied_slots_count: number;
  free_slots_count: number;
  slots: SlotSnapshot[];
}

export interface PickingRecommendationItem {
  rank: number;
  batch_id: string;
  coordinates: Coordinates;
  distance_to_dock: number;
  blocking_bags_count: number;
  estimated_cost: number;
  coffee_type: string;
  cooperative_id: string;
}

export interface PickingResponse {
  warehouse_id: string;
  generated_at: string;
  total_candidates_evaluated: number;
  recommendations: PickingRecommendationItem[];
}

export interface PickingRequest {
  warehouse_id: string;
  coffee_type: string;
  cooperative_id?: string;
  max_recommendations?: number;
}
