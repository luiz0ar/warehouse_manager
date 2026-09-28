"use client";

import dynamic from "next/dynamic";

const DynamicWarehouseApp = dynamic(
  () => import("@/components/WarehouseApp").then((mod) => mod.WarehouseApp),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full min-h-screen flex flex-col items-center justify-center bg-[#0f1117] text-slate-400">
        <div className="w-8 h-8 rounded-full border-2 border-emerald-500 border-t-transparent animate-spin mb-3" />
        <span className="text-xs uppercase tracking-widest font-semibold text-slate-300">
          Carregando Armazém 3D...
        </span>
      </div>
    ),
  }
);

export default function Page() {
  return <DynamicWarehouseApp />;
}
