import type { Metadata } from "next";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Northstar SOC | Security Operations",
  description: "Portail SOC de démonstration — données servies par l'API FastAPI.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body><Providers>{children}</Providers></body>
    </html>
  );
}
