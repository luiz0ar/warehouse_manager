import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Warehouse Manager — Digital Twin 3D",
  description: "Sistema de Inteligência e Visualização 3D de Armazém de Café para Tablets e Celulares",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
  themeColor: "#0f1117",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className="h-full bg-[#0f1117]">
      <body className="h-full w-full overflow-hidden flex flex-col bg-[#0f1117] text-slate-100 antialiased">
        {children}
      </body>
    </html>
  );
}
