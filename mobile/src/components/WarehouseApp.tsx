"use client";

import React, { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useWarehouseStore } from "@/store/useWarehouseStore";
import { fetchWarehouseGrid } from "@/services/warehouseApi";
import { WarehouseScene } from "@/components/3d/WarehouseScene";
import { Header } from "@/components/ui/Header";
import { SearchButton } from "@/components/ui/SearchButton";
import { SearchModal } from "@/components/ui/SearchModal";
import { SlotDetailDrawer } from "@/components/ui/SlotDetailDrawer";
import { PickingDrawer } from "@/components/ui/PickingDrawer";
import { LegendOverlay } from "@/components/ui/LegendOverlay";
import { Loader2 } from "lucide-react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 5, // 5 min
    },
  },
});

function WarehouseContent() {
  const [isLoading, setIsLoading] = useState(true);
  const setWarehouse = useWarehouseStore((state) => state.setWarehouse);

  useEffect(() => {
    async function loadData() {
      try {
        const { data, isMock } = await fetchWarehouseGrid("WH-MINASUL-01");
        setWarehouse(data, isMock);
      } catch (err) {
        console.error("Falha ao carregar grid:", err);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, [setWarehouse]);

  if (isLoading) {
    return (
      <div className="flex-1 w-full h-full flex flex-col items-center justify-center bg-[#0f1117] text-slate-300 space-y-3">
        <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
        <p className="text-xs uppercase tracking-widest text-slate-400 font-semibold">
          Inicializando Gêmeo Digital 3D...
        </p>
      </div>
    );
  }

  return (
    <main className="relative w-full h-full flex-1 overflow-hidden bg-[#0f1117]">
      <Header />
      <SearchButton />
      <SearchModal />
      <WarehouseScene />
      <PickingDrawer />
      <SlotDetailDrawer />
      <LegendOverlay />
    </main>
  );
}

export function WarehouseApp() {
  return (
    <QueryClientProvider client={queryClient}>
      <WarehouseContent />
    </QueryClientProvider>
  );
}
