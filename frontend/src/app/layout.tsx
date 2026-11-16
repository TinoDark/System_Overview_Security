import type { Metadata } from "next";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Northstar",
  description: "Console de supervision et de réponse aux incidents.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body><Providers>{children}</Providers></body>
    </html>
  );
}
